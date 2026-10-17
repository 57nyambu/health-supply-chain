"""Payer consent at the start of a visit (P3-SHA-02; INSURANCE.md §3.3; KE-SHA-04).

SHA: OTP (confirm which masked phone → send the code → the member reads it out → open the
payer visit) or fingerprint (authorise → the capture page in our screen → poll until
AUTHORIZED → open the payer visit). SMART: the member's code or card. The consent token the
payer returns is a secret: stored encrypted on ``PayerConsent``, never logged, never sent to
the browser; OTPs are passed straight through and never stored.

A stuck PENDING fingerprint authorisation blocks a new one at SHA, so ``start`` refuses
while one exists and ``reject_pending`` clears it. Emergencies never wait for consent
(ADR-013): nothing here gates a visit; the visit flow only reads the outcome.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.access import policies
from apps.audit.services import record
from apps.core.problems import ApiProblem
from apps.insurance.adapters import gateway_for
from apps.insurance.eligibility import PayerNotConfigured, PayerUnavailable
from apps.insurance.gateway import (
    AuthChallenge,
    AuthFailed,
    AuthMethod,
    AuthProof,
    BiometricContext,
    BusinessRuleRejected,
    ChallengeStatus,
    ConfigurationError,
    MaskedContact,
    NotFound,
    PayerGateway,
    Practitioner,
    RateLimited,
    Secret,
    SubmissionOutcomeUnknown,
    TransientError,
    Unsupported,
    ValidationRejected,
    VisitRef,
)
from apps.insurance.models import Coverage, PayerConsent
from apps.insurance.refs import coverage_ref

MAX_ATTEMPTS = 5  # wrong codes before a new one must be sent (rate limit, DESIGN §16)
OTP_LIFETIME = timedelta(minutes=10)  # local guard; SHA's own expiry is not published
SERVICE_TYPES = ("outpatient", "inpatient", "capitation", "emergency")

STATUS = {
    ChallengeStatus.OTP_SENT: PayerConsent.Status.OTP_SENT,
    ChallengeStatus.AWAITING_BIOMETRIC: PayerConsent.Status.AWAITING_BIOMETRIC,
    ChallengeStatus.AWAITING_CODE: PayerConsent.Status.AWAITING_CODE,
    ChallengeStatus.AUTHORIZED: PayerConsent.Status.AUTHORIZED,
    ChallengeStatus.AUTHORIZED_PENDING_VISIT: PayerConsent.Status.AUTHORIZED_PENDING_VISIT,
    ChallengeStatus.REJECTED: PayerConsent.Status.REJECTED,
}
BACK = {value: key for key, value in STATUS.items()}


class PendingAuthorisation(ApiProblem):
    status_code = 409
    default_detail = (
        "A fingerprint authorisation for this member is still pending with SHA. "
        "Clear it before starting a new one."
    )
    default_code = "pending_authorisation"


class OutcomeUnknown(ApiProblem):
    status_code = 502
    default_detail = (
        "The payer did not confirm the visit. Do not start again yet: check the visit "
        "with the payer first."
    )
    default_code = "payer_outcome_unknown"


@dataclass(frozen=True)
class ConsentStep:
    """What the screen needs next. ``consent`` is None while the member chooses a phone."""

    consent: PayerConsent | None
    status: str
    contacts: tuple[MaskedContact, ...] = ()
    capture_url: str = ""  # fingerprint capture page; shown once, never stored
    reason: str = ""
    otp_fallback: bool = False


def _ensure(actor: Any, facility: Any) -> None:
    if actor is not None and not policies.has_permission(
        actor, "insurance.consent.request", facility=facility
    ):
        raise PermissionDenied("You do not have permission to request payer consent here.")


def _gateway(coverage: Coverage) -> PayerGateway:
    try:
        return gateway_for(coverage.scheme.payer.gateway)
    except ConfigurationError as exc:
        raise PayerNotConfigured(str(exc)) from exc


def _translate(exc: Exception) -> Exception:
    if isinstance(exc, ValidationRejected):
        return ValidationError({"consent": exc.violations})
    if isinstance(exc, BusinessRuleRejected):
        return ValidationError({"consent": [str(exc)]})
    if isinstance(exc, Unsupported):
        return ValidationError({"method": ["This payer does not offer that kind of consent."]})
    if isinstance(exc, TransientError | RateLimited):
        return PayerUnavailable()
    if isinstance(exc, ConfigurationError):
        return PayerNotConfigured(str(exc))
    if isinstance(exc, SubmissionOutcomeUnknown):
        return OutcomeUnknown()
    if isinstance(exc, NotFound):
        return ValidationError({"consent": [str(exc)]})
    return exc


def _visit(
    consent_or_type: PayerConsent | str, practitioner: Practitioner | None = None
) -> VisitRef:
    if isinstance(consent_or_type, PayerConsent):
        return VisitRef(
            str(consent_or_type.visit_id or ""),
            consent_or_type.service_type,
            consent_or_type.created_at,
            practitioner,
        )
    return VisitRef("", consent_or_type, timezone.now(), practitioner)


def _challenge(consent: PayerConsent) -> AuthChallenge:
    token = consent.token_encrypted
    return AuthChallenge(
        AuthMethod(consent.method),
        BACK.get(PayerConsent.Status(consent.status), ChallengeStatus.REJECTED),
        reference=consent.challenge_reference,
        consent_token=Secret(token) if token else None,
        expires_at=consent.expires_at,
        reason=consent.reason,
        service_codes=tuple(consent.service_codes),
        service_type=consent.service_type,
    )


def _audit(action: str, actor: Any, consent: PayerConsent, **detail: Any) -> None:
    record(
        action,
        actor,
        consent,
        patient=consent.coverage.patient_id,
        facility=consent.facility_id,
        purpose="registration",
        detail={
            "method": consent.method,
            "status": consent.status,
            "gateway": consent.gateway,
            **detail,
        },
    )


def start(
    coverage: Coverage,
    *,
    actor: Any,
    service_type: str,
    codes: list[str],
    method: str,
    visit_id: Any = None,
    contact_id: str = "",
    biometric: BiometricContext | None = None,
) -> ConsentStep:
    _ensure(actor, coverage.facility_id)
    if service_type not in SERVICE_TYPES:
        raise ValidationError(
            {"service_type": "Choose outpatient, inpatient, capitation or emergency."}
        )
    try:
        auth_method = AuthMethod(method)
    except ValueError as exc:
        raise ValidationError({"method": "Choose OTP, fingerprint or member code."}) from exc
    if not coverage.active:
        raise ValidationError({"coverage": "This cover has ended."})
    gateway = _gateway(coverage)
    ref = coverage_ref(coverage)
    try:
        if gateway.pending_authorisations(ref):
            raise PendingAuthorisation()
        challenge = gateway.start_authorisation(
            ref,
            _visit(service_type),
            list(codes),
            auth_method,
            contact_id=contact_id,
            biometric=biometric,
        )
    except PendingAuthorisation:
        raise
    except Exception as exc:
        raise _translate(exc) from exc
    if challenge.status == ChallengeStatus.CHOOSE_CONTACT:
        return ConsentStep(None, challenge.status.value, contacts=challenge.contacts)
    expires = challenge.expires_at or (
        timezone.now() + OTP_LIFETIME if auth_method == AuthMethod.OTP else None
    )
    with transaction.atomic():
        consent = PayerConsent.objects.create(
            facility_id=coverage.facility_id,
            coverage=coverage,
            visit_id=visit_id,
            gateway=gateway.code,
            method=auth_method.value,
            status=STATUS[challenge.status],
            service_type=service_type,
            service_codes=list(challenge.service_codes or codes),
            challenge_reference=challenge.reference[:100],
            contact_id=str(contact_id)[:40],
            token_encrypted=challenge.consent_token.reveal() if challenge.consent_token else "",
            reason=challenge.reason[:100],
            expires_at=expires,
            created_by=actor,
            updated_by=actor,
        )
        _audit("insurance.consent.requested", actor, consent)
    return ConsentStep(consent, consent.status, capture_url=challenge.capture_url)


def refresh(consent: PayerConsent, *, actor: Any) -> ConsentStep:
    """Poll the payer for a fingerprint authorisation's progress."""
    _ensure(actor, consent.facility_id)
    if consent.status != PayerConsent.Status.AWAITING_BIOMETRIC:
        return ConsentStep(consent, consent.status, reason=consent.reason)
    if consent.expires_at and consent.expires_at < timezone.now():
        _set(consent, PayerConsent.Status.EXPIRED, actor, reason="capture_expired")
        return ConsentStep(consent, consent.status, reason=consent.reason)
    try:
        updated = _gateway(consent.coverage).authorisation_status(_challenge(consent))
    except Exception as exc:
        raise _translate(exc) from exc
    new = STATUS.get(updated.status, PayerConsent.Status.AWAITING_BIOMETRIC)
    if new != consent.status or updated.reason != consent.reason:
        _set(consent, new, actor, reason=updated.reason)
    return ConsentStep(
        consent,
        consent.status,
        reason=consent.reason,
        otp_fallback=consent.reason == "BIOMETRICS_NOT_FOUND_OTP_ALLOWED",
    )


def _set(
    consent: PayerConsent, status: str, actor: Any, *, reason: str = "", **fields: Any
) -> None:
    with transaction.atomic():
        current = PayerConsent.objects.select_for_update().get(pk=consent.pk)
        current.status = status
        current.reason = reason[:100]
        for name, value in fields.items():
            setattr(current, name, value)
        current.version += 1
        current.updated_by = actor
        current.save()
        _audit("insurance.consent.updated", actor, current)
    consent.refresh_from_db()


def complete(
    consent: PayerConsent,
    *,
    actor: Any,
    otp: str = "",
    member_code: str = "",
    practitioner: Practitioner | None = None,
) -> PayerConsent:
    """Open the payer visit with the member's proof. The OTP is never stored."""
    _ensure(actor, consent.facility_id)
    ready = {
        PayerConsent.Status.OTP_SENT,
        PayerConsent.Status.AWAITING_CODE,
        PayerConsent.Status.AUTHORIZED,
    }
    if consent.status not in ready:
        raise ValidationError({"consent": "This consent is not waiting for the member's proof."})
    if consent.expires_at and consent.expires_at < timezone.now() and consent.method == "otp":
        _set(consent, PayerConsent.Status.EXPIRED, actor, reason="otp_expired")
        raise ValidationError({"otp": "The code has expired. Send a new one."})
    proof = AuthProof(
        otp=Secret(otp) if otp else None, member_code=Secret(member_code) if member_code else None
    )
    coverage = consent.coverage
    try:
        handle = _gateway(coverage).complete_authorisation(
            _challenge(consent), proof, coverage_ref(coverage), _visit(consent, practitioner)
        )
    except AuthFailed as exc:
        attempts = consent.attempts + 1
        expired = "expired" in str(exc).lower()
        status = (
            PayerConsent.Status.EXPIRED
            if expired
            else PayerConsent.Status.REJECTED
            if attempts >= MAX_ATTEMPTS
            else consent.status
        )
        _set(
            consent,
            status,
            actor,
            reason="expired" if expired else "wrong_proof",
            attempts=attempts,
        )
        field = "otp" if consent.method == "otp" else "member_code"
        message = str(exc)
        if status == PayerConsent.Status.REJECTED:
            message = "Too many wrong codes. Start again to send a new one."
        raise ValidationError({field: message}) from exc
    except Exception as exc:
        raise _translate(exc) from exc
    _set(
        consent,
        PayerConsent.Status.VISIT_OPEN,
        actor,
        token_encrypted=handle.consent_token.reveal(),
        payer_visit_reference=handle.visit_reference[:100],
        authorized_at=timezone.now(),
    )
    return consent


def pending(coverage: Coverage, *, actor: Any) -> int:
    _ensure(actor, coverage.facility_id)
    try:
        return len(_gateway(coverage).pending_authorisations(coverage_ref(coverage)))
    except Exception as exc:
        raise _translate(exc) from exc


def reject_pending(coverage: Coverage, *, actor: Any) -> int:
    """Reject the member's stuck PENDING authorisations at the payer (SHA)."""
    _ensure(actor, coverage.facility_id)
    gateway = _gateway(coverage)
    try:
        stuck = gateway.pending_authorisations(coverage_ref(coverage))
        for challenge in stuck:
            gateway.reject_authorisation(challenge)
    except Exception as exc:
        raise _translate(exc) from exc
    record(
        "insurance.consent.pending_rejected",
        actor,
        coverage,
        patient=coverage.patient_id,
        facility=coverage.facility_id,
        purpose="registration",
        detail={"count": len(stuck), "gateway": gateway.code},
    )
    return len(stuck)


def cancel(consent: PayerConsent, *, actor: Any) -> PayerConsent:
    """Abandon a consent that is not yet used (wrong member, member left)."""
    _ensure(actor, consent.facility_id)
    if consent.status not in PayerConsent.OPEN_STATUSES:
        raise ValidationError({"consent": "Only consents still in progress can be cancelled."})
    if consent.method == "biometric" and consent.token_encrypted:
        try:
            _gateway(consent.coverage).reject_authorisation(_challenge(consent))
        except Exception as exc:
            raise _translate(exc) from exc
    _set(consent, PayerConsent.Status.CANCELLED, actor, reason="cancelled")
    return consent
