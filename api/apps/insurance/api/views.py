"""Payers, schemes and coverage API (seam between the parallel lanes, ADR-024)."""

from typing import Any

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from apps.access.drf import require_facility
from apps.access.roles import ChartAccess
from apps.insurance import selectors, services
from apps.insurance.models import Coverage, Scheme
from apps.patients import selectors as patient_selectors
from apps.patients.models import Patient

from .serializers import (
    CoverageCreateSerializer,
    CoverageQuerySerializer,
    CoverageSerializer,
    EndCoverageSerializer,
    SchemeSerializer,
)


class SchemeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet[Scheme]):
    """Active schemes a visit can be billed to; no scheme means cash / self-pay."""

    serializer_class = SchemeSerializer
    queryset = Scheme.objects.none()
    pagination_class = None
    policy = "insurance.payer.read"

    def get_queryset(self) -> QuerySet[Scheme]:
        return selectors.active_schemes()


class CoverageViewSet(viewsets.GenericViewSet[Coverage]):
    serializer_class = CoverageSerializer
    queryset = Coverage.objects.none()
    policy = {
        "list": "insurance.coverage.read",
        "create": "insurance.coverage.manage",
        "end": "insurance.coverage.manage",
    }

    def get_queryset(self) -> QuerySet[Coverage]:
        return Coverage.objects.filter(facility_id=require_facility(self.request))

    def _patient(self, patient_id: Any) -> Patient:
        patient = Patient.objects.filter(
            pk=patient_id, facility_id=require_facility(self.request)
        ).first()
        if patient is None:
            raise ValidationError({"patient": "Choose a patient of this facility."})
        return patient

    @extend_schema(parameters=[CoverageQuerySerializer], responses=CoverageSerializer(many=True))
    def list(self, request: Request) -> Response:
        """A patient's cover, current and ended (masked member numbers; an audited read)."""
        query = CoverageQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        patient = self._patient(query.validated_data["patient"])
        patient_selectors.open_record(
            request.user,
            patient,
            purpose=query.validated_data["purpose"],
            needed=ChartAccess.DEMOGRAPHICS,
            action="insurance.coverage.listed",
        )
        rows = selectors.coverages_for(patient, include_ended=True)
        return Response(CoverageSerializer(rows, many=True).data)

    @extend_schema(request=CoverageCreateSerializer, responses={201: CoverageSerializer})
    def create(self, request: Request) -> Response:
        serializer = CoverageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        patient = self._patient(data.pop("patient"))
        scheme = selectors.active_schemes().filter(pk=data.pop("scheme")).first()
        if scheme is None:
            raise ValidationError({"scheme": "Choose an active scheme."})
        coverage = services.add_coverage(patient=patient, scheme=scheme, actor=request.user, **data)
        return Response(CoverageSerializer(coverage).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=EndCoverageSerializer, responses=CoverageSerializer)
    @action(detail=True, methods=["post"], serializer_class=EndCoverageSerializer)
    def end(self, request: Request, pk: str | None = None) -> Response:
        serializer = EndCoverageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        coverage = services.end_coverage(
            self.get_object(), actor=request.user, reason=serializer.validated_data["reason"]
        )
        return Response(CoverageSerializer(coverage).data)
