"""The committed role matrix is the policy: every role x permission cell is asserted.

docs/generated/role-matrix.csv is regenerated with `make role-matrix`.
"""

import csv
from pathlib import Path

import pytest

from apps.access.models import Role
from apps.access.services import role_matrix_csv

MATRIX = Path(__file__).resolve().parents[2] / "docs" / "generated" / "role-matrix.csv"


def committed_cells():
    with MATRIX.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    role_codes = [
        name
        for name in rows[0]
        if name not in ("permission", "sensitivity", "requires_licence", "privileged")
    ]
    return [(row["permission"], role, row[role] == "Y") for row in rows for role in role_codes]


@pytest.mark.django_db
def test_committed_matrix_is_current():
    assert role_matrix_csv() == MATRIX.read_text(encoding="utf-8"), (
        "docs/generated/role-matrix.csv is stale: run `make role-matrix`"
    )


@pytest.mark.req("KE-DPA-06")
@pytest.mark.django_db
def test_every_role_permission_cell():
    granted = {
        role.code: set(role.permissions.values_list("code", flat=True))
        for role in Role.objects.filter(active=True)
    }
    mismatches = [
        (permission, role, expected)
        for permission, role, expected in committed_cells()
        if (permission in granted[role]) != expected
    ]
    assert mismatches == []
