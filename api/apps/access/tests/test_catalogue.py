import pytest

from apps.access import catalogue
from apps.access.catalogue import CODE_PATTERN, PermissionDef, all_permissions, expand
from apps.access.models import Permission, Role
from apps.access.roles import ROLES, ROLES_BY_CODE, ChartAccess
from apps.access.services import sync_access

DESIGN_BASE_ROLES = {
    "system_admin",
    "facility_admin",
    "medical_superintendent",
    "hrio",
    "receptionist",
    "triage_nurse",
    "nurse",
    "clinical_officer",
    "medical_officer",
    "specialist",
    "intern",
    "lab_technologist",
    "lab_supervisor",
    "radiographer",
    "radiologist",
    "pharmacist",
    "pharm_tech",
    "cashier",
    "billing_officer",
    "claims_officer",
    "finance_manager",
    "store_keeper",
    "dpo",
    "auditor",
    "report_viewer",
}
DESIGN_ADDON_ROLES = {
    "cashier_supervisor",
    "billing_supervisor",
    "claims_supervisor",
    "hrio_supervisor",
    "nurse_in_charge",
    "pharmacy_in_charge",
}
MFA_REQUIRED = {  # DESIGN §7.2
    "facility_admin",
    "system_admin",
    "medical_superintendent",
    "finance_manager",
    "claims_officer",
    "auditor",
    "dpo",
}


def test_every_code_follows_the_naming_rule():
    for code in all_permissions():
        assert CODE_PATTERN.match(code), code


def test_invalid_codes_are_rejected():
    with pytest.raises(ValueError, match=r"domain.resource.action"):
        PermissionDef("clinical.cosign", "two parts only")
    with pytest.raises(ValueError):
        PermissionDef("Clinical.Note.Write", "uppercase")


def test_duplicate_declarations_are_rejected(monkeypatch):
    duplicate = [PermissionDef("access.role.read", "again")]
    real = catalogue._module_permissions

    def fake(module_path):
        if module_path == "apps.access.reserved":
            return real(module_path) + duplicate
        return real(module_path)

    monkeypatch.setattr(catalogue, "_module_permissions", fake)
    all_permissions.cache_clear()
    try:
        with pytest.raises(ValueError, match="declared twice"):
            all_permissions()
    finally:
        all_permissions.cache_clear()


def test_patterns_expand_and_unknown_codes_fail():
    assert "patients.merge.approve" in expand("patients.*")
    assert expand("payments.receive.*") == {
        "payments.receive.cash",
        "payments.receive.mpesa",
        "payments.receive.card",
        "payments.receive.bank",
    }
    with pytest.raises(KeyError):
        expand("clinical.record.read_everything")
    with pytest.raises(KeyError):
        expand("nonexistent.*")


def test_roles_match_design_7_4_including_intern_dpo_and_addons():
    codes = {role.code for role in ROLES if not role.service_account}
    assert codes == DESIGN_BASE_ROLES | DESIGN_ADDON_ROLES
    assert {role.code for role in ROLES if role.addon} == DESIGN_ADDON_ROLES
    assert ROLES_BY_CODE["intern"].requires_cosign


def test_mfa_required_roles_match_design_7_2():
    assert {role.code for role in ROLES if role.mfa_required} == MFA_REQUIRED


@pytest.mark.parametrize(
    ("role", "permission"),
    [
        ("system_admin", "integrations.sha.configure"),
        ("facility_admin", "access.assignment.grant_privileged"),
        ("medical_superintendent", "visits.gate.override"),
        ("medical_superintendent", "billing.waiver.approve_high"),
        ("medical_superintendent", "access.breakglass.review"),
        ("hrio", "patients.merge.request"),
        ("hrio", "reporting.moh.export"),
        ("hrio", "patients.dsar.process"),
        ("receptionist", "patients.patient.create"),
        ("receptionist", "insurance.eligibility.check"),
        ("triage_nurse", "clinical.triage.record"),
        ("nurse", "pharmacy.mar.record"),
        ("clinical_officer", "pharmacy.prescription.create"),
        ("medical_officer", "inpatient.discharge.sign"),
        ("specialist", "insurance.preauth.clinical_signoff"),
        ("lab_supervisor", "laboratory.result.release"),
        ("radiologist", "imaging.report.sign"),
        ("pharmacist", "pharmacy.controlled.dispense"),
        ("cashier", "payments.shift.own"),
        ("billing_officer", "billing.invoice.finalize"),
        ("claims_officer", "insurance.claim.submit"),
        ("finance_manager", "payments.refund.approve"),
        ("store_keeper", "inventory.batch.manage"),
        ("dpo", "privacy.breach.manage"),
        ("auditor", "audit.log.read"),
        ("report_viewer", "reports.aggregate.read"),
        ("cashier_supervisor", "payments.void.approve"),
        ("billing_supervisor", "billing.waiver.approve_low"),
        ("claims_supervisor", "insurance.claim.cancel_submitted"),
        ("hrio_supervisor", "patients.merge.approve"),
        ("nurse_in_charge", "visits.gate.override"),
        ("pharmacy_in_charge", "pharmacy.stock_adjustment.approve"),
    ],
)
def test_notable_permissions_from_design(role, permission):
    assert permission in ROLES_BY_CODE[role].permission_codes()


@pytest.mark.parametrize(
    ("role", "permission"),
    [
        ("pharm_tech", "pharmacy.controlled.dispense"),  # pharmacist only
        (
            "claims_officer",
            "insurance.preauth.clinical_signoff",
        ),  # insurance.* except clinical sign-off
        ("hrio", "patients.merge.approve"),  # HRIO supervisor approves merges
        ("receptionist", "clinical.record.read_summary"),
        ("finance_manager", "clinical.record.read_summary"),
        ("system_admin", "patients.patient.read"),  # break-glass only
        ("clinical_officer", "clinical.record.read_sensitive"),
    ],
)
def test_separation_of_duties_and_least_privilege(role, permission):
    assert permission not in ROLES_BY_CODE[role].permission_codes()


def test_chart_access_defaults_follow_design_7_7():
    assert ROLES_BY_CODE["receptionist"].chart_care_team == ChartAccess.DEMOGRAPHICS
    assert ROLES_BY_CODE["triage_nurse"].chart_baseline == ChartAccess.SUMMARY
    assert ROLES_BY_CODE["clinical_officer"].chart_baseline == ChartAccess.SUMMARY
    assert ROLES_BY_CODE["clinical_officer"].chart_care_team == ChartAccess.FULL
    assert ROLES_BY_CODE["medical_superintendent"].chart_care_team == ChartAccess.SENSITIVE
    for role in ("system_admin", "finance_manager", "store_keeper", "auditor", "dpo"):
        assert ROLES_BY_CODE[role].chart_care_team == ChartAccess.NONE


@pytest.mark.django_db
def test_sync_is_idempotent_and_mirrors_the_catalogue():
    first = sync_access()
    second = sync_access()
    assert second.permissions_created == second.roles_created == second.permissions_deactivated == 0
    assert first.permissions_deactivated == 0
    assert set(Permission.objects.filter(active=True).values_list("code", flat=True)) == set(
        all_permissions()
    )
    assert Role.objects.count() == len(ROLES)
    intern = Role.objects.get(code="intern")
    assert (
        set(intern.permissions.values_list("code", flat=True))
        == ROLES_BY_CODE["intern"].permission_codes()
    )


@pytest.mark.django_db
def test_codes_removed_from_code_are_deactivated():
    Permission.objects.create(code="legacy.thing.do", description="gone", sensitivity="low")
    result = sync_access()
    assert result.permissions_deactivated == 1
    assert not Permission.objects.get(code="legacy.thing.do").active
