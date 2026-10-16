from datetime import date, timedelta

import pytest
from django.core import mail
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.utils import timezone

from apps.access import policies
from apps.access.catalogue import all_permissions
from apps.access.roles import ROLES
from apps.accounts import licences
from apps.accounts.adapters.hwr import get_registry
from apps.accounts.adapters.hwr.fake import FakeHealthWorkerRegistry
from apps.accounts.models import ProfessionalLicence
from apps.audit.models import AuditEvent
from apps.integrations.models import Notification

pytestmark = [pytest.mark.django_db, pytest.mark.req("KE-PRF-01")]

TODAY = timezone.localdate()
CLINICAL_ROLES = [
    role
    for role in ROLES
    if any(all_permissions()[code].requires_licence for code in role.permission_codes())
]


def licensed_code(role):
    return sorted(
        code for code in role.permission_codes() if all_permissions()[code].requires_licence
    )[0]


def licence(user, regulator, valid_to, **fields):
    return ProfessionalLicence.objects.create(
        user=user,
        regulator=regulator,
        registration_number=f"TEST-{user.pk}-{regulator}",
        valid_to=valid_to,
        **fields,
    )


def test_every_clinical_role_names_its_regulators():
    assert {role.code for role in CLINICAL_ROLES} >= {
        "clinical_officer",
        "nurse",
        "pharmacist",
        "lab_technologist",
    }
    for role in CLINICAL_ROLES:
        assert role.licence_regulators, role.code


@pytest.mark.parametrize("role", CLINICAL_ROLES, ids=lambda r: r.code)
def test_licensed_permissions_need_a_valid_licence_from_the_right_regulator(
    role, make_user, facility, grant
):
    code = licensed_code(role)
    user = make_user()
    grant(user, role.code, facility)
    assert not policies.has_permission(user, code, facility=facility)  # missing

    other = next(
        r for r in ProfessionalLicence.Regulator.values if r not in role.licence_regulators
    )
    licence(user, other, TODAY + timedelta(days=300))
    assert not policies.has_permission(user, code, facility=facility)  # wrong regulator

    expired = licence(user, role.licence_regulators[0], TODAY - timedelta(days=1))
    assert not policies.has_permission(user, code, facility=facility)  # expired

    expired.valid_to = TODAY + timedelta(days=200)
    expired.save()
    assert policies.has_permission(user, code, facility=facility)
    assert code in policies.effective_permissions(user, facility=facility)
    tomorrow_after_expiry = timezone.now() + timedelta(days=201)
    assert not policies.has_permission(user, code, facility=facility, at=tomorrow_after_expiry)


def test_unlicensed_permissions_do_not_need_a_licence(make_user, facility, grant):
    user = make_user()
    grant(user, "clinical_officer", facility)
    assert policies.has_permission(user, "patients.patient.read", facility=facility)


def test_licence_not_yet_valid_does_not_count(make_user, facility, grant):
    user = make_user()
    grant(user, "nurse", facility)
    licence(user, "NCK", TODAY + timedelta(days=365), valid_from=TODAY + timedelta(days=10))
    assert not policies.has_permission(user, "clinical.nursing_note.write", facility=facility)


# --- Health Worker Registry port -------------------------------------------------------------------


@pytest.mark.req("KE-DHA-04")
@pytest.mark.parametrize("registry", [FakeHealthWorkerRegistry()], ids=["fake"])
def test_registry_contract(registry):
    active = registry.lookup("KMPDC", "test-001")
    assert active is not None and active.active and active.puid.startswith("PUID-")
    assert active.licence_valid_to > TODAY
    assert registry.lookup("KMPDC", "TEST-001") == active  # deterministic, case-insensitive
    assert registry.lookup("COC", "TEST-001").puid != active.puid
    expired = registry.lookup("NCK", "EXPIRED-9")
    assert expired.licence_valid_to < TODAY
    assert registry.lookup("PPB", "SUSP-1").active is False
    assert registry.lookup("KMPDC", "12345") is None


def test_only_the_fake_registry_exists_until_phase_3(settings):
    settings.HWR_MODE = "live"
    with pytest.raises(ImproperlyConfigured, match="P3-SHA-01"):
        get_registry()


def test_verification_stores_the_puid(make_user, facility, grant):
    admin, doctor = make_user(), make_user()
    grant(admin, "facility_admin", facility)
    record = licence(doctor, "KMPDC", TODAY + timedelta(days=10))
    verified = licences.verify_licence(record, actor=admin, facility=facility)
    assert verified.puid.startswith("PUID-") and verified.verification_source == "hwr-fake"
    assert verified.valid_to.year == TODAY.year + 1  # registry is authoritative
    unknown = ProfessionalLicence.objects.create(
        user=doctor, regulator="KMPDC", registration_number="999", valid_to=TODAY
    )
    with pytest.raises(ValidationError):
        licences.verify_licence(unknown, actor=admin, facility=facility)
    assert {"access.licence.verified", "access.licence.verification_failed"} <= set(
        AuditEvent.objects.values_list("action", flat=True)
    )


# --- expiry warnings -------------------------------------------------------------------------------


def test_nightly_job_warns_holder_and_facility_admins_once(make_user, facility, grant):
    admin, nurse = make_user(), make_user()
    grant(admin, "facility_admin", facility)
    grant(nurse, "nurse", facility)
    soon = licence(nurse, "NCK", TODAY + timedelta(days=30))
    assert licences.notify_expiring(TODAY) == 1
    recipients = sorted(Notification.objects.values_list("user_id", flat=True))
    assert recipients == sorted([admin.pk, nurse.pk])
    assert len(mail.outbox) == 2
    assert "expires on" in mail.outbox[0].body
    assert licences.notify_expiring(TODAY) == 0  # not twice
    soon.valid_to = TODAY + timedelta(days=20)  # renewed record, new expiry date
    soon.save()
    assert licences.notify_expiring(TODAY) == 1


def test_licences_outside_the_window_are_not_warned(make_user):
    nurse = make_user()
    licence(nurse, "NCK", TODAY + timedelta(days=31))
    licence(nurse, "COC", TODAY - timedelta(days=1))
    assert licences.notify_expiring(TODAY) == 0


def test_warning_task_runs():
    from apps.accounts.tasks import warn_expiring_licences

    assert warn_expiring_licences() == 0


# --- API ----------------------------------------------------------------------------------------------


def test_licence_api(api_as, facility, make_user, grant):
    admin = api_as("facility_admin", facility=facility)
    doctor, stranger = make_user(), make_user()
    grant(doctor, "medical_officer", facility)
    created = admin.post(
        "/api/v1/accounts/licences/",
        {
            "user": doctor.pk,
            "regulator": "KMPDC",
            "registration_number": "TEST-77",
            "valid_to": str(TODAY + timedelta(days=60)),
        },
        format="json",
    )
    assert created.status_code == 201
    refused = admin.post(
        "/api/v1/accounts/licences/",
        {
            "user": stranger.pk,
            "regulator": "KMPDC",
            "registration_number": "TEST-78",
            "valid_to": str(TODAY),
        },
        format="json",
    )
    assert refused.status_code == 400
    licence_id = created.json()["id"]
    verified = admin.post(f"/api/v1/accounts/licences/{licence_id}/verify/").json()
    assert verified["puid"].startswith("PUID-")
    changed = admin.patch(
        f"/api/v1/accounts/licences/{licence_id}/",
        {"registration_number": "TEST-79"},
        format="json",
    )
    assert changed.json()["puid"] == "" and changed.json()["verified_at"] is None
    assert [
        row["id"]
        for row in admin.get(f"/api/v1/accounts/licences/?user={doctor.pk}").json()["results"]
    ] == [licence_id]
    assert api_as("cashier", facility=facility).get("/api/v1/accounts/licences/").status_code == 403


def test_licence_validation(make_user, facility, grant):
    admin, doctor = make_user(), make_user()
    grant(admin, "facility_admin", facility)
    with pytest.raises(ValidationError):
        licences.add_licence(
            user=doctor,
            actor=admin,
            facility=facility,
            regulator="NOPE",
            registration_number="1",
            valid_to=date(2030, 1, 1),
        )
    with pytest.raises(ValidationError):
        licences.add_licence(
            user=doctor,
            actor=admin,
            facility=facility,
            puid="PUID-X",
            regulator="KMPDC",
            registration_number="1",
            valid_to=date(2030, 1, 1),
        )
