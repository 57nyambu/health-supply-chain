from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        # Bind @shared_task to the project's Celery app in every process
        # (web, worker, beat) so .delay() uses the configured broker.
        import config.celery  # noqa: F401
