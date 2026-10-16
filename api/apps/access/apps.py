from typing import Any

from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _sync_after_migrate(sender: AppConfig, **kwargs: Any) -> None:
    from apps.access.services import sync_access

    sync_access()


class AccessConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.access"
    verbose_name = "Access control"

    def ready(self) -> None:
        # Keep the database catalogue identical to the code after every migrate.
        post_migrate.connect(_sync_after_migrate, sender=self)
        # Audit events record the roles the actor held when acting.
        from apps.access import policies
        from apps.audit import context

        context.role_resolver = lambda actor: ",".join(policies.role_codes(actor))
        # Privileged role grants are activated by the maker-checker flow.
        from apps.access import approvals, assignments

        approvals.register_executor(assignments.GRANT_ACTION, assignments.activate_privileged_grant)
        # Service-account API keys appear as a security scheme in the OpenAPI document.
        from apps.access import schema  # noqa: F401
