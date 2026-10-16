"""Development settings: local stack, fake integrations, synthetic data only."""

from .base import *

DJANGO_ENV = "dev"

DEBUG = env.bool("DJANGO_DEBUG", default=True)
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
