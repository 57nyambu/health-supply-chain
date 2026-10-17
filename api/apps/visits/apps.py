from django.apps import AppConfig


class VisitsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.visits"
    label = "visits"

    def ready(self) -> None:
        from apps.visits import gates

        gates.register_executors()
