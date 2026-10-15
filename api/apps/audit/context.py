"""Per-request audit context: who is acting, from where, on which workstation."""

from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, replace
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from apps.core.request_id import get_request_id


@dataclass(frozen=True)
class AuditContext:
    ip: str | None = None
    user_agent: str = ""
    workstation_id: str = ""
    facility_id: int | None = None


_context: ContextVar[AuditContext] = ContextVar("audit_context", default=AuditContext())  # noqa: B039 - frozen dataclass

# Set by the access app: returns the role codes an actor currently holds.
role_resolver: Callable[[Any], str] = lambda actor: ""  # noqa: E731


def current() -> AuditContext:
    return _context.get()


def update(**changes: Any) -> None:
    """Refine the context mid-request (e.g. once the workstation or facility is known)."""
    _context.set(replace(_context.get(), **changes))


def client_ip(request: HttpRequest) -> str | None:
    if settings.TRUST_PROXY_HEADERS:
        forwarded = request.META.get("HTTP_X_REAL_IP")
        if forwarded:
            return str(forwarded).strip()
    remote = request.META.get("REMOTE_ADDR")
    return str(remote) if remote else None


class AuditContextMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        token = _context.set(
            AuditContext(
                ip=client_ip(request),
                user_agent=request.headers.get("User-Agent", "")[:300],
            )
        )
        try:
            return self.get_response(request)
        finally:
            _context.reset(token)


def request_id() -> str:
    return get_request_id() or ""
