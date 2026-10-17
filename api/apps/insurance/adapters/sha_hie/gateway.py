"""The SHA payer gateway over the HIE (field names: DECISIONS.md, Phase 3 findings).

Consent tokens and OTPs pass through as ``Secret``; the HIE client keeps them out of logs.
Error strings and status words the specs leave open are spec gaps (GAP-HIE-006, -008):
the mapping below is deliberately conservative — anything unrecognised is "not verified",
never "eligible".
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.utils import timezone

from apps.insurance.adapters.base import BaseGateway
from apps.insurance.gateway import (
    AuthChallenge,
    AuthFailed,
    AuthMethod,
    AuthProof,
    BiometricContext,
    BusinessRuleRejected,
    ChallengeStatus,
    ConfigurationError,
    CoverageRef,
    DiagnosisSystem,
    EligibilityResult,
    EligibilityStatus,
    Forbidden,
    GatewayError,
    MaskedContact,
    MemberMatch,
    MemberQuery,
    NotFound,
    PayerCapabilities,
    PayerServiceCode,
    PayerVisitHandle,
    RateLimited,
    SchemeStatus,
    Secret,
    SubmissionOutcomeUnknown,
    TransientError,
    ValidationRejected,
    VisitRef,
)
from apps.interop.hie import mapping
from apps.interop.hie.client import HieClient
from apps.interop.hie.errors import (
    HieAuthError,
    HieConfigurationError,
    HieError,
    HieForbidden,
    HieNotFound,
    HieOutcomeUnknown,
    HieRateLimited,
    HieRejected,
    HieUnavailable,
)

INTEGRATION = "hie.sha"
MAX_PAGES = 20
BIOMETRIC_WINDOW = timedelta(minutes=10)  # the capture iframe's documented lifetime
OTP_FALLBACK_REASON = "BIOMETRICS_NOT_FOUND_OTP_ALLOWED"

# Our scheme kinds → the HIE's ``schemeName`` (prefix match; POMSF has variants such as
# ``POMSF-047``). PHC is reported as UHC by the HIE.
SCHEME_NAMES: dict[str, tuple[str, ...]] = {
    "shif": ("SHIF",),
    "phc": ("UHC", "PHC"),
    "eccif": ("ECCIF",),
    "pomsf": ("POMSF",),
}

AUTH_STATES = {
    "PENDING": ChallengeStatus.AWAITING_BIOMETRIC,
    "AUTHORIZED": ChallengeStatus.AUTHORIZED,
    "AUTHORIZED_PENDING_VISIT": ChallengeStatus.AUTHORIZED_PENDING_VISIT,
    "REJECTED": ChallengeStatus.REJECTED,
}


def translate(exc: HieError, *, write: bool = False) -> GatewayError:
    """HIE transport errors → the payer taxonomy (messages stay free of PHI)."""
    message = exc.payer_message
    if isinstance(exc, HieConfigurationError):
        return ConfigurationError(str(exc))
    if isinstance(exc, HieOutcomeUnknown):
        return SubmissionOutcomeUnknown(str(exc))
    if isinstance(exc, HieUnavailable):
        return TransientError("SHA (through the HIE) is not answering. Try again shortly.")
    if isinstance(exc, HieRateLimited):
        return RateLimited(exc.retry_after)
    if isinstance(exc, HieAuthError):
        return ConfigurationError(
            "The HIE refused the facility's credentials (check SHA_CLIENT_ID)."
        )
    if isinstance(exc, HieForbidden):
        return Forbidden(message or "The HIE does not allow this for the facility.")
    if isinstance(exc, HieNotFound):
        return NotFound(message or "SHA has no such record.")
    if isinstance(exc, HieRejected):
        return ValidationRejected([message or exc.error or "The request was refused."])
    return TransientError(str(exc))


def _scheme_matches(kind: str, name: str) -> bool:
    return any(name.upper().startswith(prefix) for prefix in SCHEME_NAMES.get(kind, ()))


def _scheme_status(row: dict[str, Any], on: date) -> SchemeStatus:
    coverage = row.get("coverage") or {}
    raw = mapping.text(coverage.get("status"))
    start = mapping.parse_date(coverage.get("startDate"))
    end = mapping.parse_date(coverage.get("endDate"))
    within = (start is None or start <= on) and (end is None or on <= end)
    return SchemeStatus(
        scheme_name=mapping.text(row.get("schemeName")),
        status=raw,
        active=raw.upper() == "ACTIVE" and within,  # GAP-HIE-006: only "ACTIVE" is trusted
        valid_from=start,
        valid_to=end,
        reason=mapping.text(coverage.get("reason"))[:200],
        possible_solution=mapping.text(coverage.get("possibleSolution"))[:200],
    )


def _service_code(row: dict[str, Any]) -> PayerServiceCode:
    tariff = mapping.parse_money(row.get("kephLevelTarriff"))
    if tariff is None:
        tariff = mapping.parse_money(row.get("overallTariff"))
    return PayerServiceCode(
        code=mapping.text(row.get("code")),
        name=mapping.text(row.get("name")),
        fund=mapping.text(row.get("fund")),
        sub_benefit_code=mapping.text(row.get("benefitCode")),
        access_point=mapping.text(row.get("accessPoint")),
        payment_mechanism=mapping.text(row.get("paymentMechanism")),
        needs_preauth=mapping.truthy(row.get("needsPreauth")),
        needs_manual_preauth_approval=mapping.truthy(row.get("needsManualPreauthApproval")),
        needs_doctor_authorization=mapping.truthy(row.get("needsDoctorAuthorization")),
        tariff=tariff,
        required_documents=tuple(mapping.text(d) for d in row.get("applicableDocumentTypes") or []),
    )


class ShaHieGateway(BaseGateway):
    code = "sha_hie"

    def __init__(self, client: HieClient) -> None:
        self.client = client
        self.mode = client.mode

    def capabilities(self) -> PayerCapabilities:
        return PayerCapabilities(
            incremental_claim_session=True,
            consent_otp=True,
            consent_biometric=True,
            preauth=True,
            callbacks=True,
            member_search=True,
            diagnosis_system=DiagnosisSystem.ICD11,
        )

    # --- helpers ---

    def _get(self, path: str, params: dict[str, Any], operation: str) -> Any:
        try:
            return self.client.get(
                path, params=params, operation=operation, integration=INTEGRATION
            )
        except HieError as exc:
            raise translate(exc) from exc

    def _post(
        self, path: str, body: dict[str, Any], operation: str, *, log_path: str | None = None
    ) -> Any:
        try:
            return self.client.post(
                path, json=body, operation=operation, integration=INTEGRATION, log_path=log_path
            )
        except HieError as exc:
            raise translate(exc, write=True) from exc

    @staticmethod
    def _identification(coverage: CoverageRef) -> tuple[str, str]:
        if coverage.cr_id:
            return "ClientRegistry ID", coverage.cr_id
        if coverage.identification is not None:
            hie_type = mapping.hie_id_type(coverage.identification[0])
            if hie_type:
                return hie_type, coverage.identification[1].reveal()
        raise ValidationRejected(
            ["Add the patient's national ID (or Client Registry ID) to check SHA cover."]
        )

    @staticmethod
    def _patient_id(coverage: CoverageRef) -> str:
        if not coverage.cr_id:
            raise ValidationRejected(
                ["Check SHA eligibility first: SHA consent needs the patient's Client Registry ID."]
            )
        return coverage.cr_id

    # --- members and eligibility ---

    def find_member(self, query: MemberQuery) -> list[MemberMatch]:
        hie_type = mapping.hie_id_type(query.identifier_type)
        if hie_type is None:
            raise ValidationRejected(
                ["SHA members are found by national, alien, refugee or CR ID."]
            )
        try:
            member = self._get(
                "/patients",
                {"identification_number": query.number.reveal(), "identification_type": hie_type},
                "find_member",
            )
        except NotFound:
            return []
        cr_id = mapping.text(member.get("id")) if isinstance(member, dict) else ""
        return [MemberMatch(member_ref=cr_id)] if cr_id else []

    def check_eligibility(self, coverage: CoverageRef, on: date) -> EligibilityResult:
        id_type, number = self._identification(coverage)
        try:
            body = self._get(
                "/patients/eligibility",
                {"identification_number": number, "identification_type": id_type},
                "eligibility",
            )
        except NotFound:
            return EligibilityResult(
                EligibilityStatus.NOT_FOUND, message="SHA has no member with this identifier."
            )
        schemes = tuple(_scheme_status(row, on) for row in body.get("schemes") or [])
        enforced = mapping.truthy(body.get("facilityBiometricsEnforced"))
        summary = {
            "status_code": mapping.text(body.get("statusCode"))[:20],
            "schemes": [
                {
                    "name": s.scheme_name,
                    "status": s.status,
                    "active": s.active,
                    "from": s.valid_from.isoformat() if s.valid_from else None,
                    "to": s.valid_to.isoformat() if s.valid_to else None,
                }
                for s in schemes
            ],
            "biometrics_enforced": enforced,
            "alive": mapping.truthy(body.get("isAlive", True)),
        }

        def result(status: EligibilityStatus, message: str) -> EligibilityResult:
            return EligibilityResult(
                status,
                member_ref=mapping.text(body.get("memberCrNumber")),
                schemes=schemes,
                message=message[:255],
                biometrics_enforced=enforced,
                otp_allowed=(not enforced) or mapping.truthy(body.get("whitelistedForOTP")),
                summary=summary,
            )

        ours = [s for s in schemes if _scheme_matches(coverage.scheme_kind, s.scheme_name)]
        if not schemes:
            reason = mapping.text(body.get("statusDesc"))[:200] or "No active SHA scheme."
            return result(EligibilityStatus.NOT_ELIGIBLE, reason)
        if any(s.active for s in ours):
            return result(EligibilityStatus.ELIGIBLE, "Eligible.")
        if ours:
            first = ours[0]
            reason = (
                first.reason
                or f"{first.scheme_name} cover is {first.status.lower() or 'not active'}."
            )
            if first.possible_solution:
                reason = f"{reason} {first.possible_solution}"
            return result(EligibilityStatus.INACTIVE, reason)
        return result(
            EligibilityStatus.NOT_ELIGIBLE, "The member has SHA cover, but not under this scheme."
        )

    def list_billable(self, coverage: CoverageRef) -> list[PayerServiceCode]:
        patient_id = self._patient_id(coverage)
        codes: list[PayerServiceCode] = []
        page = 1
        while page <= MAX_PAGES:
            body = self._get(
                "/patients/benefits/interventions",
                {"patient_id": patient_id, "page": str(page)},
                "interventions",
            )
            codes += [_service_code(row) for row in body.get("results") or [] if row.get("code")]
            total_pages = int(body.get("totalPages") or 1)
            if page >= total_pages:
                break
            page += 1
        return codes

    # --- consent ---

    def _contacts(self, patient_id: str) -> tuple[MaskedContact, ...]:
        body = self._get("/patients/contacts", {"patient_id": patient_id}, "contacts")
        return tuple(
            MaskedContact(
                contact_id=str(row.get("id")),
                masked=mapping.text(row.get("contactValue")),
                confirmed=mapping.truthy(row.get("isConfirmed")),
            )
            for row in body.get("results") or []
            if row.get("id") is not None and mapping.truthy(row.get("active", True))
        )

    def start_authorisation(
        self,
        coverage: CoverageRef,
        visit: VisitRef,
        codes: list[str],
        method: AuthMethod,
        *,
        contact_id: str = "",
        biometric: BiometricContext | None = None,
    ) -> AuthChallenge:
        patient_id = self._patient_id(coverage)
        if not codes:
            raise ValidationRejected(["Choose at least one SHA intervention for the visit."])
        if method == AuthMethod.OTP:
            if not contact_id:
                contacts = self._contacts(patient_id)
                if not contacts:
                    raise BusinessRuleRejected(
                        "no_contact",
                        "SHA has no confirmed phone for this member. Use fingerprints instead.",
                    )
                return AuthChallenge(
                    AuthMethod.OTP,
                    ChallengeStatus.CHOOSE_CONTACT,
                    contacts=contacts,
                    service_codes=tuple(codes),
                    service_type=visit.service_type,
                )
            try:
                contact_number = int(contact_id)
            except ValueError as exc:
                raise ValidationRejected(["Choose one of the member's phones."]) from exc
            body = self._post(
                "/claims/otp",
                {
                    "patient_id": patient_id,
                    "intervention_codes": list(codes),
                    "contact_id": contact_number,
                },
                "send_otp",  # never retried: a retry would text the member twice
            )
            data = body.get("data") if isinstance(body, dict) else None
            reference = mapping.text((data or {}).get("consent_request_id"))
            return AuthChallenge(
                AuthMethod.OTP,
                ChallengeStatus.OTP_SENT,
                reference=reference,
                contacts=(),
                service_codes=tuple(codes),
                service_type=visit.service_type,
            )
        if method == AuthMethod.BIOMETRIC:
            if biometric is None:
                raise ValidationRejected(["Connect the fingerprint workstation first."])
            service_type = mapping.AUTHORIZE_SERVICE_TYPES.get(visit.service_type)
            if service_type is None:
                raise ValidationRejected(
                    ["Fingerprint consent is for outpatient or inpatient visits."]
                )
            body = self._post(
                "/claims/authorize",
                {
                    "agent_id": biometric.agent_id.reveal(),
                    "authorizing_device_os": biometric.device_os,
                    "ekyc_provider_id": biometric.ekyc_provider_id,
                    "factors": ["fingerprint"],
                    "interventions": list(codes),
                    "is_biometrics_discharge_authorization": False,
                    "is_emergency": visit.service_type == "emergency",
                    "is_integration": True,
                    "patient_id": patient_id,
                    "provider": coverage.facility_code or self.client.config.facility_code,
                    "service_type": service_type,
                    "work_station_id": biometric.work_station_id,
                },
                "authorize_biometric",
            )
            return self._challenge_from(body, codes, visit.service_type)
        raise self._unsupported(f"{method} authorisation")

    def _challenge_from(
        self, row: dict[str, Any], codes: list[str] | tuple[str, ...], service_type: str
    ) -> AuthChallenge:
        verification = row.get("shaVerificationRequest") or {}
        token = mapping.text(row.get("token"))
        return AuthChallenge(
            AuthMethod.BIOMETRIC,
            AUTH_STATES.get(
                mapping.text(row.get("status")).upper(), ChallengeStatus.AWAITING_BIOMETRIC
            ),
            reference=mapping.text(row.get("guid")),
            consent_token=Secret(token) if token else None,
            capture_url=mapping.text(verification.get("requestUrl")),
            expires_at=timezone.now() + BIOMETRIC_WINDOW,
            reason=mapping.text(row.get("authorizationReason")),
            service_codes=tuple(codes),
            service_type=service_type,
        )

    def pending_authorisations(self, coverage: CoverageRef) -> list[AuthChallenge]:
        body = self._get(
            "/claims/authorizations", {"patient_id": self._patient_id(coverage)}, "authorizations"
        )
        rows = body if isinstance(body, list) else []
        return [
            self._challenge_from(row, (), "")
            for row in rows
            if mapping.text(row.get("status")).upper() == "PENDING"
        ]

    def authorisation_status(self, challenge: AuthChallenge) -> AuthChallenge:
        if challenge.method != AuthMethod.BIOMETRIC or not challenge.reference:
            return challenge
        body = self._get(
            "/claims/authorizations", {"guid": challenge.reference}, "authorization_status"
        )
        rows = body if isinstance(body, list) else []
        if not rows:
            raise NotFound("SHA has no such authorisation.")
        row = rows[0]
        status = AUTH_STATES.get(mapping.text(row.get("status")).upper(), challenge.status)
        return AuthChallenge(
            challenge.method,
            status,
            reference=challenge.reference,
            consent_token=challenge.consent_token,
            capture_url=challenge.capture_url
            if status == ChallengeStatus.AWAITING_BIOMETRIC
            else "",
            expires_at=challenge.expires_at,
            reason=mapping.text(row.get("authorizationReason")),
            service_codes=challenge.service_codes,
            service_type=challenge.service_type,
        )

    def reject_authorisation(self, challenge: AuthChallenge) -> None:
        if challenge.consent_token is None:
            raise ValidationRejected(["This authorisation has no consent token to reject."])
        self._post(
            f"/claims/authorizations/{challenge.consent_token.reveal()}/reject",
            {},
            "reject_authorization",
            log_path="/claims/authorizations/[redacted]/reject",
        )

    def complete_authorisation(
        self, challenge: AuthChallenge, proof: AuthProof, coverage: CoverageRef, visit: VisitRef
    ) -> PayerVisitHandle:
        service_type = mapping.SERVICE_TYPES.get(visit.service_type)
        if service_type is None:
            raise ValidationRejected(["Unknown visit type for SHA."])
        body: dict[str, Any] = {
            "intervention_codes": list(challenge.service_codes),
            "patient_id": self._patient_id(coverage),
            "service_type": service_type,
        }
        if challenge.method == AuthMethod.OTP:
            if proof.otp is None or not proof.otp.reveal().strip():
                raise ValidationRejected(["Enter the code the member received."])
            body["otp"] = proof.otp.reveal().strip()
        elif challenge.method == AuthMethod.BIOMETRIC:
            if challenge.status != ChallengeStatus.AUTHORIZED:
                raise AuthFailed("The fingerprint has not been matched yet.")
            body["auth_guid"] = challenge.reference
        else:
            raise self._unsupported(f"{challenge.method} authorisation")
        if visit.practitioner is not None and visit.practitioner.regulator in mapping.REGULATORS:
            body.update(
                practitioner_identification_type="registration_number",
                practitioner_identification_number=visit.practitioner.registration_number,
                practitioner_regulation_body=visit.practitioner.regulator,
            )
        try:
            result = self.client.post(
                "/claims/visit", json=body, operation="start_visit", integration=INTEGRATION
            )
        except HieRejected as exc:
            text = (exc.payer_message or exc.error).lower()
            if challenge.method == AuthMethod.OTP and "otp" in text:
                if "expire" in text:  # GAP-HIE-008: error words are not enumerated
                    raise AuthFailed("The code has expired. Send a new one.") from exc
                raise AuthFailed("The code is not correct. Check it with the member.") from exc
            raise translate(exc) from exc
        except HieError as exc:
            raise translate(exc, write=True) from exc
        token = mapping.text(result.get("authorization_code")) if isinstance(result, dict) else ""
        if not token:
            raise SubmissionOutcomeUnknown(
                "SHA started the visit without a consent token; check the visit with SHA."
            )
        return PayerVisitHandle(
            consent_token=Secret(token),
            visit_reference=mapping.text(result.get("visit_number")),
            payer_claim_ref=mapping.text(result.get("claim_id")),
            workflow_state=mapping.text(result.get("workflow_state")),
        )
