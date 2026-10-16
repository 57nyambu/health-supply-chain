"""Development settings: local stack, fake integrations, synthetic data only."""

from .base import *

DJANGO_ENV = "dev"
# Next.js (dev server on 3000, end-to-end production build on 3100) proxies /api/* to Django
# with Django's own Host, so the browser's Origin must be trusted for CSRF. Production is
# same-host behind nginx.
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["http://127.0.0.1:3000", "http://localhost:3000", "http://127.0.0.1:3100"],
)

DEBUG = env.bool("DJANGO_DEBUG", default=True)
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
