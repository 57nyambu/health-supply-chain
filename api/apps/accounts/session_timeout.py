"""Server-side idle and absolute session expiry (DESIGN §7.2).

Limits come from the session's facility (bounded per facility) and default to 30
minutes idle and 12 hours absolute. An expired session is ended and deleted on the
server; API callers get 401 ``session_expired``.
"""

from collections.abc import Callable

from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone

from apps.accounts.models import UserSession
from apps.accounts.sessions import end_sessions
from apps.accounts.workstation import is_locked, lock
from apps.audit.services import record
from apps.core.problems import PROBLEM_CONTENT_TYPE, problem

SESSION_LIMITS_KEY = "limits"
DEFAULT_LIMITS = {"idle_minutes": 30, "absolute_hours": 12, "lock_minutes": 5}
TOUCH_EVERY_SECONDS = 30
# While a workstation is locked only these API paths answer (lock screen).
LOCKED_ALLOWED = {
    "/api/v1/me",
    "/api/v1/auth/csrf",
    "/api/v1/auth/login",
    "/api/v1/auth/logout",
    "/api/v1/auth/mfa/verify",
    "/api/v1/auth/unlock",
    "/api/v1/auth/switch",
}


def expiry_reason(session: dict, now: float) -> str | None:
    limits = {**DEFAULT_LIMITS, **session.get(SESSION_LIMITS_KEY, {})}
    auth_at = session.get("auth_at")
    last = session.get("last_activity", auth_at)
    if auth_at is not None and now - auth_at > limits["absolute_hours"] * 3600:
        return UserSession.EndReason.ABSOLUTE
    if last is not None and now - last > limits["idle_minutes"] * 60:
        return UserSession.EndReason.IDLE
    return None


class SessionTimeoutMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            now = timezone.now().timestamp()
            session = request.session
            session.setdefault("auth_at", now)
            reason = expiry_reason(session, now)
            if reason is not None:
                end_sessions(user, reason=reason, session_key=session.session_key)
                record(f"auth.session.expired_{reason}", user, user)
                logout(request)
                if request.path.startswith("/api/"):
                    return JsonResponse(
                        problem(401, "session_expired", "Your session has ended. Sign in again."),
                        status=401,
                        content_type=PROBLEM_CONTENT_TYPE,
                    )
            else:
                limits = {**DEFAULT_LIMITS, **session.get(SESSION_LIMITS_KEY, {})}
                idle = now - session.get("last_activity", now)
                if not is_locked(request) and idle > limits["lock_minutes"] * 60:
                    lock(request, reason="idle")
                if is_locked(request):
                    if request.path.startswith("/api/") and request.path not in LOCKED_ALLOWED:
                        return JsonResponse(
                            problem(
                                423,
                                "workstation_locked",
                                "This workstation is locked. Unlock with your PIN.",
                            ),
                            status=423,
                            content_type=PROBLEM_CONTENT_TYPE,
                        )
                elif now - session.get("last_activity", 0) > TOUCH_EVERY_SECONDS:
                    session["last_activity"] = now
        return self.get_response(request)
