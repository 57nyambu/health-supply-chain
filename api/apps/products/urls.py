from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import CategoryViewSet, InventoryViewSet, ProductImageViewSet, ProductViewSet

router = SimpleRouter()
router.register(r"categories", CategoryViewSet)
router.register(r"products", ProductViewSet)
router.register(r"inventory", InventoryViewSet, basename="inventory")

# Nested router for product images
product_router = SimpleRouter()
product_router.register(r"images", ProductImageViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("products/<int:product_pk>/", include(product_router.urls)),
]
