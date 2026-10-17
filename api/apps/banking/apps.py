from django.apps import AppConfig


class BankingConfig(AppConfig):
    """Equity (Jenga), KCB (Buni), Pesapal and PDQ: vendor clients, notifications and, from
    stage B, the payments provider port (PAYMENTS.md §4-7; SEAMS §5-6)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.banking"
    label = "banking"

    def ready(self) -> None:
        from apps.banking import notifications

        notifications.register()
