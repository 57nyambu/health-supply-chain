"""KRA eTIMS through a Virtual Sales Control Unit (VSCU) — mapping, tax and client.

Source: KRA "VSCU Specification Document v2.0" (DECISIONS.md, Phase 3 findings). The VSCU is
a KRA-supplied JAR running on the facility's own server; we call its REST paths with JSON
bodies that carry ``tin`` (KRA PIN) and ``bhfId`` (branch). Sales and credit notes go to
``/trnsSales/saveSales``; the answer is ``{resultCd, resultMsg, resultDt, data{rcptNo,
intrlData, rcptSign, totRcptNo, VSCURcptPbctDate, sdcId, mrcNo}}``; ``resultCd`` ``000`` is
success. OSCU (KRA's online variant) uses its own specification and is not built (GAP-ETIMS-001).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import httpx

from apps.integrations.exchange import exchange
from apps.integrations.models import ExchangeLog

CENT = Decimal("0.01")
TIMEOUT = httpx.Timeout(30.0, connect=5.0)
SAVE_SALES = "/trnsSales/saveSales"

# 4.1 Tax Type: A exempt, B 16 %, C 0 %, D non-VAT, E 8 %.
TAX_RATES: dict[str, Decimal] = {
    "A": Decimal("0"),
    "B": Decimal("16"),
    "C": Decimal("0"),
    "D": Decimal("0"),
    "E": Decimal("8"),
}
SALE, CREDIT_NOTE = "S", "R"  # 4.9 Sales Receipt Type
NORMAL = "N"  # 4.8 Transaction Type (send only N)
APPROVED = "02"  # 4.11 Transaction Progress
PAYMENT_TYPES = {
    "cash": "01",
    "credit": "02",
    "card": "05",
    "mobile_money": "06",
    "other": "07",
}  # 4.10
CREDIT_NOTE_REASONS = {
    "refund": "06",
    "wrong_amount": "09",
    "wrong_quantity": "10",
    "wrong_item": "11",
    "other": "13",
}  # 4.16
SUCCESS, DUPLICATE = "000", "994"  # 4.14 API Response Code


@dataclass(frozen=True)
class TaxLine:
    item_code: str  # the service's eTIMS item code (billing.Service.etims_item_code)
    name: str
    quantity: Decimal
    unit_price: Decimal  # VAT-inclusive
    discount: Decimal
    tax_type: str  # A to E
    item_class_code: str = ""
    quantity_unit: str = "U"
    package_unit: str = "NT"


@dataclass(frozen=True)
class TaxDocument:
    trader_invoice_no: str
    invoice_no: int
    original_invoice_no: int
    receipt_type: str  # S | R
    confirmed_at: datetime
    lines: tuple[TaxLine, ...]
    payment_type: str = "cash"
    credit_note_reason: str = ""
    customer_pin: str = ""  # a KRA PIN, only when the payer is a business (no patient names)


_DECIMAL = re.compile(r'"__decimal__(-?[0-9]+(?:[.][0-9]+)?)__"')


def dumps(value: Any) -> bytes:
    """JSON with Decimals written as exact numbers (eTIMS NUMBER fields; never floats)."""

    def mark(item: Any) -> Any:
        if isinstance(item, Decimal):
            return f"__decimal__{item}__"
        if isinstance(item, dict):
            return {k: mark(v) for k, v in item.items()}
        if isinstance(item, list):
            return [mark(v) for v in item]
        return item

    return _DECIMAL.sub(lambda m: m.group(1), json.dumps(mark(value))).encode()


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def tax_in(amount: Decimal, tax_type: str) -> Decimal:
    """VAT contained in a VAT-inclusive amount (the spec's sample: 200000 at 18 % → 30508)."""
    rate = TAX_RATES[tax_type]
    return _money(amount * rate / (Decimal(100) + rate)) if rate else Decimal("0.00")


def _number(value: Decimal) -> Any:
    """eTIMS NUMBER fields: Decimal stays exact through ``dumps``."""
    return _money(value)


def build_save_sales(doc: TaxDocument, *, tin: str, branch_id: str, user: str) -> dict[str, Any]:
    if not doc.lines:
        raise ValueError("An eTIMS document needs at least one line.")
    taxable = {code: Decimal("0") for code in TAX_RATES}
    taxes = {code: Decimal("0") for code in TAX_RATES}
    items = []
    for seq, line in enumerate(doc.lines, start=1):
        if line.tax_type not in TAX_RATES:
            raise ValueError(f"Unknown eTIMS tax type {line.tax_type!r}.")
        supply = _money(line.quantity * line.unit_price)
        total = _money(supply - line.discount)
        tax = tax_in(total, line.tax_type)
        taxable[line.tax_type] += total
        taxes[line.tax_type] += tax
        rate = _money(line.discount / supply * 100) if supply else Decimal("0.00")
        items.append(
            {
                "itemSeq": seq,
                "itemCd": line.item_code,
                "itemClsCd": line.item_class_code or None,
                "itemNm": line.name[:200],
                "bcd": None,
                "pkgUnitCd": line.package_unit,
                "pkg": _number(line.quantity),
                "qtyUnitCd": line.quantity_unit,
                "qty": _number(line.quantity),
                "prc": _number(line.unit_price),
                "splyAmt": _number(supply),
                "dcRt": _number(rate),
                "dcAmt": _number(line.discount),
                "isrccCd": None,
                "isrccNm": None,
                "isrcRt": None,
                "isrcAmt": None,
                "taxTyCd": line.tax_type,
                "taxblAmt": _number(total),
                "taxAmt": _number(tax),
                "totAmt": _number(total),
            }
        )
    stamp = doc.confirmed_at.strftime("%Y%m%d%H%M%S")
    body: dict[str, Any] = {
        "tin": tin,
        "bhfId": branch_id,
        "trdInvcNo": doc.trader_invoice_no[:50],
        "invcNo": doc.invoice_no,
        "orgInvcNo": doc.original_invoice_no,
        "custTin": doc.customer_pin or None,
        "custNm": None,  # never a patient's name
        "salesTyCd": NORMAL,
        "rcptTyCd": doc.receipt_type,
        "pmtTyCd": PAYMENT_TYPES.get(doc.payment_type, "07"),
        "salesSttsCd": APPROVED,
        "cfmDt": stamp,
        "salesDt": stamp[:8],
        "stockRlsDt": stamp,
        "cnclReqDt": None,
        "cnclDt": None,
        "rfdDt": stamp if doc.receipt_type == CREDIT_NOTE else None,
        "rfdRsnCd": CREDIT_NOTE_REASONS.get(doc.credit_note_reason, "13")
        if doc.receipt_type == CREDIT_NOTE
        else None,
        "totItemCnt": len(items),
        "totTaxblAmt": _number(sum(taxable.values(), Decimal("0"))),
        "totTaxAmt": _number(sum(taxes.values(), Decimal("0"))),
        "totAmt": _number(sum(taxable.values(), Decimal("0"))),
        "prchrAcptcYn": "N",
        "remark": None,
        "regrId": user[:20],
        "regrNm": user[:60],
        "modrId": user[:20],
        "modrNm": user[:60],
        "receipt": {
            "custTin": doc.customer_pin or None,
            "custMblNo": None,
            "rptNo": 1,
            "trdeNm": "",
            "adrs": "",
            "topMsg": "",
            "btmMsg": "",
            "prchrAcptcYn": "N",
        },
        "itemList": items,
    }
    for code in TAX_RATES:
        body[f"taxblAmt{code}"] = _number(taxable[code])
        body[f"taxRt{code}"] = _number(TAX_RATES[code])
        body[f"taxAmt{code}"] = _number(taxes[code])
    return body


@dataclass(frozen=True)
class SaveResult:
    code: str
    message: str
    receipt_no: int | None = None
    total_receipt_no: int | None = None
    internal_data: str = ""
    receipt_signature: str = ""
    sdc_id: str = ""
    mrc_no: str = ""
    signed_at: str = ""


class VscuUnavailable(Exception):
    """The VSCU did not answer (the document stays queued and is retried)."""


class VscuClient:
    def __init__(self, base_url: str, *, mode: str, transport: httpx.BaseTransport | None = None):
        self.mode = mode
        self.http = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=TIMEOUT, transport=transport
        )

    def save_sales(self, content: bytes, *, facility_id: int | None = None) -> SaveResult:
        """POST the exact JSON produced by ``dumps(build_save_sales(...))``."""
        with exchange(
            "etims.vscu",
            "save_sales",
            mode=self.mode,
            facility_id=facility_id,
            request=_logged(content),
        ) as call:
            try:
                response = self.http.post(
                    SAVE_SALES, content=content, headers={"Content-Type": "application/json"}
                )
            except httpx.HTTPError as exc:
                call.outcome = ExchangeLog.Outcome.UNAVAILABLE
                raise VscuUnavailable("The eTIMS VSCU did not answer.") from exc
            call.http_status = response.status_code
            if response.status_code >= 500:
                call.outcome = ExchangeLog.Outcome.UNAVAILABLE
                raise VscuUnavailable("The eTIMS VSCU failed to answer.")
            try:
                answer = response.json()
            except ValueError as exc:
                call.outcome = ExchangeLog.Outcome.ERROR
                raise VscuUnavailable("The eTIMS VSCU answer could not be read.") from exc
            call.response = answer
            code = str(answer.get("resultCd") or "")
            call.outcome = (
                ExchangeLog.Outcome.SUCCESS if code == SUCCESS else ExchangeLog.Outcome.ERROR
            )
            data = answer.get("data") or {}
            return SaveResult(
                code=code,
                message=str(answer.get("resultMsg") or "")[:200],
                receipt_no=_int(data.get("rcptNo")),
                total_receipt_no=_int(data.get("totRcptNo")),
                internal_data=str(data.get("intrlData") or ""),
                receipt_signature=str(data.get("rcptSign") or ""),
                sdc_id=str(data.get("sdcId") or ""),
                mrc_no=str(data.get("mrcNo") or ""),
                signed_at=str(data.get("VSCURcptPbctDate") or ""),
            )


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _logged(content: bytes) -> dict[str, Any]:
    copy: dict[str, Any] = json.loads(content)
    copy["custTin"] = "[redacted]" if copy.get("custTin") else None
    return copy
