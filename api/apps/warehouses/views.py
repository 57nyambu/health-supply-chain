"""Branches, stores (warehouses), bins and stock transfers, scoped to the active facility."""

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.access.drf import request_facility
from apps.audit.services import record
from apps.core.problems import Conflict, Forbidden

from .models import BinLocation, Branch, StockTransfer, Warehouse
from .selectors import (
    branch_facility_id,
    facility_branches,
    facility_warehouses,
    warehouse_facility_id,
)
from .serializers import (
    BinLocationSerializer,
    BranchSerializer,
    StockTransferCreateSerializer,
    StockTransferSerializer,
    WarehouseSerializer,
)

STORE_READ = "inventory.store.read"
STORE_MANAGE = "inventory.store.manage"
UPDATE_ACTIONS = ("update", "partial_update")


def _audit(request, action_name, instance, **detail):
    record(action_name, request.user, instance, facility=request_facility(request), detail=detail)


class BranchViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """The organisation unit behind the facility. New branches come with new facilities."""

    queryset = Branch.objects.none()
    serializer_class = BranchSerializer
    policy = {
        "list": STORE_READ,
        "retrieve": STORE_READ,
        "update": "inventory.branch.manage",
        "partial_update": "inventory.branch.manage",
    }

    def get_queryset(self):
        return facility_branches(request_facility(self.request)).filter(is_active=True)

    def facility_of(self, obj):
        return branch_facility_id(obj)

    def perform_update(self, serializer):
        branch = serializer.save()
        _audit(
            self.request,
            "inventory.branch.updated",
            branch,
            fields=sorted(serializer.validated_data),
        )


class FacilityStoreMixin:
    def _check_branch(self, serializer):
        branch = serializer.validated_data.get("branch")
        if branch is not None and branch_facility_id(branch) != request_facility(self.request):
            raise serializers.ValidationError({"branch": "Choose your facility's branch."})

    def _check_warehouse(self, serializer, field="warehouse"):
        warehouse = serializer.validated_data.get(field)
        if warehouse is not None and warehouse_facility_id(warehouse) != request_facility(
            self.request
        ):
            raise serializers.ValidationError({field: "Choose a store in your facility."})


class WarehouseViewSet(
    FacilityStoreMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Warehouse.objects.none()
    serializer_class = WarehouseSerializer
    policy = {
        "list": STORE_READ,
        "retrieve": STORE_READ,
        "create": STORE_MANAGE,
        "update": STORE_MANAGE,
        "partial_update": STORE_MANAGE,
    }

    def get_queryset(self):
        return facility_warehouses(request_facility(self.request)).select_related("branch")

    def facility_of(self, obj):
        return warehouse_facility_id(obj)

    def perform_create(self, serializer):
        self._check_branch(serializer)
        _audit(self.request, "inventory.store.created", serializer.save())

    def perform_update(self, serializer):
        self._check_branch(serializer)
        warehouse = serializer.save()
        _audit(
            self.request,
            "inventory.store.updated",
            warehouse,
            fields=sorted(serializer.validated_data),
        )


class BinLocationViewSet(
    FacilityStoreMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = BinLocation.objects.none()
    serializer_class = BinLocationSerializer
    policy = {
        "list": STORE_READ,
        "retrieve": STORE_READ,
        "create": STORE_MANAGE,
        "update": STORE_MANAGE,
        "partial_update": STORE_MANAGE,
    }

    def get_queryset(self):
        warehouses = facility_warehouses(request_facility(self.request))
        queryset = BinLocation.objects.filter(warehouse__in=warehouses).select_related("warehouse")
        warehouse_id = self.request.query_params.get("warehouse")
        return queryset.filter(warehouse_id=warehouse_id) if warehouse_id else queryset

    def facility_of(self, obj):
        return warehouse_facility_id(obj.warehouse)

    def perform_create(self, serializer):
        self._check_warehouse(serializer)
        _audit(self.request, "inventory.bin.created", serializer.save())

    def perform_update(self, serializer):
        self._check_warehouse(serializer)
        _audit(
            self.request,
            "inventory.bin.updated",
            serializer.save(),
            fields=sorted(serializer.validated_data),
        )


class StockTransferViewSet(
    FacilityStoreMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Transfers are records: created, approved by someone else, received — never edited."""

    queryset = StockTransfer.objects.none()
    policy = {
        "list": "inventory.transfer.read",
        "retrieve": "inventory.transfer.read",
        "create": "inventory.transfer.create",
        "approve": "inventory.transfer.approve",
        "complete": "inventory.transfer.receive",
    }

    def get_queryset(self):
        warehouses = facility_warehouses(request_facility(self.request))
        return StockTransfer.objects.filter(
            Q(from_warehouse__in=warehouses) | Q(to_warehouse__in=warehouses)
        ).select_related("product", "from_warehouse", "to_warehouse", "initiated_by")

    def facility_of(self, obj):
        return request_facility(self.request)  # the queryset already limits to this facility

    def get_serializer_class(self):
        if self.action == "create":
            return StockTransferCreateSerializer
        return StockTransferSerializer

    def perform_create(self, serializer):
        self._check_warehouse(serializer, "from_warehouse")
        transfer = serializer.save(initiated_by=self.request.user)
        _audit(self.request, "inventory.transfer.created", transfer, quantity=transfer.quantity)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        transfer = self.get_object()
        transfer = StockTransfer.objects.select_for_update().get(pk=transfer.pk)
        if transfer.initiated_by_id == request.user.pk:
            raise Forbidden("You cannot approve a transfer you requested.")
        if transfer.status != "PENDING":
            raise Conflict(f"The transfer is {transfer.get_status_display().lower()}.")
        transfer.status = "APPROVED"
        transfer.approved_by = request.user
        transfer.save(update_fields=["status", "approved_by", "updated_at"])
        _audit(request, "inventory.transfer.approved", transfer)
        return Response(StockTransferSerializer(transfer).data)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        transfer = self.get_object()
        transfer = StockTransfer.objects.select_for_update().get(pk=transfer.pk)
        if warehouse_facility_id(transfer.to_warehouse) != request_facility(request):
            raise Forbidden("Only the receiving facility can receive this transfer.")
        if transfer.status not in ("APPROVED", "IN_TRANSIT"):
            raise Conflict("Only approved transfers can be received.")
        transfer.status = "RECEIVED"
        transfer.verified_at = timezone.now()
        transfer.save(update_fields=["status", "verified_at", "updated_at"])
        _audit(request, "inventory.transfer.received", transfer)
        return Response(StockTransferSerializer(transfer).data)
