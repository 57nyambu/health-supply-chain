"""Shared pytest fixtures: synthetic users, facilities and role assignments."""

import itertools
from datetime import datetime, timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.access.models import Role, RoleAssignment
from apps.accounts.models import ProfessionalLicence
from apps.facilities.models import Facility
from apps.facilities.tests.factories import FacilityFactory

_emails = itertools.count(1)


@pytest.fixture(autouse=True)
def _isolated_audit_context():
    """Views called without the middleware may refine the audit context; never leak it."""
    from apps.audit import context

    token = context._context.set(context.AuditContext())
    yield
    context._context.reset(token)


@pytest.fixture(autouse=True)
def _fresh_throttles():
    """Rate limits are per client IP; every test starts with a clean budget."""
    from django.core.cache import cache

    cache.clear()


@pytest.fixture
def make_user(django_user_model):
    def make(email: str | None = None, **fields: Any):
        address = email or f"user{next(_emails)}@example.test"
        return django_user_model.objects.create_user(email=address, **fields)

    return make


@pytest.fixture
def facility(db) -> Facility:
    return FacilityFactory.create()


@pytest.fixture
def api_as(make_user, grant):
    """api_as("store_keeper", facility) → an APIClient signed in as a new user with that role."""
    from rest_framework.test import APIClient

    def make(*role_codes: str, facility: Facility, user: Any = None) -> APIClient:
        person = user or make_user()
        for code in role_codes:
            grant(person, code, facility)
        client = APIClient()
        client.force_login(person)
        # A fully signed-in user: password and (where required) second factor done.
        # MFA itself is exercised end to end in apps/accounts/tests/test_mfa.py.
        session = client.session
        session["mfa_verified"] = True
        session.save()
        client.user = person  # type: ignore[attr-defined]
        return client

    return make


@pytest.fixture
def grant(db):
    """grant(user, "receptionist", facility, valid_to=..., department=..., ward=...)."""

    def make(
        user: Any,
        role_code: str,
        facility: Facility,
        *,
        valid_from: datetime | None = None,
        **fields: Any,
    ) -> RoleAssignment:
        return RoleAssignment.objects.create(
            user=user,
            role=Role.objects.get(code=role_code),
            facility=facility,
            valid_from=valid_from or timezone.now(),
            **fields,
        )

    return make


# Regulator whose licence each seeded clinical role needs (KE-PRF-01).
REGULATOR = {
    "clinical_officer": "COC",
    "medical_officer": "KMPDC",
    "medical_superintendent": "KMPDC",
    "nurse": "NCK",
    "triage_nurse": "NCK",
    "pharmacist": "PPB",
}


@pytest.fixture
def staff(make_user, grant, facility):
    """staff("clinical_officer") → a user with that role and, for clinicians, a valid licence."""

    def make(*roles: str, licensed: bool = True) -> Any:
        user = make_user()
        for role in roles:
            grant(user, role, facility)
            if licensed and role in REGULATOR:
                ProfessionalLicence.objects.get_or_create(
                    user=user,
                    regulator=REGULATOR[role],
                    defaults={
                        "registration_number": f"TEST-{user.pk}-{role}",
                        "valid_to": timezone.localdate() + timedelta(days=365),
                    },
                )
        return user

    return make
