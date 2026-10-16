from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.documents"
    verbose_name = "Documents"

    def ready(self) -> None:
        # Refuse to start (strict) or disable S3 (warn) when the bucket is outside the
        # residency allowlist (docs/integrations/STORAGE.md §2).
        from apps.documents.storage import check_residency

        check_residency()
