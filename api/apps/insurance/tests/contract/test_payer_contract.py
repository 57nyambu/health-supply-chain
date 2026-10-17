"""The payer contract (INSURANCE.md §2): every adapter fake behaves the same way at the
port, so services never special-case a payer. Run with ``pytest -m payers``."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.insurance.gateway import (
    AuthFailed,
    AuthMethod,
    ChallengeStatus,
    ClaimRef,
    ClaimState,
    EligibilityStatus,
    MemberQuery,
    PayerCapabilities,
    PayerGateway,
    PayerVisitHandle,
    PreauthState,
    Secret,
    SubmissionOutcomeUnknown,
    TransientError,
    Unsupported,
)

from .conftest import Script, claim, preauth, visit

pytestmark = [pytest.mark.payers, pytest.mark.django_db]


def _handle(script: Script) -> PayerVisitHandle:
    return PayerVisitHandle(consent_token=Secret(""), visit_reference="SYN-V-1")


def _authorise(script: Script, proof_name: str = "good"):
    consent = script.consent
    assert consent is not None
    gateway, coverage = script.gateway, script.coverage("eligible")
    challenge = gateway.start_authorisation(coverage, visit(), ["SYN-SHA-OP-001"], consent.method)
    if challenge.status == ChallengeStatus.CHOOSE_CONTACT:
        assert challenge.contacts and all("*" in c.masked for c in challenge.contacts)
        challenge = gateway.start_authorisation(
            coverage, visit(), ["SYN-SHA-OP-001"], consent.method, contact_id=consent.contact_id
        )
    return gateway.complete_authorisation(
        challenge, getattr(consent, proof_name), coverage, visit()
    )


def test_implements_the_port(payer: Script):
    assert isinstance(payer.gateway, PayerGateway)
    assert isinstance(payer.gateway.capabilities(), PayerCapabilities)
    assert payer.gateway.code and payer.gateway.mode


def test_eligible_member_is_eligible_with_a_member_reference(payer: Script):
    result = payer.gateway.check_eligibility(payer.coverage("eligible"), timezone.localdate())
    if "eligible" not in payer.outcomes:
        assert result.status == EligibilityStatus.PENDING and result.message  # staff confirm
        return
    assert result.status == EligibilityStatus.ELIGIBLE
    assert result.member_ref
    assert result.schemes and any(s.active for s in result.schemes)


def test_unknown_member_is_not_found(payer: Script):
    if "not_found" not in payer.outcomes:  # no eligibility service: staff confirm cover
        assert payer.name == "manual"
        return
    result = payer.gateway.check_eligibility(payer.coverage("not_found"), timezone.localdate())
    assert result.status == EligibilityStatus.NOT_FOUND


def test_inactive_cover_says_why(payer: Script):
    if "inactive" not in payer.outcomes:
        assert payer.name == "manual"
        return
    result = payer.gateway.check_eligibility(payer.coverage("inactive"), timezone.localdate())
    assert result.status == EligibilityStatus.INACTIVE
    assert result.message and not any(s.active for s in result.schemes)


def test_outage_is_a_transient_error_never_a_verdict(payer: Script):
    if "outage" not in payer.outcomes:
        assert payer.name == "manual"
        return
    with pytest.raises(TransientError) as caught:
        payer.gateway.check_eligibility(payer.coverage("outage"), timezone.localdate())
    assert caught.value.retryable


def test_member_search_matches_capability(payer: Script):
    query = MemberQuery("national_id", Secret("10000011"))
    if not payer.gateway.capabilities().member_search:
        with pytest.raises(Unsupported):
            payer.gateway.find_member(query)
        return
    if payer.name == "sha_hie":
        assert payer.gateway.find_member(query)[0].member_ref.startswith("CR-SYN-")
        assert payer.gateway.find_member(MemberQuery("national_id", Secret("10000097"))) == []
    else:
        assert payer.gateway.find_member(MemberQuery("national_id", Secret("SYN-X-00011")))
        assert payer.gateway.find_member(MemberQuery("national_id", Secret("SYN-X-00097"))) == []


def test_billable_codes_never_turn_an_unknown_tariff_into_zero(payer: Script):
    if payer.name == "manual":
        with pytest.raises(Unsupported):
            payer.gateway.list_billable(payer.coverage("eligible"))
        return
    codes = payer.gateway.list_billable(payer.coverage("eligible"))
    assert codes and all(c.code for c in codes)
    assert any(c.tariff is None for c in codes)  # an unpublished rate stays unknown (KE-SHA-08)
    assert all(c.tariff is None or isinstance(c.tariff, Decimal) for c in codes)


def test_consent_happy_path_returns_a_secret_token(payer: Script):
    caps = payer.gateway.capabilities()
    if payer.consent is None:
        assert not (caps.consent_otp or caps.consent_biometric or caps.card_or_code_auth)
        with pytest.raises(Unsupported):
            payer.gateway.start_authorisation(
                payer.coverage("eligible"), visit(), ["X"], AuthMethod.OTP
            )
        return
    handle = _authorise(payer)
    assert handle.consent_token and handle.consent_token.reveal()
    assert handle.consent_token.reveal() not in repr(handle)
    assert "[redacted]" in repr(handle.consent_token)


@pytest.mark.parametrize("proof", ["wrong", "expired"])
def test_consent_refuses_wrong_and_expired_proofs_differently(payer: Script, proof):
    if payer.consent is None:  # no member consent step at this payer
        caps = payer.gateway.capabilities()
        assert not (caps.consent_otp or caps.consent_biometric or caps.card_or_code_auth)
        return
    with pytest.raises(AuthFailed) as caught:
        _authorise(payer, proof)
    assert ("expired" in str(caught.value).lower()) is (proof == "expired")


def test_preauth_matches_capability_and_scripted_outcomes(payer: Script):
    gateway = payer.gateway
    coverage = payer.coverage("eligible")
    if not gateway.capabilities().preauth or payer.name == "sha_hie":  # SHA: P3-SHA-04
        if payer.name != "sha_hie":
            with pytest.raises(Unsupported):
                gateway.request_preauth(None, preauth(coverage, "1000.00"))
        return
    expected = {
        "1000.00": PreauthState.APPROVED,
        "1000.11": PreauthState.PARTIALLY_APPROVED,
        "1000.22": PreauthState.DECLINED,
        "1000.44": PreauthState.PENDING,
    }
    for amount, state in expected.items():
        status = gateway.preauth_status(gateway.request_preauth(None, preauth(coverage, amount)))
        assert status.state == state
        if state == PreauthState.PARTIALLY_APPROVED:
            assert status.approved_amount == Decimal("900.10")
    with pytest.raises(SubmissionOutcomeUnknown):
        gateway.request_preauth(None, preauth(coverage, "1000.99"))


def _claims(payer: Script) -> bool:
    return payer.claims


def test_submission_is_exactly_once_per_key(payer: Script):
    if not _claims(payer):
        pytest.skip("SHA claim dispatch is P3-SHA-03 (stage B)")
    coverage = payer.coverage("eligible")
    first = payer.gateway.submit_claim(_handle(payer), claim(coverage, "2500.00"), "idem-1")
    again = payer.gateway.submit_claim(_handle(payer), claim(coverage, "2500.00"), "idem-1")
    assert first.reference == again.reference
    assert first.state == ClaimState.SUBMITTED


def test_unknown_outcome_is_resolved_by_query_never_by_blind_resend(payer: Script):
    if not _claims(payer):
        pytest.skip("SHA claim dispatch is P3-SHA-03 (stage B)")
    if payer.name == "manual":  # generating a pack has no unknown outcome
        assert payer.gateway.find_claim(claim(payer.coverage("eligible"), "1.00"), "k").found
        return
    gateway, coverage = payer.gateway, payer.coverage("eligible")
    # .99: sent, answer lost, the payer has it → found, so we must not resend.
    with pytest.raises(SubmissionOutcomeUnknown):
        gateway.submit_claim(_handle(payer), claim(coverage, "2500.99"), "idem-99")
    found = gateway.find_claim(claim(coverage, "2500.99"), "idem-99")
    assert found.found and found.reference
    # .98: sent, never arrived → not found, so resubmitting with the same key is safe.
    with pytest.raises(SubmissionOutcomeUnknown):
        gateway.submit_claim(_handle(payer), claim(coverage, "2500.98"), "idem-98")
    assert gateway.find_claim(claim(coverage, "2500.98"), "idem-98").found is False


def test_claim_states_map_with_reasons(payer: Script):
    if not _claims(payer):
        pytest.skip("SHA claim dispatch is P3-SHA-03 (stage B)")
    if payer.name == "manual":  # states are entered by staff from the payer's letters
        with pytest.raises(Unsupported):
            payer.gateway.claim_status(ClaimRef("MANUAL-CLM-1"))
        return
    gateway, coverage = payer.gateway, payer.coverage("eligible")
    expected = {
        "2500.00": ClaimState.APPROVED,
        "2500.11": ClaimState.PARTIALLY_APPROVED,
        "2500.22": ClaimState.REJECTED,
        "2500.33": ClaimState.QUERIED,
        "2500.44": ClaimState.IN_REVIEW,
    }
    for total, state in expected.items():
        ref = gateway.submit_claim(
            _handle(payer), claim(coverage, total), f"idem-{total}"
        ).reference
        status = gateway.claim_status(ClaimRef(ref))
        assert status.state == state, total
        if state in (ClaimState.REJECTED, ClaimState.QUERIED):
            assert status.reasons and all(code and text for code, text in status.reasons)
    assert gateway.claim_status(ClaimRef("no-such-claim")).found is False


def test_remittances_pay_each_approved_claim_once(payer: Script):
    if not payer.gateway.capabilities().remittance_api:
        with pytest.raises(Unsupported):
            payer.gateway.fetch_remittances(timezone.now() - timedelta(days=1))
        return
    gateway, coverage = payer.gateway, payer.coverage("eligible")
    ref = gateway.submit_claim(_handle(payer), claim(coverage, "3000.00"), "idem-paid").reference
    since = timezone.now() - timedelta(days=1)
    advices = gateway.fetch_remittances(since)
    assert [line.claim_reference for a in advices for line in a.lines] == [ref]
    assert advices[0].amount == Decimal("3000.00")
    assert gateway.fetch_remittances(since) == []
    assert gateway.claim_status(ClaimRef(ref)).state == ClaimState.PAID


def test_secrets_never_appear_in_reprs(payer: Script):
    coverage = payer.coverage("eligible")
    assert coverage.member_number.reveal() not in repr(coverage)
    assert coverage.member_number.reveal() not in str(coverage.member_number)
