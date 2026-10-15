"""Audit viewer for the DPO and auditors (DESIGN §7.11). Looking at the log is audited too."""

from typing import Any

from django.db.models import QuerySet
from rest_framework import mixins, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from apps.access.drf import request_facility
from apps.audit.models import AuditEvent
from apps.audit.services import record
from apps.core.pagination import LargeListCursorPagination

from .serializers import AuditEventSerializer, AuditFilterSerializer


class AuditPagination(LargeListCursorPagination):
    ordering = "-ts"


class AuditEventViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet[AuditEvent]
):
    serializer_class = AuditEventSerializer
    pagination_class = AuditPagination
    queryset = AuditEvent.objects.none()
    policy = "audit.log.read"

    def facility_of(self, obj: AuditEvent) -> int | None:
        return request_facility(self.request)  # queryset holds this facility + system events

    def filters(self) -> dict[str, Any]:
        serializer = AuditFilterSerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)
        return dict(serializer.validated_data)

    def get_queryset(self) -> QuerySet[AuditEvent]:
        facility_id = request_facility(self.request)
        queryset = AuditEvent.objects.filter(facility_id__in=[facility_id or -1, 0])
        if self.action != "list":
            return queryset
        wanted = self.filters()
        lookups = {
            "actor": "actor_id",
            "patient": "patient_id",
            "resource_type": "resource_type",
            "outcome": "outcome",
            "date_from": "chain_date__gte",
            "date_to": "chain_date__lte",
        }
        for name, lookup in lookups.items():
            if name in wanted:
                queryset = queryset.filter(**{lookup: wanted[name]})
        if "action" in wanted:
            action = wanted["action"]
            queryset = (
                queryset.filter(action__startswith=action[:-1])
                if action.endswith("*")
                else queryset.filter(action=action)
            )
        return queryset

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        response = super().list(request, *args, **kwargs)
        record(
            "audit.log.viewed",
            request.user,
            None,
            facility=request_facility(request),
            detail={"filters": {key: str(value) for key, value in self.filters().items()}},
            severity="notice",
        )
        return response

    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        response = super().retrieve(request, *args, **kwargs)
        record(
            "audit.log.viewed",
            request.user,
            ("audit.auditevent", kwargs.get("pk", "")),
            facility=request_facility(request),
            severity="notice",
        )
        return response
