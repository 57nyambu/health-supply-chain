"""Every environment variable the settings read is documented (P1-REPO-02)."""

import re
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = API_DIR.parent
ENV_READ = re.compile(
    r"""\benv(?:_or|\.(?:bool|int|list|db|str|float|json))?\(\s*["']([A-Z][A-Z0-9_]+)["']"""
)


def variables_read_by_settings():
    names = set()
    for path in (API_DIR / "config").rglob("*.py"):
        if "tests" not in path.parts:
            names.update(ENV_READ.findall(path.read_text(encoding="utf-8")))
    return names


def test_settings_read_some_variables():
    assert {
        "DJANGO_SECRET_KEY",
        "DATABASE_URL",
        "FIELD_ENCRYPTION_KEYS",
    } <= variables_read_by_settings()


def test_every_variable_is_in_env_example():
    example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    documented = set(re.findall(r"^([A-Z][A-Z0-9_]+)=", example, flags=re.MULTILINE))
    assert variables_read_by_settings() - documented == set()


def test_every_variable_is_in_env_md():
    env_md = (REPO_ROOT / "docs" / "operations" / "ENV.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"`([A-Z][A-Z0-9_]+)`", env_md))
    assert variables_read_by_settings() - documented == set()
