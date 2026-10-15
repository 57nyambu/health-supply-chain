"""Select the settings module from DJANGO_ENV (dev | test | prod)."""

import os
from pathlib import Path

ENVIRONMENTS = ("dev", "test", "prod")
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def configure_settings_module(default: str) -> str:
    """Set DJANGO_SETTINGS_MODULE from DJANGO_ENV unless it is already set explicitly."""
    import environ

    # DJANGO_ENV may live in the repository .env; real environment variables win.
    if (REPO_ROOT / ".env").exists():
        environ.Env.read_env(REPO_ROOT / ".env")
    name = os.environ.get("DJANGO_ENV", default)
    if name not in ENVIRONMENTS:
        raise RuntimeError(f"DJANGO_ENV must be one of {', '.join(ENVIRONMENTS)}; got {name!r}.")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"config.settings.{name}")
    return os.environ["DJANGO_SETTINGS_MODULE"]
