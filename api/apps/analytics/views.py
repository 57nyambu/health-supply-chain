from rest_framework import generics

from apps.access.drf import request_facility
from apps.warehouses.selectors import facility_warehouses, warehouse_facility_id

from .models import RTInventoryAlert
from .serializers import RTInventoryAlertSerializer


class InventoryAlertsView(generics.ListAPIView):
    """Low-stock alerts for the stores of the request's facility (plain list for legacy dashboards)."""

    serializer_class = RTInventoryAlertSerializer
    pagination_class = None
    policy = "inventory.alert.read"

    def get_queryset(self):
        warehouses = facility_warehouses(request_facility(self.request))
        return RTInventoryAlert.objects.filter(warehouse__in=warehouses).select_related(
            "product", "warehouse"
        )

    def facility_of(self, obj):
        return warehouse_facility_id(obj.warehouse)
