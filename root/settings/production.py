import dj_database_url
from .base import *

# Set DEBUG to False for production
DEBUG = False

# Allowed hosts come from DJANGO_ALLOWED_HOSTS in .env.

# Database settings
DATABASES = {
    'default': dj_database_url.config(
        default='postgres://postgres:postgres@localhost:5432/afyasync',
        conn_max_age=600,
        ssl_require=False,
    )
}

DATABASES['default'] = clean_database_config(DATABASES['default'])

# Static and media files
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT = BASE_DIR / 'media'

STATIC_URL = '/static/'
MEDIA_URL = '/media/'

# Logging: Set the level to DEBUG for more detailed logs (can change to ERROR after resolving issues)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "DEBUG",  # Changed to DEBUG for production logs
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "debug.log",  # Store logs in debug.log
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": "DEBUG",  # Set to DEBUG for detailed logs
            "propagate": True,
        },
    },
}

# Security settings: SSL/TLS headers for reverse proxies
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Secure cookies: Ensure CSRF and session cookies are transmitted securely over HTTPS
CSRF_COOKIE_SECURE = True # Enable this for production
SESSION_COOKIE_SECURE = True # Enable this for production
CSRF_COOKIE_SAMESITE = 'Lax'

# Enforce HTTPS and prevent HTTP traffic
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0  # recommended 3600 in production
SECURE_HSTS_INCLUDE_SUBDOMAINS = False # Enable HSTS for subdomains enable in production
SECURE_HSTS_PRELOAD = False # Enable HSTS Preload in production

# Optional but recommended: Ensure cookies are only accessible over HTTPS
SECURE_HTTP_ONLY = True

# Additional headers for better security
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
