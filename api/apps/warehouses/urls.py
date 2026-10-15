from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BranchViewSet,
    WarehouseViewSet,
    BinLocationViewSet,
    StockTransferViewSet
)

router = DefaultRouter()
router.register(r'branches', BranchViewSet)
router.register(r'warehouses', WarehouseViewSet, basename='warehouse')
router.register(r'bins', BinLocationViewSet, basename='binlocation')
router.register(r'transfers', StockTransferViewSet)

urlpatterns = [
    path('', include(router.urls)),
]