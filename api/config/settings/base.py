"""Settings shared by every environment.

Environment-specific modules (dev, test, prod) import from here and are
selected by DJANGO_ENV (see config/env.py). Every value that differs per
deployment or is secret comes from the environment; each variable is
documented in .env.example and docs/operations/ENV.md.
"""

from datetime import timedelta
from pathlib import Path

import environ
from celery.schedules import crontab

from apps.core.logs import logging_config

# BASE_DIR is api/; the shared .env and data/ live at the repository root.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = BASE_DIR.parent

env = environ.Env()
if (REPO_ROOT / ".env").exists():
    environ.Env.read_env(REPO_ROOT / ".env")

DJANGO_ENV = env("DJANGO_ENV", default="dev")

# --- Core security ---------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", default="unsafe-dev-secret")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# --- Database: PostgreSQL everywhere; SQLite is not supported ----------------
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://afyasync:afyasync@127.0.0.1:5432/afyasync",
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Applications ------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    "apps.core",
    "apps.accounts",
    "apps.products",
    "apps.suppliers",
    "apps.warehouses",
    "apps.sales.apps.SalesConfig",
    "apps.procurement",
    "apps.integrations",
    "apps.analytics",
    "apps.facility_ops",
    "apps.ai",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.core.request_id.RequestIdMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.idempotency.IdempotencyMiddleware",
]
CSRF_FAILURE_VIEW = "apps.core.problems.csrf_failure"

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
AUTH_USER_MODEL = "accounts.User"
APPEND_SLASH = True

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Locale: Kenya -------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

# --- Static files ----------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- Data protection ------------------------------------------------------------
# Local object store root (DESIGN §13). Production holds real patient files here.
DATA_DIR = Path(env("DATA_DIR", default=str(REPO_ROOT / "data")))
# Field encryption keys (P1-DATA-01) and storage master keys (P1-STO-01):
# JSON objects {"<key id>": "<base64 32-byte key>"}, newest first.
FIELD_ENCRYPTION_KEYS = env("FIELD_ENCRYPTION_KEYS", default="")
FIELD_BLIND_INDEX_KEY = env("FIELD_BLIND_INDEX_KEY", default="")
STORAGE_MASTER_KEYS = env("STORAGE_MASTER_KEYS", default="")
# Residency guard (DESIGN §8.3): strict | warn | off.
DATA_RESIDENCY_MODE = env("DATA_RESIDENCY_MODE", default="warn")
RESIDENCY_ALLOWED_HOSTS = env.list("RESIDENCY_ALLOWED_HOSTS", default=[])
# Legacy AI endpoints stay off until a DPIA covers them (ADR-014).
AI_FEATURES_ENABLED = env.bool("AI_FEATURES_ENABLED", default=False)

# --- Django REST Framework ------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "apps.ai.authentication.PublicAPIKeyAuth",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "EXCEPTION_HANDLER": "apps.core.problems.exception_handler",
    # Catalogues page by number; large lists opt into LargeListCursorPagination.
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.CataloguePagination",
    "PAGE_SIZE": 50,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "AfyaSync HMIS API",
    "DESCRIPTION": "AfyaSync hospital management information system API.",
    "VERSION": "1.0.0",
    "OAS_VERSION": "3.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# Legacy browser auth (SimpleJWT + CORS), removed in P1-UAC-04 (ADR-005).
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_LIFETIME_MIN", default=15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_LIFETIME_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
}

# --- Celery ------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "generate-daily-reports": {
        "task": "apps.analytics.tasks.generate_daily_sales_report",
        "schedule": crontab(hour=0, minute=0),
    },
    "purge-expired-idempotency-records": {
        "task": "apps.core.tasks.purge_expired_idempotency_records",
        "schedule": crontab(minute=15),
    },
    "flag-underperforming-facilities": {
        "task": "apps.facility_ops.tasks.flag_underperforming_facilities",
        "schedule": crontab(minute="*/30"),
    },
}

# --- Email and notifications ----------------------------------------------------------
NOTIFICATION_CHANNEL = env("NOTIFICATION_CHANNEL", default="email").lower()
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="alerts@afyasync.local")
SITE_NAME = env("SITE_NAME", default="AfyaSync")

# --- Legacy integrations (moved behind adapters in later phases) ------------------------
GEMMA_API_KEY = env("GEMMA_API_KEY", default="")
GEMMA_MODEL_ASSISTANT = env("GEMMA_MODEL_ASSISTANT", default="gemma-4-4b-it")
GEMMA_MODEL_VISION = env("GEMMA_MODEL_VISION", default="gemma-4-12b-it")
GEMMA_CACHE_TTL_SECONDS = env.int("GEMMA_CACHE_TTL_SECONDS", default=1200)
PUBLIC_API_KEY = env("PUBLIC_API_KEY", default="")
MPESA_CONSUMER_KEY = env("MPESA_CONSUMER_KEY", default="")
MPESA_CONSUMER_SECRET = env("MPESA_CONSUMER_SECRET", default="")
MPESA_BUSINESS_SHORTCODE = env("MPESA_BUSINESS_SHORTCODE", default="")
MPESA_PASSKEY = env("MPESA_PASSKEY", default="")
MPESA_CALLBACK_URL = env("MPESA_CALLBACK_URL", default="")
AT_USERNAME = env("AT_USERNAME", default="")
AT_API_KEY = env("AT_API_KEY", default="")

# --- Security headers that apply everywhere ------------------------------------------------
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "no-referrer"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# --- Observability (DESIGN §16) ------------------------------------------------------------------
# JSON to stdout with request IDs; the PHI scrubbing filter runs on every record.
LOGGING = logging_config(env("LOG_LEVEL", default="INFO"))
# Sentry-compatible DSN. Enabled only when set and allowed by the residency guard.
ERROR_TRACKER_DSN = env("ERROR_TRACKER_DSN", default="")
