"""Celery application. Settings come from Django settings with the CELERY_ prefix."""

from celery import Celery

from config.env import configure_settings_module

configure_settings_module(default="dev")

app = Celery("afyasync")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
