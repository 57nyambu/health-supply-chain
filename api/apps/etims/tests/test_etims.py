"""KRA eTIMS vendor part in fake mode (P3-TAX-01 acceptance 1 and 3; KE-KRA-01): payload
per the VSCU spec, VAT inside inclusive prices, receipts stored, offline queue with retry,
one invoice number per document, ETIMS_MODE=off by default."""

import json
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
import time_machine
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from apps.etims import fake, services, vscu
from apps.etims.models import EtimsTransmission
from apps.integrations.models import ExchangeLog

pytestmark = [pytest.mark.django_db, pytest.mark.req("KE-KRA-01")]

CONSULT = vscu.TaxLine(
    "KE2NTU0000001", "Synthetic consultation", Decimal("1"), Decimal("1500.00"), Decimal("0"), "A"
)
DRUG = vscu.TaxLine(
    "KE2NTU0000002", "Synthetic medicine", Decimal("2"), Decimal("580.00"), Decimal("10.00"), "B"
)


@pytest.fixture(autouse=True)
def _fake(settings):
    settings.ETIMS_MODE = "fake"
    settings.ETIMS_PIN = "P000000001Z"
    fake._shared = None


def sale(facility, number="INV-SYN-0001", lines=(CONSULT, DRUG), source=None) -> EtimsTransmission:
    doc = services.queue(
        facility_id=facility.pk,
        kind=EtimsTransmission.Kind.SALE,
        source_id=source or uuid.uuid4(),
        trader_invoice_no=number,
        lines=list(lines),
    )
    assert doc is not None
    return doc


def test_off_by_default_queues_nothing(settings, facility):
    settings.ETIMS_MODE = "off"
    assert services.enabled() is False
    assert (
        services.queue(
            facility_id=facility.pk,
            kind="sale",
            source_id=uuid.uuid4(),
            trader_invoice_no="X",
            lines=[CONSULT],
        )
        is None
    )
    assert services.transmit_due() == (0, 0)
    with pytest.raises(ImproperlyConfigured):
        services.client()


def test_vat_is_taken_from_inclusive_prices_like_the_spec_sample():
    assert vscu.tax_in(Decimal("200000"), "B") == Decimal("27586.21")  # 16 %
    assert vscu.tax_in(Decimal("1500.00"), "A") == Decimal("0.00")  # exempt
    with pytest.raises(ValueError, match="tax type"):
        vscu.build_save_sales(
            vscu.TaxDocument(
                "X",
                1,
                0,
                "S",
                timezone.now(),
                (vscu.TaxLine("I", "n", Decimal(1), Decimal(1), Decimal(0), "Z"),),
            ),
            tin="P1",
            branch_id="00",
            user="u",
        )


def test_sale_payload_follows_the_spec_and_is_accepted(facility):
    doc = sale(facility)
    body = json.loads(doc.payload_json)
    assert (body["rcptTyCd"], body["salesTyCd"], body["salesSttsCd"], body["pmtTyCd"]) == (
        "S",
        "N",
        "02",
        "01",
    )
    assert body["custNm"] is None  # never a patient's name
    assert body["totItemCnt"] == 2 and body["invcNo"] == doc.etims_invoice_no == 1
    assert '"totAmt": 2650.00' in doc.payload_json  # exact decimals: 1500 + 2 x 580 - 10
    assert body["taxblAmtB"] == 1150.0 and body["taxAmtB"] == 158.62 and body["taxblAmtA"] == 1500.0
    drug = body["itemList"][1]
    assert (drug["splyAmt"], drug["dcAmt"], drug["totAmt"], drug["taxTyCd"]) == (
        1160.0,
        10.0,
        1150.0,
        "B",
    )
    sent = services.transmit(doc)
    assert sent.status == "accepted" and sent.receipt_no == 1
    assert sent.internal_data and sent.receipt_signature and sent.sdc_id == "SYN-SDC-0001"
    assert ExchangeLog.objects.filter(integration="etims.vscu", outcome="success").exists()


def test_numbers_are_sequential_and_a_document_is_queued_once(facility):
    source = uuid.uuid4()
    first = sale(facility, source=source)
    again = sale(facility, source=source)
    second = sale(facility, number="INV-SYN-0002")
    assert first.pk == again.pk
    assert (first.etims_invoice_no, second.etims_invoice_no) == (1, 2)


def test_offline_documents_wait_and_are_retried_with_backoff(facility):
    doc = sale(facility, number="INV-SYN-OFFLINE-1")
    assert services.transmit(doc).status == "queued"
    doc.refresh_from_db()
    assert doc.attempts == 1 and doc.next_attempt_at is not None
    assert doc.next_attempt_at > timezone.now()
    assert services.transmit_due() == (0, 0)  # not due yet
    payload = doc.payload_json.replace("OFFLINE", "ONLINE")
    EtimsTransmission.objects.filter(pk=doc.pk).update(payload_json=payload)  # the VSCU is back
    with time_machine.travel(timezone.now() + timedelta(minutes=5)):
        assert services.transmit_due() == (1, 0)
    doc.refresh_from_db()
    assert doc.status == "accepted" and doc.attempts == 2


def test_resending_an_invoice_number_is_flagged_not_duplicated(facility):
    doc = sale(facility)
    services.transmit(doc)
    EtimsTransmission.objects.filter(pk=doc.pk).update(status="queued")
    doc.refresh_from_db()
    assert services.transmit(doc).status == "duplicate"
    assert len(fake.shared().received) == 1


def test_rejected_payload_needs_correction(facility):
    doc = sale(facility)
    broken = json.loads(doc.payload_json)
    broken["itemList"] = []
    EtimsTransmission.objects.filter(pk=doc.pk).update(payload_json=json.dumps(broken))
    doc.refresh_from_db()
    rejected = services.transmit(doc)
    assert (rejected.status, rejected.result_code) == ("rejected", "910")


def test_credit_note_points_at_the_accepted_invoice(facility):
    invoice = services.transmit(sale(facility))
    with pytest.raises(ValueError, match="accepted"):
        services.queue(
            facility_id=facility.pk,
            kind="credit_note",
            source_id=uuid.uuid4(),
            trader_invoice_no="CN-1",
            lines=[CONSULT],
            original=sale(facility, number="INV-2"),
        )
    note = services.queue(
        facility_id=facility.pk,
        kind="credit_note",
        source_id=uuid.uuid4(),
        trader_invoice_no="CN-SYN-0001",
        lines=[CONSULT],
        original=invoice,
        credit_note_reason="refund",
    )
    assert note is not None
    body = json.loads(note.payload_json)
    assert (body["rcptTyCd"], body["orgInvcNo"], body["rfdRsnCd"]) == (
        "R",
        invoice.etims_invoice_no,
        "06",
    )
    assert services.transmit(note).status == "accepted"


def test_vscu_mode_needs_url_and_pin(settings):
    settings.ETIMS_MODE = "vscu"
    settings.ETIMS_VSCU_URL = ""
    with pytest.raises(ImproperlyConfigured, match="ETIMS_VSCU_URL"):
        services.client()
    settings.ETIMS_MODE = "bogus"
    with pytest.raises(ImproperlyConfigured):
        services.enabled()
