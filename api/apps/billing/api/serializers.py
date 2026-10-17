from typing import Any

from rest_framework import serializers

from apps.billing.models import PriceList, PriceListItem, Service


class ServiceSerializer(serializers.ModelSerializer[Service]):
    class Meta:
        model = Service
        fields = [
            "id",
            "code",
            "name",
            "kind",
            "department",
            "revenue_code",
            "sha_interventions",
            "etims_item_code",
            "status",
        ]
        read_only_fields = fields


class ServiceRequestSerializer(serializers.Serializer[Any]):
    """A new service waits for the finance manager's approval (maker-checker)."""

    code = serializers.CharField(max_length=40)
    name = serializers.CharField(max_length=160)
    kind = serializers.ChoiceField(choices=Service.Kind.choices)
    department = serializers.IntegerField(required=False, allow_null=True, default=None)
    revenue_code = serializers.CharField(
        max_length=20, required=False, allow_blank=True, default=""
    )
    sha_interventions = serializers.ListField(
        child=serializers.CharField(max_length=40), required=False, default=list
    )
    etims_item_code = serializers.CharField(
        max_length=40, required=False, allow_blank=True, default=""
    )
    cash_price = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=0, required=False, allow_null=True, default=None
    )
    reason = serializers.CharField(max_length=255)


class ServiceUpdateSerializer(serializers.Serializer[Any]):
    name = serializers.CharField(max_length=160, required=False)
    department = serializers.IntegerField(required=False, allow_null=True)
    revenue_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    sha_interventions = serializers.ListField(
        child=serializers.CharField(max_length=40), required=False
    )
    etims_item_code = serializers.CharField(max_length=40, required=False, allow_blank=True)


class ServiceStatusSerializer(serializers.Serializer[Any]):
    active = serializers.BooleanField()
    reason = serializers.CharField(max_length=255)


class PriceListSerializer(serializers.ModelSerializer[PriceList]):
    basis = serializers.CharField(read_only=True)
    payer_name = serializers.CharField(source="payer.name", read_only=True, default=None)
    scheme_name = serializers.CharField(source="scheme.name", read_only=True, default=None)

    class Meta:
        model = PriceList
        fields = [
            "id",
            "code",
            "name",
            "basis",
            "payer",
            "payer_name",
            "scheme",
            "scheme_name",
            "active",
        ]
        read_only_fields = fields


class PriceListCreateSerializer(serializers.Serializer[Any]):
    code = serializers.SlugField(max_length=40)
    name = serializers.CharField(max_length=120)
    payer = serializers.UUIDField(required=False, allow_null=True, default=None)
    scheme = serializers.UUIDField(required=False, allow_null=True, default=None)


class PriceItemSerializer(serializers.ModelSerializer[PriceListItem]):
    service_code = serializers.CharField(source="service.code", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = PriceListItem
        fields = [
            "id",
            "service",
            "service_code",
            "service_name",
            "price",
            "effective_from",
            "effective_to",
            "approval",
        ]
        read_only_fields = fields


class PriceChangeSerializer(serializers.Serializer[Any]):
    service = serializers.UUIDField()
    price = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0)
    effective_from = serializers.DateField(required=False, allow_null=True, default=None)
    reason = serializers.CharField(max_length=255)


class ApprovalRefSerializer(serializers.Serializer[Any]):
    approval_id = serializers.UUIDField()
    status = serializers.CharField()


class QuoteQuerySerializer(serializers.Serializer[Any]):
    service = serializers.UUIDField()
    scheme = serializers.UUIDField(required=False, allow_null=True, default=None)
    on = serializers.DateField(required=False, allow_null=True, default=None)


class QuoteSerializer(serializers.Serializer[Any]):
    service = serializers.UUIDField(source="service_id")
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    basis = serializers.CharField()
    price_list = serializers.UUIDField(source="price_list_id")
