"""WSGI entry point. Defaults to production settings so a missing DJANGO_ENV fails safe."""

from django.core.wsgi import get_wsgi_application

from config.env import configure_settings_module

configure_settings_module(default="prod")

application = get_wsgi_application()
