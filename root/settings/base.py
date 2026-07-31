import os
from pathlib import Path
from datetime import timedelta
import psycopg2
import environ
from celery.schedules import crontab

env = environ.Env(DEBUG=(bool, False) )

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

environ.Env.read_env(os.path.join(BASE_DIR, '.env'))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY=env('SECRET_KEY')

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
    'apps.sales.apps.SalesConfig',  # (POS, Invoices, M-Pesa)
    'apps.procurement',
    'apps.integrations',  # (M-Pesa, SMS, ERP)
    'apps.analytics',

]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',  # Optional: for form data
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Inventory System Api Documentation",
    "DESCRIPTION": "Realtime Inventory Management System",
    "VERSION": "1.0.0",
    "SERVER_INCLUDE_SCHEMA": False,
}

APPEND_SLASH = True

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=3),  
    'REFRESH_TOKEN_LIFETIME': timedelta(days=10),    
    'ROTATE_REFRESH_TOKENS': True,                  # Issue a new refresh token on every use
    'BLACKLIST_AFTER_ROTATION': True,               # Blacklist old refresh tokens if rotated
    'ALGORITHM': 'HS256',                           # Default is HS256, but you can switch to RS256 for RSA keys
    'SIGNING_KEY': SECRET_KEY,                      # Default is Django's SECRET_KEY
    'AUTH_HEADER_TYPES': ('Bearer',),               # Authorization: Bearer <token>
    'USER_ID_FIELD': 'id',                          # Field to identify the user
    'USER_ID_CLAIM': 'user_id',                     # Claim name in the token
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),  # Token classes
    'TOKEN_TYPE_CLAIM': 'token_type',               # Token type claim
}


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  # Add this line
    
]

ROOT_URLCONF = 'root.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Directory for custom templates
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


# https://docs.djangoproject.com/en/5.1/ref/settings/#databases# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Nairobi'

USE_I18N = True

USE_TZ = True

# Celery configuration
CELERY_BEAT_SCHEDULE = {
    'generate-daily-reports': {
        'task': 'apps.analytics.tasks.generate_daily_sales_report',
        'schedule': crontab(hour=0, minute=0),  # Midnight Nairobi time
    },
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# settings.py
AUTH_USER_MODEL = 'accounts.User'

# Email conf
RESEND_KEY = env('INVENTORY_RESEND_KEY')
# Security settings
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True

DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')
# Static files configuration
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# M-Pesa Daraja API (Sandbox)
MPESA_CONSUMER_KEY = env('MPESA_CONSUMER_KEY')
MPESA_CONSUMER_SECRET = env('MPESA_CONSUMER_SECRET')
MPESA_BUSINESS_SHORTCODE = env('MPESA_BUSINESS_SHORTCODE')
MPESA_PASSKEY = env('MPESA_PASSKEY')
MPESA_CALLBACK_URL = env('MPESA_CALLBACK_URL')
# AfricasTalking SMS
AT_USERNAME = env('AT_USERNAME')
AT_API_KEY = env('AT_API_KEY')
SITE_NAME = env('SITE_NAME')