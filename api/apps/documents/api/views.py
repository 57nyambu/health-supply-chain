"""Documents API: upload, list per patient, metadata and the audited content stream.

Content is served only by ``GET /api/v1/documents/{id}/content/`` — never by public or
presigned URLs (docs/integrations/STORAGE.md §5).
"""

import logging
from typing import Any

from django.db.models import QuerySet
from django.http import StreamingHttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from apps.access import chart
from apps.access.drf import require_facility
from apps.access.roles import ChartAccess
from apps.audit.services import record
from apps.core.problems import ApiProblem
from apps.documents import selectors, services
from apps.documents.envelope import EnvelopeError
from apps.documents.models import Document
from apps.patients import selectors as patient_selectors
from apps.patients.models import Patient

from .serializers import DocumentSerializer, PatientDocumentsQuerySerializer, UploadSerializer

logger = logging.getLogger(__name__)
EXTENSIONS = {
    "application/pdf": "pdf",
    "application/json": "json",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class DocumentUnreadable(ApiProblem):
    status_code = 500
    default_detail = "The document could not be read. The administrators have been alerted."
    default_code = "document_unreadable"


class DocumentViewSet(viewsets.GenericViewSet[Document]):
    serializer_class = DocumentSerializer
    queryset = Document.objects.none()
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    policy = {
        "list": "documents.document.read",
        "retrieve": "documents.document.read",
        "content": "documents.document.read",
        "create": "documents.document.upload",
    }

    def get_queryset(self) -> QuerySet[Document]:
        return Document.objects.filter(facility_id=require_facility(self.request)).select_related(
            "patient"
        )

    def _patient(self, patient_id: Any) -> Patient | None:
        if patient_id is None:
            return None
        patient = Patient.objects.filter(
            pk=patient_id, facility_id=require_facility(self.request)
        ).first()
        if patient is None:
            raise ValidationError({"patient": "Choose a patient of this facility."})
        return patient

    def create(self, request: Request) -> Response:
        serializer = UploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        supersedes = None
        if data["supersedes"] is not None:
            supersedes = self.get_queryset().filter(pk=data["supersedes"]).first()
            if supersedes is None:
                raise ValidationError({"supersedes": "Choose a document of this facility."})
        document = services.upload(
            actor=request.user,
            facility_id=require_facility(request),
            content=data["file"],
            filename=data["file"].name or "",
            category=data["category"],
            patient=self._patient(data["patient"]),
            sensitivity=data["sensitivity"],
            supersedes=supersedes,
        )
        return Response(DocumentSerializer(document).data, status=status.HTTP_201_CREATED)

    def list(self, request: Request) -> Response:
        """A patient's current documents, shaped by chart access (sensitive ones as placeholders)."""
        query = PatientDocumentsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        patient = self._patient(query.validated_data["patient"])
        if patient is None:
            raise ValidationError({"patient": "Choose a patient."})
        decision = patient_selectors.open_record(
            request.user,
            patient,
            purpose=query.validated_data["purpose"],
            needed=ChartAccess.DEMOGRAPHICS,
            action="documents.document.listed",
        )
        return Response({"results": selectors.for_patient(patient, decision)})

    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        document = self.get_object()
        purpose = request.query_params.get("purpose", "care")
        services.authorise_read(document, user=request.user, purpose=purpose)
        record(
            "documents.document.metadata_viewed",
            request.user,
            document,
            patient=document.patient_id,
            purpose=purpose if purpose in chart.PURPOSES else "care",
        )
        return Response(DocumentSerializer(document).data)

    @action(detail=True, methods=["get"])
    def content(self, request: Request, pk: str | None = None) -> StreamingHttpResponse:
        return stream_response(
            self.get_object(),
            user=request.user,
            purpose=request.query_params.get("purpose", "care"),
        )


def stream_response(document: Document, *, user: Any, purpose: str) -> StreamingHttpResponse:
    """Authorise, audit and stream one document (also used by the DSAR register)."""
    try:
        stream = services.open_content(document, user=user, purpose=purpose)
    except EnvelopeError as exc:
        logger.error(
            "Document failed decryption or integrity check",
            extra={"document_id": str(document.pk)},
        )
        raise DocumentUnreadable() from exc
    response = StreamingHttpResponse(stream, content_type=document.content_type)
    extension = EXTENSIONS.get(document.content_type, "bin")
    response["Content-Disposition"] = f'inline; filename="document-{document.pk}.{extension}"'
    response["Content-Length"] = str(document.size)
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
