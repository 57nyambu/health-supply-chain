import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from apps.access import care_team, policies
from apps.accounts.models import ProfessionalLicence, User
from apps.facilities import seed as facility_seed
from apps.patients.models import Patient


@pytest.fixture
def seeded(settings, monkeypatch):
    from apps.patients import seed as patient_seed

    settings.DJANGO_ENV = "dev"
    monkeypatch.setattr(patient_seed, "COUNT", 1)
    call_command("seed", stdout=StringIO())
    return facility_seed.facility()


def make(*args: str) -> User:
    out = StringIO()
    call_command("e2e_user", *args, stdout=out)
    return User.objects.get(pk=json.loads(out.getvalue().strip().splitlines()[-1])["id"])


@pytest.mark.django_db
def test_e2e_user_licences_and_care_team(seeded):
    patient = Patient.objects.get(facility=seeded)
    current = make("--role", "clinical_officer", "--care-team", str(patient.pk))
    assert care_team.is_member(current, patient)
    assert ProfessionalLicence.objects.get(user=current).valid_to > timezone.localdate()
    assert policies.has_permission(current, "pharmacy.prescription.create", facility=seeded.pk)

    lapsed = make("--role", "clinical_officer", "--licence-expired")
    assert ProfessionalLicence.objects.get(user=lapsed).valid_to < timezone.localdate()
    assert not care_team.is_member(lapsed, patient)
    assert not policies.has_permission(lapsed, "pharmacy.prescription.create", facility=seeded.pk)
    # Licensed permissions (break-glass too, DESIGN §7.10) go; the rest of the role stays.
    assert not policies.has_permission(lapsed, "access.breakglass.request", facility=seeded.pk)
    assert policies.has_permission(lapsed, "patients.patient.search", facility=seeded.pk)


@pytest.mark.django_db
def test_e2e_user_refuses_unknown_patients_and_production(seeded, settings):
    with pytest.raises(CommandError, match="No such patient"):
        make("--role", "nurse", "--care-team", "00000000-0000-0000-0000-000000000000")
    settings.DJANGO_ENV = "prod"
    with pytest.raises(CommandError, match="only with DJANGO_ENV"):
        make("--role", "nurse")
