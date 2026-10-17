"""One ``payer`` fixture per adapter fake. Each comes with a script: how to make a member
with a given outcome and how to complete its consent step. The contract tests are written
once against the port and run for every payer (INSURANCE.md §2). Sandboxes join with
``RUN_LIVE=1`` and credentials (none exist yet: every vendor step is an owner action)."""

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.insurance.adapters.manual import ManualGateway
from apps.insurance.adapters.sha_hie import ShaHieGateway
from apps.insurance.adapters.slade360.fake import FakeSlade360Gateway
from apps.insurance.adapters.smart.fake import FakeSmartGateway
from apps.insurance.gateway import (
    AuthMethod,
    AuthProof,
    ClaimDiagnosis,
    ClaimDraft,
    ClaimLineDraft,
    CoverageRef,
    PayerGateway,
    Practitioner,
    PreauthDraft,
    Secret,
    VisitRef,
)
from apps.interop.hie.client import HieClient, HieConfig, TokenCache
from apps.interop.hie.fake import FakeHie

DOCTOR = Practitioner("KMPDC", "TEST-1001", "PUID-SYN-1")


@dataclass
class Consent:
    method: AuthMethod
    good: AuthProof
    wrong: AuthProof
    expired: AuthProof
    contact_id: str = ""  # OTP: the payer asks which phone to use first


@dataclass
class Script:
    name: str
    gateway: PayerGateway
    coverage: Callable[[str], CoverageRef]
    consent: Consent | None = None
    claims: bool = True  # claim submission built for this adapter (SHA: P3-SHA-03)
    outcomes: set[str] = field(
        default_factory=lambda: {"eligible", "not_found", "inactive", "outage"}
    )


def visit(service_type="outpatient") -> VisitRef:
    return VisitRef("0190a000-0000-7000-8000-000000000001", service_type, timezone.now(), DOCTOR)


def claim(coverage: CoverageRef, total: str, number: str = "CLM-SYN-0001") -> ClaimDraft:
    amount = Decimal(total)
    today = timezone.localdate()
    return ClaimDraft(
        claim_id="0190a000-0000-7000-8000-0000000000c1",
        number=number,
        visit=visit(),
        coverage=coverage,
        billable_from=today,
        billable_to=today,
        total=amount,
        lines=(
            ClaimLineDraft(
                line_id="0190a000-0000-7000-8000-0000000000l1",
                payer_code="SYN-PVT-CONS",
                description="Synthetic consultation",
                quantity=Decimal("1"),
                unit_price=amount,
                net=amount,
                serviced_from=today,
                serviced_to=today,
                diagnosis_codes=("CA40.Z",),
            ),
        ),
        diagnoses=(ClaimDiagnosis("CA40.Z", "icd11", "Pneumonia, unspecified", True),),
        practitioners=(DOCTOR,),
    )


def preauth(coverage: CoverageRef, amount: str) -> PreauthDraft:
    today = timezone.localdate()
    return PreauthDraft(
        preauth_id="0190a000-0000-7000-8000-0000000000p" + amount[-1],
        coverage=coverage,
        visit=visit(),
        intervention_code="SYN-PVT-SURG",
        kind="surgical",
        service_from=today,
        service_to=today,
        estimated_amount=Decimal(amount),
        diagnoses=(ClaimDiagnosis("CA40.Z", "icd11", "Pneumonia, unspecified", True),),
        practitioners=(DOCTOR,),
    )


def _sha() -> Script:
    numbers = {
        "eligible": "10000011",
        "not_found": "10000097",
        "inactive": "10000098",
        "outage": "99999999",
    }
    client = HieClient(
        HieConfig(
            "fake",
            "https://hie.fake.invalid/api/v1",
            "contract-client",
            "contract-secret",
            "FID-SYN-000001",
        ),
        transport=FakeHie().transport(),
        tokens=TokenCache(),
        sleep=lambda seconds: None,
    )

    def coverage(outcome: str) -> CoverageRef:
        return CoverageRef(
            coverage_id=f"cov-sha-{outcome}",
            payer_code="sha",
            scheme_code="shif",
            scheme_kind="shif",
            member_number=Secret("SHA-SYN-000011"),
            cr_id=f"CR-SYN-N{numbers[outcome]}",
            facility_code="FID-SYN-000001",
        )

    return Script(
        "sha_hie",
        ShaHieGateway(client),
        coverage,
        Consent(
            AuthMethod.OTP,
            AuthProof(otp=Secret("123456")),
            AuthProof(otp=Secret("000000")),
            AuthProof(otp=Secret("111111")),
            contact_id="1",
        ),
        claims=False,
    )


def _private(name: str, gateway: PayerGateway, consent: Consent | None) -> Script:
    numbers = {
        "eligible": "SYN-X-00011",
        "not_found": "SYN-X-00097",
        "inactive": "SYN-X-00098",
        "outage": "SYN-X-00095",
    }

    def coverage(outcome: str) -> CoverageRef:
        return CoverageRef(
            coverage_id=f"cov-{name}-{outcome}",
            payer_code=f"syn-{name}",
            scheme_code="gold",
            scheme_kind="corporate",
            member_number=Secret(numbers[outcome]),
        )

    return Script(name, gateway, coverage, consent)


def _manual() -> Script:
    def coverage(outcome: str) -> CoverageRef:
        return CoverageRef(
            "cov-manual", "syn-employer", "staff", "corporate", Secret("SYN-E-00011")
        )

    return Script("manual", ManualGateway(), coverage, outcomes=set())


SCRIPTS: dict[str, Callable[[], Script]] = {
    "sha_hie": _sha,
    "smart": lambda: _private(
        "smart",
        FakeSmartGateway(),
        Consent(
            AuthMethod.CARD_OR_CODE,
            AuthProof(member_code=Secret("1234")),
            AuthProof(member_code=Secret("0000")),
            AuthProof(member_code=Secret("1111")),
        ),
    ),
    "slade360": lambda: _private("slade360", FakeSlade360Gateway(), None),
    "manual": _manual,
}


@pytest.fixture(params=sorted(SCRIPTS))
def payer(request, db) -> Script:
    return SCRIPTS[request.param]()
