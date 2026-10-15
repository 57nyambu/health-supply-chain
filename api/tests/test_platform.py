"""Platform baseline: the project boots on Django 5.2 + PostgreSQL with complete migrations."""

from io import StringIO

import django
import pytest
from django.core.management import call_command
from django.db import connection


def test_django_is_5_2_lts():
    assert django.VERSION[:2] == (5, 2)


def test_system_checks_pass():
    call_command("check", fail_level="WARNING")


@pytest.mark.django_db
def test_database_is_postgresql():
    assert connection.vendor == "postgresql"


@pytest.mark.django_db
def test_no_missing_migrations():
    out = StringIO()
    call_command("makemigrations", "--check", "--dry-run", stdout=out)
    assert "No changes detected" in out.getvalue()
