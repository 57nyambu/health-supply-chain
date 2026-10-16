from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"

    def ready(self):
        from apps.access import policies
        from apps.accounts import sessions  # noqa: F401 - connects login/logout receivers
        from apps.accounts.licences import licence_ok

        # Clinical permissions need a valid licence (P1-UAC-07).
        policies.licence_checker = licence_ok
