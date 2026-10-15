"""Shared pytest fixtures: synthetic users, facilities and role assignments."""

import itertools
from datetime import datetime
from typing import Any

import pytest
from django.utils import timezone

from apps.access.models import Role, RoleAssignment
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
