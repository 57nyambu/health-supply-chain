"""Reception and registry API (P1-PAT-01), scoped to the request facility.

Reading a record is a chart open: ``selectors.open_record`` checks the chart access level
(care team, break-glass) and audits it with its purpose. Searching is audited with the term
stored only as an HMAC (api/CLAUDE.md).
"""

from typing import Any

from django.db.models import QuerySet
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.access import breakglass, chart
from apps.access.drf import require_facility
from apps.access.roles import ChartAccess
from apps.audit.services import record
from apps.facilities.models import Facility
from apps.patients import dsar, privacy, selectors, services
from apps.patients.models import DataSubjectRequest, Patient, PatientMerge

from .serializers import (
    BreakGlassGrantSerializer,
    BreakGlassRequestSerializer,
    ConsentInputSerializer,
    ConsentSerializer,
    ContactInputSerializer,
    ContactSerializer,
    DsarCloseSerializer,
    DsarCreateSerializer,
    DsarExportSerializer,
    DsarSerializer,
    DsarVerifySerializer,
    IdentifierInputSerializer,
    IdentifierSerializer,
    MergeRequestSerializer,
    MergeSerializer,
    NextOfKinInputSerializer,
    NextOfKinSerializer,
    PatientCreateSerializer,
    PatientSerializer,
    PatientUpdateSerializer,
    PrivacyNoticeTextSerializer,
    SearchQuerySerializer,
    SearchResultSerializer,
    UnidentifiedSerializer,
    UnmergeSerializer,
)

UPDATE = "patients.patient.update"


class PatientThrottle(ScopedRateThrottle):
    def allow_request(self, request: Request, view: Any) -> bool:
        if getattr(view, "action", None) != "search":
            return True
        return super().allow_request(request, view)


class PatientViewSet(
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet[Patient],
):
    serializer_class = PatientSerializer
    queryset = Patient.objects.none()
    throttle_classes = [PatientThrottle]
    throttle_scope = "patient_search"
    http_method_names = ["get", "post", "patch"]
    policy = {
        "search": "patients.patient.search",
        "create": "patients.patient.create",
        "retrieve": "patients.patient.read",
        "partial_update": UPDATE,
        "unidentified": "patients.patient.register_unidentified",
        "identifiers": UPDATE,
        "contacts": UPDATE,
        "next_of_kin": UPDATE,
        "merge": "patients.merge.request",
        "chart": "clinical.record.read_summary",
        "break_glass": "access.breakglass.request",
        "privacy_notice": "patients.consent.record",
        "consents": "patients.consent.record",
    }

    def get_queryset(self) -> QuerySet[Patient]:
        return Patient.objects.filter(facility_id=require_facility(self.request))

    def facility(self) -> Facility:
        return Facility.objects.get(pk=require_facility(self.request))

    def editable_object(self) -> Patient:
        """Writes need at least demographic access (already audited by the service)."""
        patient = self.get_object()
        decision = chart.decide(self.request.user, patient, purpose="registration")
        if not decision.allows(ChartAccess.DEMOGRAPHICS):
            raise selectors.ChartAccessDenied(decision, ChartAccess.DEMOGRAPHICS)
        return patient

    @action(detail=False, methods=["get"], serializer_class=SearchResultSerializer)
    def search(self, request: Request) -> Response:
        query = SearchQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        results = services.search(
            facility=require_facility(request),
            actor=request.user,
            query=query.validated_data["q"],
            date_of_birth=query.validated_data.get("date_of_birth"),
            sex=query.validated_data.get("sex"),
        )
        return Response({"results": SearchResultSerializer(results, many=True).data})

    def create(self, request: Request) -> Response:
        serializer = PatientCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = services.create_patient(
            facility=self.facility(), actor=request.user, **serializer.validated_data
        )
        return Response(PatientSerializer(patient).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Demographics (name, identifiers, contacts, next of kin) with the access banner."""
        patient = self.get_object()
        decision = selectors.open_record(
            request.user,
            patient,
            purpose=request.query_params.get("purpose", "care"),
            needed=ChartAccess.DEMOGRAPHICS,
        )
        return Response(
            {**PatientSerializer(patient).data, "access": selectors.access_payload(decision)}
        )

    @action(detail=True, methods=["get"])
    def chart(self, request: Request, pk: str | None = None) -> Response:
        """The clinical record, shaped by the chart access level (summary, full, sensitive)."""
        patient = self.get_object()
        decision = selectors.open_record(
            request.user,
            patient,
            purpose=request.query_params.get("purpose", "care"),
            needed=ChartAccess.SUMMARY,
        )
        return Response(
            {
                "access": selectors.access_payload(decision),
                "patient": PatientSerializer(patient).data,
                **selectors.chart_sections(patient, decision),
            }
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="break-glass",
        serializer_class=BreakGlassRequestSerializer,
    )
    def break_glass(self, request: Request, pk: str | None = None) -> Response:
        """Emergency full access for a limited time; reviewed afterwards (DESIGN §7.8)."""
        serializer = BreakGlassRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        grant = breakglass.request_access(
            user=request.user, patient=self.get_object(), **serializer.validated_data
        )
        return Response(BreakGlassGrantSerializer(grant).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = PatientUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        version = data.pop("version")
        patient = services.update_patient(
            self.editable_object(), actor=request.user, version=version, **data
        )
        return Response(PatientSerializer(patient).data)

    @action(
        detail=False,
        methods=["get"],
        url_path="privacy-notice",
        serializer_class=PrivacyNoticeTextSerializer,
    )
    def privacy_notice(self, request: Request) -> Response:
        """The notice reception gives at registration; its version goes with the acknowledgement."""
        return Response(privacy.notice(self.facility()))

    @action(detail=True, methods=["post"], serializer_class=ConsentInputSerializer)
    def consents(self, request: Request, pk: str | None = None) -> Response:
        """Record a privacy-notice acknowledgement or a consent decision (append-only)."""
        serializer = ConsentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = privacy.record_consent(
            self.editable_object(), actor=request.user, **serializer.validated_data
        )
        return Response(ConsentSerializer(row).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], serializer_class=UnidentifiedSerializer)
    def unidentified(self, request: Request) -> Response:
        serializer = UnidentifiedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = services.register_unidentified(
            facility=self.facility(), actor=request.user, **serializer.validated_data
        )
        return Response(PatientSerializer(patient).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], serializer_class=IdentifierInputSerializer)
    def identifiers(self, request: Request, pk: str | None = None) -> Response:
        serializer = IdentifierInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = services.add_identifier(
            self.editable_object(),
            actor=request.user,
            type_=serializer.validated_data["type"],
            value=serializer.validated_data["value"],
            issuer=serializer.validated_data["issuer"],
        )
        return Response(IdentifierSerializer(row).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], serializer_class=ContactInputSerializer)
    def contacts(self, request: Request, pk: str | None = None) -> Response:
        serializer = ContactInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = services.add_contact(
            self.editable_object(), actor=request.user, **serializer.validated_data
        )
        return Response(ContactSerializer(row).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["post"],
        url_path="next-of-kin",
        serializer_class=NextOfKinInputSerializer,
    )
    def next_of_kin(self, request: Request, pk: str | None = None) -> Response:
        serializer = NextOfKinInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = services.add_next_of_kin(
            self.editable_object(), actor=request.user, **serializer.validated_data
        )
        return Response(NextOfKinSerializer(row).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], serializer_class=MergeRequestSerializer)
    def merge(self, request: Request, pk: str | None = None) -> Response:
        """Request merging ``duplicate`` into this record (an HRIO supervisor approves)."""
        serializer = MergeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        duplicate = self.get_queryset().filter(pk=serializer.validated_data["duplicate"]).first()
        if duplicate is None:
            raise ValidationError({"duplicate": "Choose a record of this facility."})
        merge = services.request_merge(
            survivor=self.get_object(),
            duplicate=duplicate,
            actor=request.user,
            reason=serializer.validated_data["reason"],
        )
        return Response(MergeSerializer(merge).data, status=status.HTTP_201_CREATED)


class PatientMergeViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet[PatientMerge]
):
    serializer_class = MergeSerializer
    queryset = PatientMerge.objects.none()
    policy = {
        "list": "patients.merge.request",
        "retrieve": "patients.merge.request",
        "unmerge": "patients.merge.request",
    }

    def get_queryset(self) -> QuerySet[PatientMerge]:
        return PatientMerge.objects.filter(facility_id=require_facility(self.request)).order_by(
            "-created_at"
        )

    @action(detail=True, methods=["post"], serializer_class=UnmergeSerializer)
    def unmerge(self, request: Request, pk: str | None = None) -> Response:
        serializer = UnmergeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        merge = services.request_unmerge(
            self.get_object(), actor=request.user, reason=serializer.validated_data["reason"]
        )
        return Response(MergeSerializer(merge).data)


class DataSubjectRequestViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet[DataSubjectRequest]
):
    """The DSAR register (DPO, HRIO): due dates, identity checks, exports and outcomes."""

    serializer_class = DsarSerializer
    queryset = DataSubjectRequest.objects.none()
    policy = {
        "list": "patients.dsar.read",
        "retrieve": "patients.dsar.read",
        "create": "patients.dsar.process",
        "verify_identity": "patients.dsar.process",
        "export": "patients.dsar.process",
        "close": "patients.dsar.process",
        "download": "patients.dsar.read",
    }

    def get_queryset(self) -> QuerySet[DataSubjectRequest]:
        queryset = DataSubjectRequest.objects.filter(facility_id=require_facility(self.request))
        wanted = self.request.query_params.get("status")
        if wanted:
            queryset = queryset.filter(status=wanted)
        if self.request.query_params.get("overdue") == "true":
            queryset = queryset.filter(status__in=dsar.OPEN, due_at__lt=timezone.now())
        return queryset.order_by("due_at")

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        response = super().list(request, *args, **kwargs)
        record(
            "patients.dsar.register_viewed",
            request.user,
            facility=require_facility(request),
            purpose="records",
        )
        return response

    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        item = self.get_object()
        record(
            "patients.dsar.viewed", request.user, item, patient=item.patient_id, purpose="records"
        )
        return Response(DsarSerializer(item).data)

    def create(self, request: Request) -> Response:
        serializer = DsarCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        patient = Patient.objects.filter(
            pk=data.pop("patient"), facility_id=require_facility(request)
        ).first()
        if patient is None:
            raise ValidationError({"patient": "Choose a patient of this facility."})
        item = dsar.receive(actor=request.user, patient=patient, **data)
        return Response(DsarSerializer(item).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["post"],
        url_path="verify-identity",
        serializer_class=DsarVerifySerializer,
    )
    def verify_identity(self, request: Request, pk: str | None = None) -> Response:
        serializer = DsarVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = dsar.verify_identity(
            self.get_object(), actor=request.user, **serializer.validated_data
        )
        return Response(DsarSerializer(item).data)

    @action(detail=True, methods=["post"], serializer_class=DsarExportSerializer)
    def export(self, request: Request, pk: str | None = None) -> Response:
        """Produce the JSON (FHIR-shaped) and PDF copies for an access or portability request."""
        serializer = DsarExportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = dsar.export(self.get_object(), actor=request.user, **serializer.validated_data)
        return Response(DsarSerializer(item).data)

    @action(detail=True, methods=["get"], url_path=r"download/(?P<copy>[a-z0-9]+)")
    def download(
        self, request: Request, pk: str | None = None, copy: str = "pdf"
    ) -> StreamingHttpResponse:
        """Stream the JSON or PDF copy produced for this request (audited as a document view)."""
        from apps.documents.api.views import stream_response

        item = self.get_object()
        if copy not in ("json", "pdf"):
            raise NotFound("Choose the json or pdf copy.")
        document = item.export_json if copy == "json" else item.export_pdf
        if document is None:
            raise NotFound("No export has been produced for this request yet.")
        return stream_response(document, user=request.user, purpose="records")

    @action(detail=True, methods=["post"], serializer_class=DsarCloseSerializer)
    def close(self, request: Request, pk: str | None = None) -> Response:
        serializer = DsarCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = dsar.close(self.get_object(), actor=request.user, **serializer.validated_data)
        return Response(DsarSerializer(item).data)
