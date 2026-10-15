"""Daily facility statistics and alerts for the legacy dashboards, scoped to the active facility.

Responses stay plain lists (no pagination) until the dashboards move to web/ (P1-WEB-06).
"""

from rest_framework import generics, serializers

from apps.access.drf import request_facility
from apps.audit.services import record
from apps.warehouses.selectors import facility_warehouses, warehouse_facility_id

from .models import FacilityAlert, FacilityDailyStats
from .serializers import FacilityAlertSerializer, FacilityDailyStatsSerializer


class FacilityStatsView(generics.ListCreateAPIView):
    serializer_class = FacilityDailyStatsSerializer
    pagination_class = None
    policy = {"GET": "operations.stats.read", "POST": "operations.stats.submit"}

    def get_queryset(self):
        queryset = FacilityDailyStats.objects.filter(
            warehouse__in=facility_warehouses(request_facility(self.request))
        ).select_related("warehouse")
        warehouse = self.request.query_params.get("warehouse")
        return queryset.filter(warehouse_id=warehouse) if warehouse else queryset

    def facility_of(self, obj):
        return warehouse_facility_id(obj.warehouse)

    def perform_create(self, serializer):
        warehouse = serializer.validated_data["warehouse"]
        if warehouse_facility_id(warehouse) != request_facility(self.request):
            raise serializers.ValidationError(
                {"warehouse": "Submit statistics for your own facility."}
            )
        stats = serializer.save()
        record(
            "operations.stats.submitted",
            self.request.user,
            stats,
            facility=request_facility(self.request),
            detail={"date": stats.date},
        )


class FacilityAlertsView(generics.ListAPIView):
    serializer_class = FacilityAlertSerializer
    pagination_class = None
    policy = "operations.alert.read"

    def get_queryset(self):
        return FacilityAlert.objects.filter(
            warehouse__in=facility_warehouses(request_facility(self.request))
        ).select_related("warehouse")

    def facility_of(self, obj):
        return warehouse_facility_id(obj.warehouse)
