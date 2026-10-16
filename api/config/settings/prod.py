"""Production settings. Real patient data: every guard in guards.py must pass."""

from .base import *
from .guards import check_production_settings

DJANGO_ENV = "prod"

DEBUG = env.bool("DJANGO_DEBUG", default=False)
DATA_RESIDENCY_MODE = env("DATA_RESIDENCY_MODE", default="strict")
TRUST_PROXY_HEADERS = env.bool("TRUST_PROXY_HEADERS", default=True)

# TLS terminates at nginx, which sets X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_REDIRECT_EXEMPT = [r"^healthz$", r"^readyz$"]
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

check_production_settings(globals())
