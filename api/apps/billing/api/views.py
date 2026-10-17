"""Service catalogue and price list API (P2-BIL-01): thin views over billing.services."""

from typing import Any

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.drf import require_facility
from apps.billing import services
from apps.billing.models import PriceList, PriceListItem, Service
from apps.core.pagination import CataloguePagination
from apps.facilities.models import Department
from apps.insurance.models import Payer
from apps.insurance.selectors import active_schemes

from .serializers import (
    ApprovalRefSerializer,
    PriceChangeSerializer,
    PriceItemSerializer,
    PriceListCreateSerializer,
    PriceListSerializer,
    QuoteQuerySerializer,
    QuoteSerializer,
    ServiceRequestSerializer,
    ServiceSerializer,
    ServiceStatusSerializer,
    ServiceUpdateSerializer,
)

READ = "billing.service.read"
MANAGE = "billing.pricelist.manage"


def _department(facility_id: int, department_id: Any) -> Department | None:
    if department_id is None:
        return None
    department = Department.objects.filter(pk=department_id, facility_id=facility_id).first()
    if department is None:
        raise ValidationError({"department": "Choose a department of this facility."})
    return department


def _approval_response(request: Any) -> Response:
    return Response(
        ApprovalRefSerializer({"approval_id": request.pk, "status": request.status}).data,
        status=status.HTTP_202_ACCEPTED,
    )


class ServiceViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet[Service]
):
    """The facility's service catalogue. New services wait for finance approval."""

    serializer_class = ServiceSerializer
    queryset = Service.objects.none()
    pagination_class = CataloguePagination
    policy = {
        "list": READ,
        "retrieve": READ,
        "create": MANAGE,
        "partial_update": MANAGE,
        "set_status": MANAGE,
    }
    http_method_names = ["get", "post", "patch"]

    def get_queryset(self) -> QuerySet[Service]:
        rows = Service.objects.filter(facility_id=require_facility(self.request))
        kind = self.request.query_params.get("kind")
        if kind:
            rows = rows.filter(kind=kind)
        term = (self.request.query_params.get("q") or "").strip()
        if term:
            rows = rows.filter(name__icontains=term) | rows.filter(code__icontains=term)
        if self.request.query_params.get("active") == "true":
            rows = rows.filter(status=Service.Status.ACTIVE)
        return rows.order_by("kind", "name")

    @extend_schema(request=ServiceRequestSerializer, responses={202: ApprovalRefSerializer})
    def create(self, request: Request) -> Response:
        serializer = ServiceRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        facility_id = require_facility(request)
        data["department"] = _department(facility_id, data.get("department"))
        approval = services.request_new_service(facility=facility_id, actor=request.user, **data)
        return _approval_response(approval)

    @extend_schema(request=ServiceUpdateSerializer, responses=ServiceSerializer)
    def partial_update(self, request: Request, pk: str | None = None) -> Response:
        serializer = ServiceUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changes = dict(serializer.validated_data)
        service = self.get_object()
        if "department" in changes:
            changes["department"] = _department(service.facility_id, changes["department"])
        updated = services.update_service(service, actor=request.user, changes=changes)
        return Response(ServiceSerializer(updated).data)

    @extend_schema(request=ServiceStatusSerializer, responses=ServiceSerializer)
    @action(detail=True, methods=["post"], url_path="status")
    def set_status(self, request: Request, pk: str | None = None) -> Response:
        serializer = ServiceStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = services.set_service_status(
            self.get_object(), actor=request.user, **serializer.validated_data
        )
        return Response(ServiceSerializer(updated).data)


class PriceListViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet[PriceList]
):
    serializer_class = PriceListSerializer
    queryset = PriceList.objects.none()
    pagination_class = None
    policy = {
        "list": READ,
        "retrieve": READ,
        "create": MANAGE,
        "items": READ,
        "change_price": MANAGE,
    }

    def get_queryset(self) -> QuerySet[PriceList]:
        return PriceList.objects.filter(facility_id=require_facility(self.request)).select_related(
            "payer", "scheme"
        )

    @extend_schema(request=PriceListCreateSerializer, responses={201: PriceListSerializer})
    def create(self, request: Request) -> Response:
        serializer = PriceListCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        payer = scheme = None
        payer_id = data.pop("payer")
        if payer_id:
            payer = Payer.objects.filter(pk=payer_id, active=True).first()
            if payer is None:
                raise ValidationError({"payer": "Choose an active payer."})
        scheme_id = data.pop("scheme")
        if scheme_id:
            scheme = active_schemes().filter(pk=scheme_id).first()
            if scheme is None:
                raise ValidationError({"scheme": "Choose an active scheme."})
        price_list = services.create_price_list(
            facility=require_facility(request),
            actor=request.user,
            payer=payer,
            scheme=scheme,
            **data,
        )
        return Response(PriceListSerializer(price_list).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses=PriceItemSerializer(many=True))
    @action(detail=True, methods=["get"])
    def items(self, request: Request, pk: str | None = None) -> Response:
        """Price history of this list, newest first per service."""
        rows = PriceListItem.objects.filter(price_list=self.get_object()).select_related("service")
        if request.query_params.get("current") == "true":
            rows = rows.filter(effective_to__isnull=True)
        return Response(
            PriceItemSerializer(rows.order_by("service__name", "-effective_from"), many=True).data
        )

    @extend_schema(request=PriceChangeSerializer, responses={202: ApprovalRefSerializer})
    @action(detail=True, methods=["post"], url_path="prices")
    def change_price(self, request: Request, pk: str | None = None) -> Response:
        serializer = PriceChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        price_list = self.get_object()
        service = Service.objects.filter(
            pk=data["service"], facility_id=price_list.facility_id
        ).first()
        if service is None:
            raise ValidationError({"service": "Choose a service of this facility."})
        approval = services.request_price_change(
            price_list=price_list,
            service=service,
            price=data["price"],
            effective_from=data["effective_from"],
            actor=request.user,
            reason=data["reason"],
        )
        return _approval_response(approval)


class QuoteView(APIView):
    """The price that applies to a service for a scheme (or cash) on a date."""

    policy = READ

    @extend_schema(parameters=[QuoteQuerySerializer], responses=QuoteSerializer)
    def get(self, request: Request) -> Response:
        query = QuoteQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        service = Service.objects.filter(
            pk=data["service"], facility_id=require_facility(request)
        ).first()
        if service is None:
            raise ValidationError({"service": "Choose a service of this facility."})
        scheme = None
        if data["scheme"]:
            scheme = active_schemes().filter(pk=data["scheme"]).first()
            if scheme is None:
                raise ValidationError({"scheme": "Choose an active scheme."})
        quote = services.resolve_price(service, scheme=scheme, on=data["on"])
        return Response(QuoteSerializer(quote).data)
