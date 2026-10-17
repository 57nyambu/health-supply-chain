from django.apps import AppConfig


class EtimsConfig(AppConfig):
    """KRA eTIMS invoice transmission behind ETIMS_MODE (DESIGN §10; P3-TAX-01)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.etims"
    label = "etims"
