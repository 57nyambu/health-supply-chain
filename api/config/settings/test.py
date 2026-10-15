"""Test settings: PostgreSQL (DATABASE_URL), inline tasks, no outbound mail."""

from .base import *

DEBUG = False
SECRET_KEY = "test-only-secret-key-not-used-anywhere-else-0123456789abcdef"

# Tests never need a broker: tasks run inline.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = False

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
LOGGING = logging_config("WARNING")
