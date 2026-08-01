import os
from pathlib import Path
from datetime import timedelta
from xml.parsers.expat import model

import environ
from celery.schedules import crontab

env = environ.Env(DEBUG=(bool, False))

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))


def _csv_env(name, default=""):
    raw = env(name, default=default)
    return [part.strip() for part in raw.split(',') if part.strip()]


def clean_database_config(database_config):
    if not isinstance(database_config, dict):
        return database_config

    cleaned_config = dict(database_config)
    cleaned_config.pop('schema', None)

    options = cleaned_config.get('OPTIONS')
    if isinstance(options, dict):
        cleaned_options = dict(options)
        cleaned_options.pop('schema', None)
        cleaned_config['OPTIONS'] = cleaned_options

    return cleaned_config


# Security / host configuration
SECRET_KEY = env('DJANGO_SECRET_KEY', default=env('SECRET_KEY', default='unsafe-dev-secret'))
DEBUG = env('DJANGO_DEBUG', default=env('DEBUG', default=False))
ALLOWED_HOSTS = _csv_env('DJANGO_ALLOWED_HOSTS', default='localhost,127.0.0.1')
CORS_ALLOWED_ORIGINS = _csv_env(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5500,http://127.0.0.1:5500',
)
CORS_ALLOW_CREDENTIALS = True

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
    'apps.core',
    'apps.accounts',
    'apps.products',
    'apps.suppliers',
    'apps.warehouses',
    'apps.sales.apps.SalesConfig',
    'apps.procurement',
    'apps.integrations',
    'apps.analytics',
    'apps.facility_ops',
    'apps.ai',
]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'apps.ai.authentication.PublicAPIKeyAuth',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Inventory System API Documentation',
    'DESCRIPTION': 'Realtime Inventory Management System',
    'VERSION': '1.0.0',
    'SERVER_INCLUDE_SCHEMA': False,
}

APPEND_SLASH = True

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env('JWT_ACCESS_LIFETIME_MIN', default=15)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env('JWT_REFRESH_LIFETIME_DAYS', default=7)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'root.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'root.wsgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# Celery configuration
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_BEAT_SCHEDULE = {
    'generate-daily-reports': {
        'task': 'apps.analytics.tasks.generate_daily_sales_report',
        'schedule': crontab(hour=0, minute=0),
    },
    'flag-underperforming-facilities': {
        'task': 'apps.facility_ops.tasks.flag_underperforming_facilities',
        'schedule': crontab(minute='*/30'),
    },
}

AUTH_USER_MODEL = 'accounts.User'

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [BASE_DIR / 'static']

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Security hardening
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True

# Email configuration (notifications run on email for this build)
NOTIFICATION_CHANNEL = env('NOTIFICATION_CHANNEL', default='email').lower()
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='localhost')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='alerts@afyasyc.dima.co.ke')

# Smart Health / Gemma config
GEMMA_API_KEY = env('GEMMA_API_KEY', default='')
GEMMA_MODEL_ASSISTANT = env('GEMMA_MODEL_ASSISTANT', default='gemma-4-4b-it')
GEMMA_MODEL_VISION = env('GEMMA_MODEL_VISION', default='gemma-4-12b-it')
GEMMA_CACHE_TTL_SECONDS = env.int('GEMMA_CACHE_TTL_SECONDS', default=1200)
PUBLIC_API_KEY = env('PUBLIC_API_KEY', default='')

# Optional providers retained for later enablement
RESEND_KEY = env('INVENTORY_RESEND_KEY', default='')
MPESA_CONSUMER_KEY = env('MPESA_CONSUMER_KEY', default='')
MPESA_CONSUMER_SECRET = env('MPESA_CONSUMER_SECRET', default='')
MPESA_BUSINESS_SHORTCODE = env('MPESA_BUSINESS_SHORTCODE', default='')
MPESA_PASSKEY = env('MPESA_PASSKEY', default='')
MPESA_CALLBACK_URL = env('MPESA_CALLBACK_URL', default='')
AT_USERNAME = env('AT_USERNAME', default='')
AT_API_KEY = env('AT_API_KEY', default='')
SITE_NAME = env('SITE_NAME', default='AfyaSync')