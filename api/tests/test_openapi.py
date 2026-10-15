"""The committed api/openapi.yaml matches the code (regenerate with `make openapi`)."""

from io import StringIO
from pathlib import Path

import yaml
from django.core.management import call_command

API_DIR = Path(__file__).resolve().parents[1]


def test_committed_openapi_schema_has_no_drift(capsys):
    generated = StringIO()
    call_command("spectacular", stdout=generated)
    capsys.readouterr()  # legacy views print schema warnings; they are not failures here
    committed = (API_DIR / "openapi.yaml").read_text(encoding="utf-8")
    assert generated.getvalue() == committed, (
        "api/openapi.yaml is stale: run `make openapi` and commit the result"
    )


def test_schema_is_openapi_3_1():
    schema = yaml.safe_load((API_DIR / "openapi.yaml").read_text(encoding="utf-8"))
    assert schema["openapi"].startswith("3.1")
    assert schema["info"]["title"] == "AfyaSync HMIS API"
