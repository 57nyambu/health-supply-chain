"""Celery application. Settings come from Django settings with the CELERY_ prefix."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("afyasync")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
