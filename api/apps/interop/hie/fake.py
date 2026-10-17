"""An in-process fake of the national HIE for dev, CI and demos (synthetic data only).

``FakeHie().transport()`` is an ``httpx.MockTransport``: the real ``HieClient`` and the real
adapters run against it unchanged, so fake mode exercises authentication, facility headers,
mapping and error handling exactly as UAT will. It answers only the operations and fields of
the HIE's published specs (DECISIONS.md, Phase 3 findings). Values the specs leave open —
error strings, status words, payment-mechanism names — are the fake's own and listed as
spec gaps; adapters must not rely on them beyond what the gaps say.

Scripted outcomes (``SCRIPT``), keyed on the last two digits of the identification number
(national ID, or the national ID inside a synthetic CR ID ``CR-SYN-N<id>``):

    99999999   registry/eligibility outage (503)        95  read timeout
    97  not found (404)                                  96  known, no active scheme (not eligible)
    98  scheme suspended (inactive, with reason)          94  eligible, no confirmed phone (no OTP)
    93  fingerprint never matches (REJECTED)            92  no usable fingerprints → OTP allowed
    91  a stuck PENDING biometric authorisation exists   90  facility enforces biometrics (no OTP)
    anything else: eligible for SHIF and PHC/UHC this calendar year

OTPs: ``123456`` accepted, ``000000`` wrong, ``111111`` expired. Intervention codes are
``SYN-…`` (clearly not the SHA tariff). Practitioner and facility registries reuse the
conventions of the Phase 1 fakes (``TEST-``, ``EXPIRED-``, ``SUSP-`` registration numbers).
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import threading
from collections.abc import Callable
from datetime import date
from typing import Any
from urllib.parse import parse_qs

import httpx

PREFIX = "/api/v1"
GOOD_OTP, WRONG_OTP, EXPIRED_OTP = "123456", "000000", "111111"
OUTAGE_NUMBER = "99999999"

SCRIPT = {
    "95": "timeout",
    "97": "not_found",
    "96": "not_eligible",
    "98": "inactive",
    "94": "no_contact",
    "93": "biometric_fails",
    "92": "no_fingerprints",
    "91": "stuck_pending",
    "90": "biometrics_enforced",
}

# (code, name, sub-benefit, fund, access point, mechanism, flags, level-4 tariff)
INTERVENTIONS: list[dict[str, Any]] = [
    {
        "code": "SYN-SHA-OP-001",
        "name": "Synthetic outpatient consultation",
        "subBenefit": "SYN-SB-OP",
        "fund": "SHIF",
        "accessPoint": "OP",
        "paymentMechanism": "FEE_FOR_SERVICE",
        "tariff": 1500,
    },
    {
        "code": "SYN-SHA-OP-002",
        "name": "Synthetic outpatient procedure (normal preauth)",
        "subBenefit": "SYN-SB-OP",
        "fund": "SHIF",
        "accessPoint": "OP",
        "paymentMechanism": "FEE_FOR_SERVICE",
        "needsPreauth": True,
        "tariff": 8500,
    },
    {
        "code": "SYN-SHA-OP-003",
        "name": "Synthetic elective outpatient service (elective preauth)",
        "subBenefit": "SYN-SB-OP",
        "fund": "SHIF",
        "accessPoint": "OP",
        "paymentMechanism": "FEE_FOR_SERVICE",
        "needsPreauth": True,
        "needsManualPreauthApproval": True,
        "tariff": 12000,
    },
    {
        "code": "SYN-SHA-IP-001",
        "name": "Synthetic inpatient bed day (per diem; no published level rate)",
        "subBenefit": "SYN-SB-IP",
        "fund": "SHIF",
        "accessPoint": "IP",
        "paymentMechanism": "PER_DIEM",
        "tariff": None,
    },
    {
        "code": "SYN-SHA-IP-002",
        "name": "Synthetic inpatient surgery (specialised preauth)",
        "subBenefit": "SYN-SB-IP",
        "fund": "SHIF",
        "accessPoint": "IP",
        "paymentMechanism": "FEE_FOR_SERVICE",
        "needsPreauth": True,
        "requiresSurgicalPreauth": True,
        "tariff": 85000,
    },
    {
        "code": "SYN-SHA-IP-003",
        "name": "Synthetic elective inpatient admission (elective preauth)",
        "subBenefit": "SYN-SB-IP",
        "fund": "SHIF",
        "accessPoint": "IP",
        "paymentMechanism": "FEE_FOR_SERVICE",
        "needsPreauth": True,
        "needsManualPreauthApproval": True,
        "tariff": 45000,
    },
    {
        "code": "SYN-PHC-001",
        "name": "Synthetic primary care visit (capitation)",
        "subBenefit": "SYN-SB-PHC",
        "fund": "UHC",
        "accessPoint": "OP",
        "paymentMechanism": "CAPITATION",
        "tariff": 0,
    },
    {
        "code": "SYN-ECC-001",
        "name": "Synthetic emergency stabilisation (ECCIF protocol)",
        "subBenefit": "SYN-SB-EM",
        "fund": "ECCIF",
        "accessPoint": "OP",
        "paymentMechanism": "FEE_FOR_SERVICE",
        "needsDoctorAuthorization": True,
        "tariff": 10000,
    },
]

SUB_BENEFITS = [
    {
        "code": "SYN-SB-OP",
        "name": "Synthetic outpatient services",
        "fund": "SHIF",
        "accessPoint": "OP",
    },
    {
        "code": "SYN-SB-IP",
        "name": "Synthetic inpatient services",
        "fund": "SHIF",
        "accessPoint": "IP",
    },
    {
        "code": "SYN-SB-PHC",
        "name": "Synthetic primary health care",
        "fund": "UHC",
        "accessPoint": "OP",
    },
    {"code": "SYN-SB-EM", "name": "Synthetic emergency care", "fund": "ECCIF", "accessPoint": "OP"},
]

ID_TYPES = {
    "National ID",
    "ClientRegistry ID",
    "Birth Notification",
    "Birth Certificate",
    "Alien ID",
    "Refugee ID",
    "Mandate Number",
}


def _outcome(number: str) -> str:
    digits = re.sub(r"\D", "", number)
    if digits == OUTAGE_NUMBER:
        return "outage"
    return SCRIPT.get(digits[-2:], "eligible") if len(digits) >= 2 else "eligible"


def _json(status: int, body: Any) -> httpx.Response:
    return httpx.Response(status, json=body)


def _error(status: int, error: str, message: str) -> httpx.Response:
    return _json(status, {"error": error, "message": message})


def cr_id_for(number: str) -> str:
    return f"CR-SYN-N{re.sub(r'\D', '', number)}"


def _number_in(cr_id: str) -> str:
    match = re.match(r"^CR-SYN-N(\d+)$", cr_id)
    return match.group(1) if match else ""


class FakeHie:
    """The fake HIE. ``fail_next`` injects one fault per path (``timeout``, ``connect``,
    ``500``, ``429``, ``401``); ``calls`` records (method, path) for assertions."""

    def __init__(self, *, token_lifetime: int = 3600, clock: Callable[[], date] = date.today):
        self.token_lifetime = token_lifetime
        self._clock = clock
        self._lock = threading.Lock()
        self.tokens: set[str] = set()
        self.fail_next: dict[str, str] = {}
        self.calls: list[tuple[str, str]] = []
        self.headers_seen: list[dict[str, str]] = []
        self.rejected_tokens: set[str] = set()
        self.otp_requests: list[dict[str, Any]] = []

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def revoke_tokens(self) -> None:
        """Make every issued token invalid (the HIE expired them early)."""
        with self._lock:
            self.tokens.clear()

    # --- dispatcher ---

    def handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        path = path[len(PREFIX) :] if path.startswith(PREFIX) else path
        with self._lock:
            self.calls.append((request.method, path))
            self.headers_seen.append(dict(request.headers))
            fault = self.fail_next.pop(path, None)
        if fault == "timeout":
            raise httpx.ReadTimeout("fake HIE timeout", request=request)
        if fault == "connect":
            raise httpx.ConnectError("fake HIE unreachable", request=request)
        if fault == "500":
            return _error(500, "internal_error", "Internal Server Error - Service error occurred")
        if fault == "429":
            return httpx.Response(
                429,
                headers={"Retry-After": "1"},
                json={"error": "rate_limited", "message": "Too many requests"},
            )
        if path == "/tenants/token" and request.method == "POST":
            return self.token(request)
        bearer = request.headers.get("Authorization", "").removeprefix("Bearer ")
        with self._lock:
            valid = bearer in self.tokens
        if fault == "401" or not valid:
            return _error(
                401, "unauthorized", "Unauthorized - Invalid or missing authentication token"
            )
        params = {k: v[0] for k, v in parse_qs(request.url.query.decode()).items()}
        body: dict[str, Any] = json.loads(request.content) if request.content else {}
        route = ROUTES.get((request.method, path))
        if route is None:
            reject = re.match(r"^/claims/authorizations/([^/]+)/reject$", path)
            if reject and request.method == "POST":
                return self.reject_authorization(reject.group(1))
            return _error(404, "not_found", "Not found")
        return route(self, params, body)

    # --- auth ---

    def token(self, request: httpx.Request) -> httpx.Response:
        form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        if not form.get("client_id") or not form.get("client_secret"):
            return _error(400, "invalid_request", "client_id and client_secret are required")
        if form["client_secret"] == "wrong":  # noqa: S105 - scripted refusal
            return _error(400, "invalid_client", "Invalid client credentials")
        token = "fakehie." + secrets.token_hex(12)
        with self._lock:
            self.tokens.add(token)
        return _json(
            200, {"access_token": token, "expires_in": self.token_lifetime, "token_type": "Bearer"}
        )

    # --- registries ---

    def _member(self, id_type: str, number: str) -> dict[str, Any] | None:
        from apps.patients.adapters.client_registry import fake as registry

        ours = {
            "National ID": "national_id",
            "Alien ID": "alien_id",
            "Refugee ID": "refugee_id",
        }.get(id_type)
        person = registry.RECORDS.get((ours, number.upper())) if ours else None
        if id_type == "ClientRegistry ID":
            person = next((p for p in registry.RECORDS.values() if p.cr_id == number), None)
            if person is None and _number_in(number):
                return self._member("National ID", _number_in(number))
        if person is None and ours == "national_id" and registry.GENERATED.match(number):
            person = registry.generated(number)
        if person is not None:
            return {
                "id": person.cr_id,
                "resourceType": "Patient",
                "first_name": person.given_name,
                "middle_name": person.middle_name,
                "last_name": person.family_name,
                "gender": person.sex,
                "date_of_birth": person.date_of_birth.isoformat() if person.date_of_birth else "",
                "phone": person.phone,
                "identification_type": id_type,
                "identification_number": number,
                "other_identifications": [],
            }
        if ours == "national_id" and re.fullmatch(r"\d{8}", number):
            digest = hashlib.sha256(number.encode()).digest()
            return {
                "id": cr_id_for(number),
                "resourceType": "Patient",
                "first_name": "Synthetic",
                "middle_name": "",
                "last_name": f"Member{number[-4:]}",
                "gender": "female" if digest[0] % 2 == 0 else "male",
                "date_of_birth": date(
                    1950 + digest[1] % 55, 1 + digest[2] % 12, 1 + digest[3] % 28
                ).isoformat(),
                "phone": "",
                "identification_type": id_type,
                "identification_number": number,
                "other_identifications": [],
            }
        return None

    def patients(self, params: dict[str, str], body: dict[str, Any]) -> httpx.Response:
        id_type, number = (
            params.get("identification_type", ""),
            params.get("identification_number", ""),
        )
        if not id_type or not number or id_type not in ID_TYPES:
            return _error(
                400,
                "bad_request",
                "Bad Request - Missing query parameters or invalid request input",
            )
        outcome = _outcome(_number_in(number) or number)
        if outcome == "outage":
            return _error(503, "unavailable", "Service unavailable")
        if outcome == "timeout":
            raise httpx.ReadTimeout("fake HIE timeout")
        member = None if outcome == "not_found" else self._member(id_type, number)
        if member is None:
            return _error(404, "not_found", "Patient not found")
        return _json(200, member)

    def professionals(self, params: dict[str, str], body: dict[str, Any]) -> httpx.Response:
        number = params.get("identification_number", "").strip().upper()
        regulator = params.get("regulator", "")
        if not number or params.get("identification_type") not in {
            "registration_number",
            "National ID",
            "Alien ID",
            "Refugee ID",
        }:
            return _error(400, "bad_request", "Bad Request - Missing required query parameters")
        if not number.startswith(("TEST-", "EXPIRED-", "SUSP-")):
            return _error(404, "not_found", "Practitioner not found")
        digest = hashlib.sha256(f"{regulator}:{number}".encode()).hexdigest()[:10].upper()
        year = self._clock().year
        end = date(year - 1, 12, 31) if number.startswith("EXPIRED-") else date(year + 1, 12, 31)
        return _json(
            200,
            {
                "message": {
                    "identifiers": {
                        "client_registry_id": f"PUID-{digest}",
                        "identification_type": "registration_number",
                        "identification_number": number,
                    },
                    "licenses": [
                        {
                            "id": f"LIC-{digest}",
                            "license_type": "practice",
                            "license_start": date(year - 1, 1, 1).isoformat(),
                            "license_end": end.isoformat(),
                            "external_reference_id": "",
                        }
                    ],
                    "membership": {
                        "registration_id": number,
                        "licensing_body": regulator,
                        "is_active": 0 if number.startswith("SUSP-") else 1,
                    },
                }
            },
        )

    def facilities(self, params: dict[str, str], body: dict[str, Any]) -> httpx.Response:
        identifier = params.get("identifier", "").strip().upper()
        if not identifier and not params.get("name"):
            return _error(400, "bad_request", "Bad Request - Missing required query parameters")
        if not identifier.startswith("FID-SYN-"):
            return _error(404, "not_found", "Facility not found")
        suspended = identifier.endswith("9")
        year = self._clock().year
        return _json(
            200,
            {
                "fidCode": identifier,
                "frCode": identifier,
                "officialName": "Synthetic Facility " + identifier[-6:],
                "kephLevel": "Level 4",
                "facilityLicenseStatus": "Licensed",
                "facilityLicenseEndDate": date(year, 12, 31).isoformat(),
                "shaContractStatus": "Suspended" if suspended else "Active",
                "shaContractedServices": ["SYN-SB-OP", "SYN-SB-IP", "SYN-SB-PHC", "SYN-SB-EM"],
                "SHAOperationStatus": {
                    "operationalStatus": "Suspended" if suspended else "Operational"
                },
            },
        )

    # --- eligibility and benefits ---

    def eligibility(self, params: dict[str, str], body: dict[str, Any]) -> httpx.Response:
        id_type, number = (
            params.get("identification_type", ""),
            params.get("identification_number", ""),
        )
        if not id_type or not number or id_type not in ID_TYPES:
            return _error(
                400,
                "bad_request",
                "Bad Request - Missing query parameters or invalid request input",
            )
        outcome = _outcome(_number_in(number) or number)
        if outcome == "outage":
            return _error(503, "unavailable", "Service unavailable")
        if outcome == "timeout":
            raise httpx.ReadTimeout("fake HIE timeout")
        if outcome == "not_found":
            return _error(404, "not_found", "Beneficiary not found")
        year = self._clock().year
        cr_id = number if id_type == "ClientRegistry ID" else cr_id_for(number)
        result: dict[str, Any] = {
            "requestIdNumber": number,
            "requestIdType": 1,
            "memberCrNumber": cr_id,
            "isAlive": True,
            "facilityBiometricsEnforced": outcome == "biometrics_enforced",
            "whitelistedForOTP": outcome not in ("no_contact", "biometrics_enforced"),
            "statusCode": "200",
            "statusDesc": "Success",
            "schemes": [],
        }
        if outcome == "not_eligible":
            result["statusDesc"] = "No active cover"
            return _json(200, result)
        status = "SUSPENDED" if outcome == "inactive" else "ACTIVE"
        coverage = {
            "status": status,
            "startDate": date(year, 1, 1).isoformat(),
            "endDate": date(year, 12, 31).isoformat(),
            "reason": "Contributions in arrears" if status == "SUSPENDED" else "",
            "message": "Cover suspended" if status == "SUSPENDED" else "Cover active",
            "possibleSolution": "Pay outstanding contributions" if status == "SUSPENDED" else "",
        }
        result["schemes"] = [
            {
                "schemeId": 1,
                "schemeName": "SHIF",
                "memberType": "PRINCIPAL",
                "coverage": coverage,
                "policy": {
                    "number": "SYN-POL-1",
                    "startDate": coverage["startDate"],
                    "endDate": coverage["endDate"],
                },
            },
            {
                "schemeId": 2,
                "schemeName": "UHC",
                "memberType": "PRINCIPAL",
                "coverage": coverage,
                "policy": {
                    "number": "SYN-POL-2",
                    "startDate": coverage["startDate"],
                    "endDate": coverage["endDate"],
                },
            },
        ]
        return _json(200, result)

    @staticmethod
    def _page(results: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "count": len(results),
            "currentPage": 1,
            "totalPages": 1,
            "pageSize": max(len(results), 1),
            "startIndex": 0,
            "endIndex": len(results),
            "next": "",
            "previous": "",
            "results": results,
        }

    def sub_benefits(self, params: dict[str, str], body: dict[str, Any]) -> httpx.Response:
        if not params.get("patient_id"):
            return _error(400, "bad_request", "patient_id is required")
        rows = [
            {
                **row,
                "active": True,
                "status": "ACTIVE",
                "parentBenefitCode": "SYN-SHA",
                "allowedInterventions": [
                    i["code"] for i in INTERVENTIONS if i["subBenefit"] == row["code"]
                ],
            }
            for row in SUB_BENEFITS
        ]
        return _json(200, self._page(rows))

    def interventions(self, params: dict[str, str], body: dict[str, Any]) -> httpx.Response:
        if not params.get("patient_id"):
            return _error(400, "bad_request", "patient_id is required")
        wanted = params.get("sub_benefit_code")
        rows = []
        for item in INTERVENTIONS:
            if wanted and item["subBenefit"] != wanted:
                continue
            rows.append(
                {
                    "code": item["code"],
                    "name": item["name"],
                    "fund": item["fund"],
                    "accessPoint": item["accessPoint"],
                    "paymentMechanism": item["paymentMechanism"],
                    "benefitCode": item["subBenefit"],
                    "needsPreauth": item.get("needsPreauth", False),
                    "needsManualPreauthApproval": item.get("needsManualPreauthApproval", False),
                    "needsDoctorAuthorization": item.get("needsDoctorAuthorization", False),
                    "requiresSurgicalPreauth": item.get("requiresSurgicalPreauth", False),
                    "kephLevelTarriff": item["tariff"],
                    "level4Tariff": item["tariff"],
                    "applicableDocumentTypes": ["CLAIM_FORM", "INVOICE", "DISCHARGE_SUMMARY"],
                    "active": True,
                    "status": "ACTIVE",
                }
            )
        return _json(200, self._page(rows))

    # --- consent ---

    def contacts(self, params: dict[str, str], body: dict[str, Any]) -> httpx.Response:
        patient_id = params.get("patient_id", "")
        if not patient_id:
            return _error(400, "bad_request", "patient_id is required")
        if _outcome(_number_in(patient_id) or patient_id) == "no_contact":
            return _json(200, {"count": 0, "results": []})
        return _json(
            200,
            {
                "count": 1,
                "results": [
                    {
                        "id": 1,
                        "contactType": "PHONE",
                        "contactValue": "+254700***001",
                        "isConfirmed": True,
                        "active": True,
                    }
                ],
            },
        )

    def send_otp(self, params: dict[str, str], body: dict[str, Any]) -> httpx.Response:
        if not body.get("patient_id") or not body.get("intervention_codes"):
            return _error(400, "bad_request", "Bad Request - Missing required fields")
        if _outcome(_number_in(body["patient_id"]) or body["patient_id"]) == "no_contact":
            return _error(400, "no_valid_contact", "Beneficiary has no valid contact")
        with self._lock:
            self.otp_requests.append(body)
        return _json(
            200,
            {
                "message": "OTP sent successfully",
                "data": {"consent_request_id": "fake-cr-" + secrets.token_hex(6)},
            },
        )

    def _authorization(self, outcome: str, body: dict[str, Any], status: str) -> dict[str, Any]:
        elective = any("-003" in code for code in body.get("interventions", []))
        return {
            "guid": f"fakeauth-{outcome}-{secrets.token_hex(6)}",
            "status": status,
            "token": "FAKETOK" + secrets.token_hex(6).upper(),
            "isElective": elective,
            "isEmergency": bool(body.get("is_emergency")),
            "authorizationReason": "",
            "shaVerificationRequest": {
                "requestUrl": "https://hie.fake.invalid/biometrics/capture/" + secrets.token_hex(6),
                "embedExpiry": 600,
            },
        }

    def authorize(self, params: dict[str, str], body: dict[str, Any]) -> httpx.Response:
        if (
            not body.get("patient_id")
            or not body.get("interventions")
            or not body.get("service_type")
        ):
            return _error(400, "bad_request", "Bad Request - Missing required fields")
        outcome = _outcome(_number_in(body["patient_id"]) or body["patient_id"])
        if "otp" in body:  # OTP variant: authorised at once when the code is right
            if body["otp"] != GOOD_OTP:
                return self._otp_refusal(body["otp"])
            return _json(200, self._authorization("ok", body, "AUTHORIZED"))
        if outcome == "stuck_pending":
            return _error(
                400,
                "pending_authorization_exists",
                "A pending authorization exists for this beneficiary",
            )
        kind = {"biometric_fails": "fail", "no_fingerprints": "nobio"}.get(outcome, "ok")
        return _json(200, self._authorization(kind, body, "PENDING"))

    def authorizations(self, params: dict[str, str], body: dict[str, Any]) -> httpx.Response:
        guid, patient_id = params.get("guid", ""), params.get("patient_id", "")
        if not (guid or patient_id or params.get("token")):
            return _error(400, "bad_request", "token, guid or patient_id is required")
        if guid:
            match = re.match(r"^fakeauth-(ok|fail|nobio)-", guid)
            if not match:
                return _json(200, [])
            kind = match.group(1)
            row: dict[str, Any] = {"guid": guid, "status": "AUTHORIZED", "authorizationReason": ""}
            if kind == "fail":
                row["status"] = "REJECTED"
            elif kind == "nobio":
                row.update(
                    status="REJECTED", authorizationReason="BIOMETRICS_NOT_FOUND_OTP_ALLOWED"
                )
            return _json(200, [row])
        if _outcome(_number_in(patient_id) or patient_id) == "stuck_pending":
            token = "FAKESTUCK" + hashlib.sha256(patient_id.encode()).hexdigest()[:6].upper()
            with self._lock:
                if token in self.rejected_tokens:
                    return _json(
                        200, [{"guid": "fakeauth-stuck", "status": "REJECTED", "token": token}]
                    )
            return _json(200, [{"guid": "fakeauth-stuck", "status": "PENDING", "token": token}])
        return _json(200, [])

    def reject_authorization(self, token: str) -> httpx.Response:
        with self._lock:
            self.rejected_tokens.add(token)
        return _json(200, {"message": "Authorization rejected"})

    def _otp_refusal(self, otp: str) -> httpx.Response:
        if otp == EXPIRED_OTP:
            return _error(400, "otp_expired", "OTP has expired")
        return _error(400, "invalid_otp", "Invalid OTP")

    def visit(self, params: dict[str, str], body: dict[str, Any]) -> httpx.Response:
        required = ("intervention_codes", "patient_id", "service_type")
        if any(not body.get(name) for name in required):
            return _error(400, "bad_request", "Bad Request - Missing required fields")
        if body["service_type"] not in {"CAPITATION", "OUTPATIENT", "INPATIENT", "EMERGENCY"}:
            return _error(400, "bad_request", "Invalid service_type")
        if "otp" in body:
            if body["otp"] != GOOD_OTP:
                return self._otp_refusal(body["otp"])
        elif "auth_guid" in body:
            if not str(body["auth_guid"]).startswith("fakeauth-ok-"):
                return _error(
                    400, "authorization_not_authorized", "Authorization is not authorized"
                )
        else:
            return _error(400, "bad_request", "otp or auth_guid is required")
        return _json(
            200,
            {
                "authorization_code": "FAKEVC" + secrets.token_hex(6).upper(),
                "visit_number": "SYN-V-" + secrets.token_hex(4).upper(),
                "workflow_state": "OPEN",
                "claim_id": int(secrets.token_hex(3), 16),
                "service_type": body["service_type"],
                "interventions": [
                    {"intervention_code": code} for code in body["intervention_codes"]
                ],
            },
        )


ROUTES: dict[
    tuple[str, str], Callable[[FakeHie, dict[str, str], dict[str, Any]], httpx.Response]
] = {
    ("GET", "/patients"): FakeHie.patients,
    ("GET", "/professionals"): FakeHie.professionals,
    ("GET", "/facilities/search"): FakeHie.facilities,
    ("GET", "/patients/eligibility"): FakeHie.eligibility,
    ("GET", "/patients/sub-benefits"): FakeHie.sub_benefits,
    ("GET", "/patients/benefits/interventions"): FakeHie.interventions,
    ("GET", "/patients/contacts"): FakeHie.contacts,
    ("POST", "/claims/otp"): FakeHie.send_otp,
    ("POST", "/claims/authorize"): FakeHie.authorize,
    ("GET", "/claims/authorizations"): FakeHie.authorizations,
    ("POST", "/claims/visit"): FakeHie.visit,
}

_shared: FakeHie | None = None
_shared_lock = threading.Lock()


def shared() -> FakeHie:
    """The process-wide fake used when ``SHA_MODE=fake`` (keeps rejected authorisations)."""
    global _shared
    with _shared_lock:
        if _shared is None:
            _shared = FakeHie()
        return _shared
