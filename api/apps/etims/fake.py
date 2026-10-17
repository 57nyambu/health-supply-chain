"""An in-process fake VSCU (``httpx.MockTransport``) for ``ETIMS_MODE=fake`` — synthetic data.

``/trnsSales/saveSales`` answers like the spec's sample: ``resultCd`` ``000`` with a receipt
number, internal data, receipt signature, SDC and MRC identifiers. Scripted outcomes:
a trader invoice number containing ``OFFLINE`` cannot connect (the queue retries);
an invoice number already received → ``994`` (overlapped data); missing required fields →
``910`` (request parameter error).
"""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime

import httpx

REQUIRED = ("tin", "bhfId", "trdInvcNo", "invcNo", "rcptTyCd", "salesTyCd", "itemList", "totAmt")


class FakeVscu:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.received: dict[tuple[str, str, int], dict[str, object]] = {}
        self.receipts = 0

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def handle(self, request: httpx.Request) -> httpx.Response:
        if request.url.path != "/trnsSales/saveSales" or request.method != "POST":
            return httpx.Response(
                404, json={"resultCd": "912", "resultMsg": "There is a request Method error."}
            )
        body = json.loads(request.content or b"{}")
        if "OFFLINE" in str(body.get("trdInvcNo", "")):
            raise httpx.ConnectError("fake VSCU unreachable", request=request)
        if any(body.get(name) in (None, "", []) for name in REQUIRED):
            return httpx.Response(
                200,
                json={
                    "resultCd": "910",
                    "resultMsg": "Request parameter error",
                    "resultDt": _now(),
                    "data": None,
                },
            )
        key = (str(body["tin"]), str(body["bhfId"]), int(body["invcNo"]))
        with self._lock:
            if key in self.received:
                return httpx.Response(
                    200,
                    json={
                        "resultCd": "994",
                        "resultMsg": "There is an overlapped Data",
                        "resultDt": _now(),
                        "data": None,
                    },
                )
            self.received[key] = body
            self.receipts += 1
            number = self.receipts
        digest = hashlib.sha256(f"{key}:{number}".encode()).hexdigest().upper()
        return httpx.Response(
            200,
            json={
                "resultCd": "000",
                "resultMsg": "It is succeeded",
                "resultDt": _now(),
                "data": {
                    "rcptNo": number,
                    "intrlData": digest[:26],
                    "rcptSign": digest[26:42],
                    "totRcptNo": number,
                    "VSCURcptPbctDate": _now(),
                    "sdcId": "SYN-SDC-0001",
                    "mrcNo": "SYN-MRC-0001",
                },
            },
        )


def _now() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")


_shared: FakeVscu | None = None
_shared_lock = threading.Lock()


def shared() -> FakeVscu:
    global _shared
    with _shared_lock:
        _shared = _shared or FakeVscu()
        return _shared
