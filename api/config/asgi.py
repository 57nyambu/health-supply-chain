"""ASGI entry point. Defaults to production settings so a missing DJANGO_ENV fails safe."""

from django.core.asgi import get_asgi_application

from config.env import configure_settings_module

configure_settings_module(default="prod")

application = get_asgi_application()
