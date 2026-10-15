"""Product catalogue (organisation-wide) and stock levels (per facility store)."""

from django.shortcuts import get_object_or_404
from rest_framework import mixins, serializers, viewsets

from apps.access.drf import request_facility
from apps.audit.services import record
from apps.warehouses.selectors import facility_warehouses, warehouse_facility_id

from .models import Category, Inventory, Product, ProductImage
from .serializers import (
    CategorySerializer,
    InventorySerializer,
    ProductCreateSerializer,
    ProductImageSerializer,
    ProductSerializer,
)

READ = "inventory.product.read"
MANAGE = "inventory.product.manage"


class AuditedCatalogueMixin:
    """Audit catalogue changes on the acting facility's chain."""

    audit_resource = "catalogue"

    def perform_create(self, serializer):
        instance = serializer.save()
        record(
            f"inventory.{self.audit_resource}.created",
            self.request.user,
            instance,
            facility=request_facility(self.request),
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        record(
            f"inventory.{self.audit_resource}.updated",
            self.request.user,
            instance,
            facility=request_facility(self.request),
            detail={"fields": sorted(serializer.validated_data)},
        )


class CategoryViewSet(
    AuditedCatalogueMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    audit_resource = "category"
    policy = {
        "list": READ,
        "retrieve": READ,
        "create": MANAGE,
        "update": MANAGE,
        "partial_update": MANAGE,
    }


class ProductViewSet(AuditedCatalogueMixin, viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    audit_resource = "product"
    policy = {
        "list": READ,
        "retrieve": READ,
        "create": MANAGE,
        "update": MANAGE,
        "partial_update": MANAGE,
        "destroy": MANAGE,
    }

    def get_serializer_class(self):
        if self.action == "create":
            return ProductCreateSerializer
        return ProductSerializer

    def perform_destroy(self, instance):
        """Products are retired, never deleted."""
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        record(
            "inventory.product.retired",
            self.request.user,
            instance,
            facility=request_facility(self.request),
        )


class ProductImageViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ProductImage.objects.none()
    serializer_class = ProductImageSerializer
    policy = {"list": READ, "retrieve": READ, "create": MANAGE, "destroy": MANAGE}

    def get_queryset(self):
        return ProductImage.objects.filter(product_id=self.kwargs["product_pk"])

    def perform_create(self, serializer):
        product = get_object_or_404(Product, pk=self.kwargs["product_pk"])
        serializer.save(product=product)


class InventoryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Stock levels in the stores of the request's facility."""

    queryset = Inventory.objects.none()
    serializer_class = InventorySerializer
    policy = {
        "list": "inventory.stock.read",
        "retrieve": "inventory.stock.read",
        "create": "inventory.stock.adjust",
        "update": "inventory.stock.adjust",
        "partial_update": "inventory.stock.adjust",
    }

    def get_queryset(self):
        warehouses = facility_warehouses(request_facility(self.request))
        queryset = Inventory.objects.filter(warehouse__in=warehouses).select_related(
            "product", "warehouse"
        )
        warehouse_id = self.request.query_params.get("warehouse")
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        return queryset

    def facility_of(self, obj):
        return warehouse_facility_id(obj.warehouse)

    def _check_store(self, serializer):
        warehouse = serializer.validated_data.get("warehouse")
        if (
            warehouse is not None
            and not facility_warehouses(request_facility(self.request))
            .filter(pk=warehouse.pk)
            .exists()
        ):
            raise serializers.ValidationError({"warehouse": "Choose a store in your facility."})

    def perform_create(self, serializer):
        self._check_store(serializer)
        instance = serializer.save()
        record(
            "inventory.stock.adjusted",
            self.request.user,
            instance,
            facility=request_facility(self.request),
            detail={"quantity": instance.quantity},
        )

    def perform_update(self, serializer):
        self._check_store(serializer)
        instance = serializer.save()
        record(
            "inventory.stock.adjusted",
            self.request.user,
            instance,
            facility=request_facility(self.request),
            detail={"quantity": instance.quantity},
        )
