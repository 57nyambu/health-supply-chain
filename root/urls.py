from django.contrib import admin
from django.urls import path, include
from django.contrib.admin.views.decorators import staff_member_required
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


urlpatterns = [
    path("api/schema/", staff_member_required(SpectacularAPIView.as_view()), name="schema"),
    path("api/docs/swagger/", staff_member_required(SpectacularSwaggerView.as_view(url_name="schema")), name="swagger-ui"),
    path("api/docs/redoc/", staff_member_required(SpectacularRedocView.as_view(url_name="schema")), name="redoc"),
    path('admin/', admin.site.urls),
    #path('', include('apps.core.urls')),
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/mgt/', include('apps.core.urls.mgt')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
    #path('api/v1/integrate/', include('apps.integrations.urls')),
    path('api/v1/procurement/', include('apps.procurement.urls')),
    path('api/v1/products/', include('apps.products.urls')),
    path('api/v1/sales/', include('apps.sales.urls')),
    path('api/v1/suppliers/', include('apps.suppliers.urls')),
    path('api/v1/warehouses/', include('apps.warehouses.urls')),
]
