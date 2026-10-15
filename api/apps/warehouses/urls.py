from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import BinLocationViewSet, BranchViewSet, StockTransferViewSet, WarehouseViewSet

router = SimpleRouter()
router.register(r"branches", BranchViewSet)
router.register(r"warehouses", WarehouseViewSet, basename="warehouse")
router.register(r"bins", BinLocationViewSet, basename="binlocation")
router.register(r"transfers", StockTransferViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
