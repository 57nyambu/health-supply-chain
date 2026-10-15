"""Facility setup API (P1-FAC-01): thin views over apps.facilities.services."""

from typing import Any

from django.db.models import Count, Q, QuerySet
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from apps.access import policies
from apps.access.drf import request_facility
from apps.facilities import services
from apps.facilities.models import Bed, Department, Facility, ServicePoint, Ward

from .serializers import (
    BedSerializer,
    BedStatusSerializer,
    DepartmentSerializer,
    FacilitySerializer,
    ServicePointSerializer,
    WardSerializer,
)

READ = "facilities.location.read"
MANAGE = "facilities.location.manage"
LAYOUT_POLICY = {"list": READ, "retrieve": READ, "create": MANAGE, "partial_update": MANAGE}


class FacilityViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet[Facility],
):
    """Facilities the user holds a role in; identifiers and settings edited by facility admins."""

    serializer_class = FacilitySerializer
    queryset = Facility.objects.none()
    http_method_names = ["get", "patch"]
    policy = {
        "list": "facilities.facility.read",
        "retrieve": "facilities.facility.read",
        "partial_update": "facilities.facility.manage",
    }

    def get_queryset(self) -> QuerySet[Facility]:
        return Facility.objects.filter(pk__in=policies.facilities_for(self.request.user))

    def facility_of(self, obj: Facility) -> int:
        return obj.pk

    def perform_update(self, serializer: Any) -> None:
        facility = self.get_object()
        serializer.instance = services.update_facility(
            facility, actor=self.request.user, **serializer.validated_data
        )


class LayoutViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet[Any],
):
    """Shared behaviour: scoped to the request facility; PATCH {active} (de)activates."""

    http_method_names = ["get", "post", "patch"]
    policy = LAYOUT_POLICY

    def facility_id(self) -> int:
        value = request_facility(self.request)
        if value is None:  # PolicyPermission already required a facility
            raise PermissionDenied()
        return value

    def facility(self) -> Facility:
        return Facility.objects.get(pk=self.facility_id())

    def perform_update(self, serializer: Any) -> None:
        data = dict(serializer.validated_data)
        instance = serializer.instance
        if "active" in data:
            instance = services.set_active(
                instance, actor=self.request.user, active=data.pop("active")
            )
        if data:
            instance = services.update_layout(instance, actor=self.request.user, **data)
        serializer.instance = instance


class DepartmentViewSet(LayoutViewSet):
    serializer_class = DepartmentSerializer
    queryset = Department.objects.none()

    def get_queryset(self) -> QuerySet[Department]:
        return Department.objects.filter(facility_id=self.facility_id())

    def perform_create(self, serializer: Any) -> None:
        serializer.instance = services.create_department(
            facility=self.facility(), actor=self.request.user, **serializer.validated_data
        )


class ServicePointViewSet(LayoutViewSet):
    serializer_class = ServicePointSerializer
    queryset = ServicePoint.objects.none()

    def get_queryset(self) -> QuerySet[ServicePoint]:
        queryset = ServicePoint.objects.filter(facility_id=self.facility_id())
        kind = self.request.query_params.get("kind")
        return queryset.filter(kind=kind) if kind else queryset

    def perform_create(self, serializer: Any) -> None:
        data = dict(serializer.validated_data)
        data.pop("active", None)
        serializer.instance = services.create_service_point(
            facility=self.facility(), actor=self.request.user, **data
        )


class WardViewSet(LayoutViewSet):
    serializer_class = WardSerializer
    queryset = Ward.objects.none()

    def get_queryset(self) -> QuerySet[Ward]:
        return Ward.objects.filter(facility_id=self.facility_id()).annotate(
            beds_total=Count("beds", filter=Q(beds__active=True)),
            beds_available=Count(
                "beds", filter=Q(beds__active=True, beds__status=Bed.Status.AVAILABLE)
            ),
        )

    def perform_create(self, serializer: Any) -> None:
        data = dict(serializer.validated_data)
        data.pop("active", None)
        serializer.instance = services.create_ward(
            facility=self.facility(), actor=self.request.user, **data
        )


class BedViewSet(LayoutViewSet):
    serializer_class = BedSerializer
    queryset = Bed.objects.none()
    policy = {**LAYOUT_POLICY, "set_status": "facilities.bed.update_status"}

    def get_queryset(self) -> QuerySet[Bed]:
        queryset = Bed.objects.filter(ward__facility_id=self.facility_id()).select_related("ward")
        ward = self.request.query_params.get("ward")
        return queryset.filter(ward_id=ward) if ward else queryset

    def facility_of(self, obj: Bed) -> int:
        return obj.ward.facility_id

    def perform_create(self, serializer: Any) -> None:
        ward = serializer.validated_data["ward"]
        if ward.facility_id != self.facility_id():
            raise ValidationError({"ward": "Choose a ward in your facility."})
        serializer.instance = services.create_bed(
            ward=ward, actor=self.request.user, code=serializer.validated_data["code"]
        )

    @action(detail=True, methods=["post"], url_path="status", serializer_class=BedStatusSerializer)
    def set_status(self, request: Request, pk: str | None = None) -> Response:
        bed = self.get_object()
        serializer = BedStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bed = services.set_bed_status(
            bed, actor=request.user, status=serializer.validated_data["status"]
        )
        return Response(BedSerializer(bed).data)
