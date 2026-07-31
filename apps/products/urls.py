from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    ProductViewSet,
    ProductImageViewSet,
    InventoryViewSet
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'inventory', InventoryViewSet, basename='inventory')

# Nested router for product images
product_router = DefaultRouter()
product_router.register(r'images', ProductImageViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('products/<int:product_pk>/', include(product_router.urls)),
]