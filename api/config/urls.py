"""URL configuration. Every API view is default-deny (apps.access.drf.PolicyPermission).

Removed in P1-UAC-03: the Django admin site (no audit, bypasses policies), the
unauthenticated legacy POS pages (`api/v1/mgt/`, `api/v1/sales/`), the duplicate
`api/v1/auth/` mount of the accounts routes and the empty procurement/suppliers routes.
"""

from django.urls import include, path

from apps.accounts.api.urls import auth_urlpatterns, me_urlpatterns
from apps.core import api_docs, health

urlpatterns = [
    path("healthz", health.healthz, name="healthz"),
    path("readyz", health.readyz, name="readyz"),
    path("api/schema/", api_docs.SchemaView.as_view(), name="schema"),
    path("api/docs/swagger/", api_docs.SwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/docs/redoc/", api_docs.RedocView.as_view(url_name="schema"), name="redoc"),
    path("api/v1/auth/", include(auth_urlpatterns)),
    path("api/v1/", include(me_urlpatterns)),
    path("api/v1/accounts/", include("apps.accounts.urls")),
    path("api/v1/facilities/", include("apps.facilities.api.urls")),
    path("api/v1/access/", include("apps.access.api.urls")),
    path("api/v1/patients/", include("apps.patients.api.urls")),
    path("api/v1/audit/", include("apps.audit.api.urls")),
    path("api/v1/analytics/", include("apps.analytics.urls")),
    path("api/v1/facility-ops/", include("apps.facility_ops.urls")),
    path("api/v1/ai/", include("apps.ai.urls")),
    path("api/v1/public/", include("apps.ai.urls_public")),
    path("api/v1/products/", include("apps.products.urls")),
    path("api/v1/warehouses/", include("apps.warehouses.urls")),
]

handler404 = "apps.core.problems.handler404"
handler500 = "apps.core.problems.handler500"
