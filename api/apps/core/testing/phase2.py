"""Shared pytest fixtures for the Phase 2 apps (import with ``from ... import *`` in an app's
tests/conftest.py). Synthetic data only."""

from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.access.roles import ROLES_BY_CODE
from apps.accounts.models import ProfessionalLicence
from apps.facilities.models import ServicePoint
from apps.facilities.tests.factories import ServicePointFactory
from apps.patients.tests.factories import PatientFactory

POINT_KINDS = [
    "triage",
    "consultation",
    "emergency",
    "lab",
    "imaging",
    "pharmacy",
    "cashier",
    "treatment_room",
]


@pytest.fixture
def clinician(make_user, grant, facility):
    """clinician("lab_technologist", "lab_supervisor") → a user with those roles and valid
    licences for every regulator the roles accept (any role, unlike ``staff``)."""

    def make(*roles: str, licensed: bool = True, user: Any = None) -> Any:
        person = user or make_user()
        for role in roles:
            grant(person, role, facility)
            if licensed:
                for regulator in ROLES_BY_CODE[role].licence_regulators:
                    ProfessionalLicence.objects.get_or_create(
                        user=person,
                        regulator=regulator,
                        defaults={
                            "registration_number": f"TEST-{person.pk}-{regulator}",
                            "valid_to": timezone.localdate() + timedelta(days=365),
                        },
                    )
        return person

    return make


@pytest.fixture
def api_for(clinician):
    """api_for("nurse") → (APIClient signed in, user) for a licensed user with those roles."""
    from rest_framework.test import APIClient

    def make(*roles: str, user: Any = None) -> APIClient:
        person = clinician(*roles, user=user)
        client = APIClient()
        client.force_login(person)
        session = client.session
        session["mfa_verified"] = True
        session.save()
        client.user = person  # type: ignore[attr-defined]
        return client

    return make


@pytest.fixture
def points(facility) -> dict[str, ServicePoint]:
    return {
        kind: ServicePointFactory.create(
            facility=facility, kind=kind, code=kind[:3].upper() + "1", name=kind.title()
        )
        for kind in POINT_KINDS
    }


@pytest.fixture
def patient(facility):
    return PatientFactory.create(facility=facility)
