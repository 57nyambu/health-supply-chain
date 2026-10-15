"""OpenAPI schema and documentation pages, behind the default-deny policy."""

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.access.drf import PolicyPermission

SCHEMA_POLICY = "admin.api.read_schema"


class SchemaView(SpectacularAPIView):
    permission_classes = [PolicyPermission]
    policy = SCHEMA_POLICY


class SwaggerView(SpectacularSwaggerView):
    permission_classes = [PolicyPermission]
    policy = SCHEMA_POLICY


class RedocView(SpectacularRedocView):
    permission_classes = [PolicyPermission]
    policy = SCHEMA_POLICY
