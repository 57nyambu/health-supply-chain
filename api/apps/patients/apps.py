from django.apps import AppConfig


class PatientsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.patients"
    verbose_name = "Patients"

    def ready(self) -> None:
        from apps.patients.services import register_executors

        register_executors()
