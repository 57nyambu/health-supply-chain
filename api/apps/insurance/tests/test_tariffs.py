"""SHA benefits and tariffs import (P3-SHA-01 acceptance 4; DESIGN §9; KE-SHA-08)."""

from decimal import Decimal
from io import StringIO

import pytest
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command

from apps.audit.models import AuditEvent
from apps.insurance import tariffs
from apps.insurance.models import ShaIntervention, ShaTariffVersion
from apps.insurance.seed_phase3 import TARIFF_FILE

pytestmark = pytest.mark.django_db
HEADER = ",".join(tariffs.COLUMNS)


def csv(*rows: str) -> bytes:
    return ("\n".join([HEADER, *rows]) + "\n").encode()


ROW = "SYN-X-1,Synthetic one,SYN-SB,SHIF,OP,FEE_FOR_SERVICE,no,no,no,,,1500.00,,,1200"


def test_synthetic_file_imports_once_and_is_active():
    first = tariffs.import_file(TARIFF_FILE.read_bytes(), label="SYN-T", synthetic=True)
    again = tariffs.import_file(TARIFF_FILE.read_bytes(), label="SYN-T", synthetic=True)
    assert first.created and not again.created and first.version.pk == again.version.pk
    assert first.rows == ShaIntervention.objects.count() == 8
    assert tariffs.active_version() == first.version
    assert first.version.source == ShaTariffVersion.Source.SYNTHETIC
    assert all(
        code.startswith("SYN-") for code in ShaIntervention.objects.values_list("code", flat=True)
    )
    assert AuditEvent.objects.filter(action="insurance.tariffs.imported").count() == 1


@pytest.mark.req("KE-SHA-08")
def test_tariff_by_keph_level_never_turns_unknown_into_zero():
    tariffs.import_file(TARIFF_FILE.read_bytes(), label="SYN-T", synthetic=True)
    assert tariffs.tariff("syn-sha-op-001", 4) == Decimal("1500.00")
    assert tariffs.tariff("SYN-SHA-OP-002", 2) == Decimal("8500.00")  # no level-2 rate: overall
    assert tariffs.tariff("SYN-SHA-IP-001", 4) is None  # per diem with no published rate
    assert tariffs.tariff("SYN-PHC-001", 3) == Decimal("0.00")  # capitation is a real zero
    assert tariffs.tariff("NOPE", 4) is None
    assert tariffs.unknown_codes(["SYN-PHC-001", "NOPE", "nope"]) == ["NOPE"]
    flags = tariffs.intervention("SYN-SHA-OP-003")
    assert flags is not None and flags.needs_preauth and flags.needs_manual_preauth_approval


def test_a_new_version_replaces_the_active_one():
    old = tariffs.import_file(csv(ROW), label="V1", synthetic=True).version
    new = tariffs.import_file(
        csv(ROW.replace("1500.00", "1600.00")), label="V2", synthetic=True
    ).version
    old.refresh_from_db()
    assert not old.active and new.active
    assert tariffs.tariff("SYN-X-1", 4) == Decimal("1600.00")
    kept = tariffs.import_file(
        csv(ROW, ROW.replace("SYN-X-1", "SYN-X-2")), label="V3", synthetic=True, activate=False
    )
    assert not kept.version.active and tariffs.active_version() == new
    with pytest.raises(ValidationError, match="already exists"):
        tariffs.import_file(csv(ROW.replace("1500.00", "1700.00")), label="V1", synthetic=True)


@pytest.mark.parametrize(
    "content, message",
    [
        (b"code,name\nX,Y\n", "lacks columns"),
        (csv(), "no rows"),
        (csv(ROW, ROW), "appears twice"),
        (csv(ROW.replace("Synthetic one", "")), "name is empty"),
        (csv(ROW.replace("1500.00", "abc")), "level_4 is not an amount"),
        (csv(ROW.replace("1500.00", "-1")), "level_4 is negative"),
        (csv(ROW.replace(",no,no,no,", ",maybe,no,no,")), "needs_preauth must be yes or no"),
        ("﻿".encode("utf-16"), "UTF-8"),
    ],
)
def test_invalid_files_are_refused_whole_with_the_line(content, message):
    with pytest.raises(ValidationError, match=message):
        tariffs.import_file(content, label="BAD", synthetic=True)
    assert not ShaTariffVersion.objects.exists()


def test_import_command(tmp_path):
    path = tmp_path / "tariffs.csv"
    path.write_bytes(csv(ROW))
    out = StringIO()
    call_command(
        "import_sha_tariffs", str(path), "--tariff-version", "CMD-1", "--synthetic", stdout=out
    )
    assert "imported, 1 interventions" in out.getvalue()
    call_command(
        "import_sha_tariffs", str(path), "--tariff-version", "CMD-1", "--synthetic", stdout=out
    )
    assert "already imported" in out.getvalue()
    with pytest.raises(CommandError, match="No such file"):
        call_command("import_sha_tariffs", str(tmp_path / "missing.csv"), "--tariff-version", "X")
    bad = tmp_path / "bad.csv"
    bad.write_bytes(b"code\n")
    with pytest.raises(CommandError, match="lacks columns"):
        call_command("import_sha_tariffs", str(bad), "--tariff-version", "Y")
