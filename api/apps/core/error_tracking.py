"""Optional error tracker (Sentry-compatible), off unless a DSN is set and residency allows it.

Events carry no request bodies, cookies, headers, query strings or local
variables, and every remaining string passes through the PHI scrubber.
"""

import logging
from typing import Any

from django.conf import settings

from apps.core import residency
from apps.core.scrubbing import scrub_text, scrub_value

logger = logging.getLogger(__name__)

_DROPPED_REQUEST_KEYS = ("data", "cookies", "headers", "query_string", "env")


def scrub_event(event: dict[str, Any], hint: dict[str, Any] | None = None) -> dict[str, Any]:
    request = event.get("request")
    if isinstance(request, dict):
        for key in _DROPPED_REQUEST_KEYS:
            request.pop(key, None)
        if "url" in request:
            request["url"] = scrub_text(str(request["url"]))
    user = event.get("user")
    if isinstance(user, dict):
        event["user"] = {"id": user["id"]} if "id" in user else {}
    for exception in (event.get("exception") or {}).get("values", []) or []:
        if exception.get("value"):
            exception["value"] = scrub_text(str(exception["value"]))
        for frame in (exception.get("stacktrace") or {}).get("frames", []) or []:
            frame.pop("vars", None)
    if event.get("message"):
        event["message"] = scrub_text(str(event["message"]))
    logentry = event.get("logentry")
    if isinstance(logentry, dict):
        logentry["message"] = scrub_text(str(logentry.get("message", "")))
        logentry.pop("params", None)
    breadcrumbs = event.get("breadcrumbs")
    if isinstance(breadcrumbs, dict):
        for crumb in breadcrumbs.get("values", []) or []:
            if crumb.get("message"):
                crumb["message"] = scrub_text(str(crumb["message"]))
            crumb.pop("data", None)
    if "extra" in event:
        event["extra"] = scrub_value(event["extra"])
    return event


def init_error_tracking() -> bool:
    """Initialise the SDK when allowed. Returns True when enabled."""
    dsn = settings.ERROR_TRACKER_DSN
    if not dsn:
        return False
    if not residency.check_endpoint(dsn, "Error tracker"):
        return False

    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.DJANGO_ENV,
        send_default_pii=False,
        max_request_body_size="never",
        include_local_variables=False,
        traces_sample_rate=0.0,
        before_send=scrub_event,
        before_breadcrumb=lambda crumb, hint: {**crumb, "data": None},
    )
    logger.info("Error tracking enabled.")
    return True
