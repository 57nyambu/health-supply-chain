"""Payers, schemes and coverage API (seam between the parallel lanes, ADR-024)."""

from typing import Any

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from apps.access.drf import require_facility
from apps.access.roles import ChartAccess
from apps.core.problems import PreconditionRequired
from apps.insurance import consent, eligibility, selectors, services
from apps.insurance.gateway import BiometricContext, Secret
from apps.insurance.models import Coverage, PayerConsent, Scheme
from apps.patients import selectors as patient_selectors
from apps.patients.models import Patient

from .serializers import (
    ConsentCompleteSerializer,
    ConsentStartSerializer,
    ConsentStepSerializer,
    CoverageCreateSerializer,
    CoverageQuerySerializer,
    CoverageSerializer,
    EligibilityCheckSerializer,
    EndCoverageSerializer,
    PayerConsentSerializer,
    PayerServiceCodeSerializer,
    PendingAuthorisationsSerializer,
    SchemeSerializer,
)


class KeyedActions:
    """Actions that reach a payer need an ``Idempotency-Key`` (DESIGN §17). Checked after
    authentication and the policy, so anonymous callers still get 401/403; the core
    middleware stores and replays the response whenever the key is sent."""

    keyed_actions: frozenset[str] = frozenset()

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)  # type: ignore[misc]
        action_name = getattr(self, "action", None)
        if (
            request.method in ("POST", "PUT", "PATCH", "DELETE")
            and action_name in self.keyed_actions
            and not request.headers.get("Idempotency-Key")
        ):
            raise PreconditionRequired("This request needs an Idempotency-Key header.")


class SchemeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet[Scheme]):
    """Active schemes a visit can be billed to; no scheme means cash / self-pay."""

    serializer_class = SchemeSerializer
    queryset = Scheme.objects.none()
    pagination_class = None
    policy = "insurance.payer.read"

    def get_queryset(self) -> QuerySet[Scheme]:
        return selectors.active_schemes()


class CoverageViewSet(KeyedActions, viewsets.GenericViewSet[Coverage]):
    serializer_class = CoverageSerializer
    queryset = Coverage.objects.none()
    policy = {
        "list": "insurance.coverage.read",
        "create": "insurance.coverage.manage",
        "end": "insurance.coverage.manage",
        "eligibility": "insurance.eligibility.check",
        "benefits": "insurance.eligibility.check",
        "pending_authorisations": "insurance.consent.request",
        "reject_pending": "insurance.consent.request",
    }
    # These call the payer: one execution per Idempotency-Key (DESIGN §17).
    keyed_actions = frozenset({"eligibility", "reject_pending"})

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

    # --- Phase 3: eligibility, benefits and pending authorisations ---

    def _opened(self, coverage: Coverage, action: str) -> None:
        patient_selectors.open_record(
            self.request.user,
            coverage.patient,
            purpose="registration",
            needed=ChartAccess.DEMOGRAPHICS,
            action=action,
        )

    @extend_schema(
        request=None,
        responses={200: EligibilityCheckSerializer, 201: EligibilityCheckSerializer},
    )
    @action(detail=True, methods=["get", "post"])
    def eligibility(self, request: Request, pk: str | None = None) -> Response:
        """GET: the latest eligibility snapshot (404 if never checked). POST: ask the payer
        now (Idempotency-Key required). A payer outage gives ``pending_verification``."""
        coverage = self.get_object()
        if request.method == "GET":
            self._opened(coverage, "insurance.eligibility.viewed")
            latest = eligibility.latest(coverage)
            if latest is None:
                raise NotFound("This cover has not been checked yet.")
            return Response(EligibilityCheckSerializer(latest).data)
        check = eligibility.check(coverage, actor=request.user)
        return Response(EligibilityCheckSerializer(check).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses=PayerServiceCodeSerializer(many=True))
    @action(detail=True, methods=["get"])
    def benefits(self, request: Request, pk: str | None = None) -> Response:
        """The services the payer lists for this member, with pre-authorisation flags."""
        codes = eligibility.billable(self.get_object(), actor=request.user)
        return Response(PayerServiceCodeSerializer([c.__dict__ for c in codes], many=True).data)

    @extend_schema(responses=PendingAuthorisationsSerializer)
    @action(detail=True, methods=["get"], url_path="pending-authorisations")
    def pending_authorisations(self, request: Request, pk: str | None = None) -> Response:
        return Response({"pending": consent.pending(self.get_object(), actor=request.user)})

    @extend_schema(request=None, responses=PendingAuthorisationsSerializer)
    @action(detail=True, methods=["post"], url_path="pending-authorisations/reject")
    def reject_pending(self, request: Request, pk: str | None = None) -> Response:
        """Clear the member's stuck fingerprint authorisations at SHA (Idempotency-Key)."""
        consent.reject_pending(self.get_object(), actor=request.user)
        return Response({"pending": 0})


def _step(step: consent.ConsentStep) -> dict[str, Any]:
    return {
        "status": step.status,
        "consent": PayerConsentSerializer(step.consent).data if step.consent else None,
        "contacts": [c.__dict__ for c in step.contacts],
        "capture_url": step.capture_url,
        "reason": step.reason,
        "otp_fallback": step.otp_fallback,
    }


class PayerConsentViewSet(KeyedActions, viewsets.GenericViewSet[PayerConsent]):
    """Payer consent for a visit: OTP, fingerprint or member code (P3-SHA-02). The consent
    token is held server-side only; responses say whether one is held."""

    serializer_class = PayerConsentSerializer
    queryset = PayerConsent.objects.none()
    policy = {
        "create": "insurance.consent.request",
        "retrieve": "insurance.consent.request",
        "complete": "insurance.consent.request",
        "cancel": "insurance.consent.request",
    }
    keyed_actions = frozenset({"create", "complete", "cancel"})

    def get_queryset(self) -> QuerySet[PayerConsent]:
        return PayerConsent.objects.filter(
            facility_id=require_facility(self.request)
        ).select_related("coverage__scheme__payer", "coverage__patient")

    @extend_schema(
        request=ConsentStartSerializer,
        responses={200: ConsentStepSerializer, 201: ConsentStepSerializer},
    )
    def create(self, request: Request) -> Response:
        """Start consent. OTP without ``contact_id`` returns the member's masked phones to
        choose from (no consent yet); with it, sends the code. Fingerprint returns the
        capture page to show. Member code (SMART) waits for the code."""
        data = ConsentStartSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        coverage = (
            Coverage.objects.filter(pk=values["coverage"], facility_id=require_facility(request))
            .select_related("scheme__payer", "patient")
            .first()
        )
        if coverage is None:
            raise ValidationError({"coverage": "Choose a cover of this facility."})
        bio = values.get("biometric")
        step = consent.start(
            coverage,
            actor=request.user,
            service_type=values["service_type"],
            codes=values["codes"],
            method=values["method"],
            visit_id=values.get("visit"),
            contact_id=values.get("contact_id", ""),
            biometric=BiometricContext(
                Secret(bio["agent_id"]),
                bio["device_os"],
                bio["ekyc_provider_id"],
                bio["work_station_id"],
            )
            if bio
            else None,
        )
        code = status.HTTP_201_CREATED if step.consent is not None else status.HTTP_200_OK
        return Response(_step(step), status=code)

    @extend_schema(responses=ConsentStepSerializer)
    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        """The consent's state; for a fingerprint in progress this asks the payer (poll)."""
        return Response(_step(consent.refresh(self.get_object(), actor=request.user)))

    @extend_schema(request=ConsentCompleteSerializer, responses=PayerConsentSerializer)
    @action(detail=True, methods=["post"], serializer_class=ConsentCompleteSerializer)
    def complete(self, request: Request, pk: str | None = None) -> Response:
        """Open the payer visit with the member's OTP or code (never stored)."""
        data = ConsentCompleteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        done = consent.complete(
            self.get_object(),
            actor=request.user,
            otp=data.validated_data["otp"],
            member_code=data.validated_data["member_code"],
        )
        return Response(PayerConsentSerializer(done).data)

    @extend_schema(request=None, responses=PayerConsentSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        cancelled = consent.cancel(self.get_object(), actor=request.user)
        return Response(PayerConsentSerializer(cancelled).data)
