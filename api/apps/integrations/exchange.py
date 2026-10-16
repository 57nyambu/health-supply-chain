"""Recording calls to external systems in ``ExchangeLog`` (api/CLAUDE.md "External adapters").

Adapters wrap each call::

    with exchange("hie.client_registry", "find", mode="fake", request={...}) as call:
        call.response = {...}
        call.outcome = ExchangeLog.Outcome.SUCCESS

The row is written whatever happens (an exception marks it ``error`` unless the adapter set
another outcome). Bodies are encrypted; header values whose names suggest credentials are
replaced before storage. Logs carry only the correlation ID.
"""

import json
import logging
import time
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from django.utils import timezone

from apps.integrations.models import ExchangeLog

logger = logging.getLogger(__name__)
REDACTED = "[redacted]"
SECRET_HEADER_PARTS = ("authorization", "cookie", "token", "secret", "key", "password", "otp")


def redact_headers(headers: Mapping[str, str] | None) -> dict[str, str]:
    return {
        name: REDACTED if any(part in name.lower() for part in SECRET_HEADER_PARTS) else value
        for name, value in (headers or {}).items()
    }


@dataclass
class Exchange:
    correlation_id: str
    outcome: str = ""
    response: Any = None
    http_status: int | None = None
    provider_trace_id: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


def _body(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes | str):
        return value.decode("utf-8", "replace") if isinstance(value, bytes) else value
    return json.dumps(value, default=str, ensure_ascii=False, sort_keys=True)


@contextmanager
def exchange(
    integration: str,
    operation: str,
    *,
    mode: str,
    facility_id: int | None = None,
    request: Any = None,
    headers: Mapping[str, str] | None = None,
) -> Iterator[Exchange]:
    call = Exchange(correlation_id=uuid.uuid4().hex)
    started_at = timezone.now()
    start = time.monotonic()
    try:
        yield call
    except Exception:
        call.outcome = call.outcome or ExchangeLog.Outcome.ERROR
        raise
    finally:
        ExchangeLog.objects.create(
            facility_id=facility_id,
            integration=integration,
            operation=operation,
            mode=mode,
            correlation_id=call.correlation_id,
            started_at=started_at,
            duration_ms=int((time.monotonic() - start) * 1000),
            outcome=call.outcome or ExchangeLog.Outcome.SUCCESS,
            http_status=call.http_status,
            provider_trace_id=call.provider_trace_id,
            request_headers=redact_headers(headers),
            request_body=_body(request),
            response_body=_body(call.response),
        )
        logger.info(
            "External exchange",
            extra={
                "integration": integration,
                "operation": operation,
                "correlation_id": call.correlation_id,
                "outcome": call.outcome or ExchangeLog.Outcome.SUCCESS,
            },
        )
