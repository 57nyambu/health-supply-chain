"""OpenAPI description of the service-account API key scheme (drf-spectacular extension)."""

from typing import Any

from drf_spectacular.extensions import OpenApiAuthenticationExtension

from apps.access.authentication import HEADER


class ApiKeyScheme(OpenApiAuthenticationExtension):  # type: ignore[no-untyped-call]
    target_class = "apps.access.authentication.ApiKeyAuthentication"
    name = "apiKey"

    def get_security_definition(self, auto_schema: Any) -> dict[str, str]:
        return {"type": "apiKey", "in": "header", "name": HEADER}
