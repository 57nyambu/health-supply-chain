"""Default-deny enforcement for every API view (DESIGN §7.3, P1-UAC-03).

``PolicyPermission`` is ``DEFAULT_PERMISSION_CLASSES``. A view states what it needs:

    policy = "inventory.store.read"                        # every method
    policy = {"GET": "operations.stats.read", "POST": "operations.stats.submit"}
    policy = {"list": "admin.user.read", "create": "admin.user.create"}  # viewset actions
    policy = PUBLIC          # explicit allowlist only: login, health, verified webhooks
    policy = AUTHENTICATED   # any signed-in user, for their own data (e.g. /me)

No ``policy`` (or no entry for the method/action) denies the request. Codes are
checked in the request's facility; object-level checks use the object's facility.
"""

import logging
from typing import TYPE_CHECKING, Any

from django.db.models import Model
from rest_framework.exceptions import APIException
from rest_framework.permissions import BasePermission

from apps.access import policies
from apps.access.catalogue import is_known
from apps.audit import context as audit_context

if TYPE_CHECKING:  # rest_framework.views imports this module through DEFAULT_PERMISSION_CLASSES
    from rest_framework.request import Request
    from rest_framework.views import APIView

logger = logging.getLogger(__name__)

PUBLIC = "public"
AUTHENTICATED = "authenticated"
SENTINELS = {PUBLIC, AUTHENTICATED}
SESSION_FACILITY_KEY = "active_facility_id"


def declared_policy(view_class: type, action: str | None, method: str) -> Any:
    """The policy a view class declares for one action/method, or None (deny)."""
    policy = getattr(view_class, "policy", None)
    if isinstance(policy, dict):
        if action is not None and action in policy:
            return policy[action]
        return policy.get(method.upper())
    return policy


def policy_for(view: "APIView", request: "Request") -> Any:
    policy = declared_policy(type(view), getattr(view, "action", None), request.method or "")
    if callable(policy):
        return policy(view, request)
    return policy


def request_facility(request: Any) -> int | None:
    """The facility the user acts in: the session's chosen one, else their only facility."""
    django_request = getattr(request, "_request", request)
    if hasattr(django_request, "_access_facility"):
        return django_request._access_facility  # type: ignore[no-any-return]
    user = getattr(request, "user", None)
    facility_id: int | None = None
    if user is not None and getattr(user, "is_authenticated", False):
        allowed = policies.facilities_for(user)
        session = getattr(django_request, "session", None)
        chosen = session.get(SESSION_FACILITY_KEY) if session is not None else None
        if chosen in allowed:
            facility_id = chosen
        elif len(allowed) == 1:
            facility_id = allowed[0]
    django_request._access_facility = facility_id
    if facility_id is not None:
        audit_context.update(facility_id=facility_id)
    return facility_id


def object_facility(view: "APIView", obj: Any) -> int | None:
    """Facility an object belongs to: ``view.facility_of(obj)``, else ``obj.facility_id``."""
    resolver = getattr(view, "facility_of", None)
    if callable(resolver):
        return resolver(obj)  # type: ignore[no-any-return]
    value = getattr(obj, "facility_id", None)
    return int(value) if value is not None else None


class PasswordChangeRequired(APIException):
    status_code = 403
    default_detail = "Change your temporary password before continuing."
    default_code = "password_change_required"


class MfaEnrolmentRequired(APIException):
    status_code = 403
    default_detail = "Set up two-step sign-in (an authenticator app) before continuing."
    default_code = "mfa_enrolment_required"


class MfaVerificationRequired(APIException):
    status_code = 403
    default_detail = "Enter the code from your authenticator app to continue."
    default_code = "mfa_required"


def enforce_mfa(request: Any) -> None:
    from apps.accounts import mfa

    current = mfa.state(request)
    if current == "enrol":
        raise MfaEnrolmentRequired()
    if current == "verify":
        raise MfaVerificationRequired()


class PolicyPermission(BasePermission):
    message = "You do not have permission to perform this action."

    def has_permission(self, request: "Request", view: "APIView") -> bool:
        code = policy_for(view, request)
        if code is None:
            logger.warning(
                "Denied: %s declares no policy for %s", type(view).__name__, request.method
            )
            return False
        if code == PUBLIC:
            return True
        user = request.user
        if user is None or not user.is_authenticated:
            return False
        if getattr(user, "is_service_account", False):
            from apps.access.authentication import ServicePrincipal

            return (
                code != AUTHENTICATED
                and is_known(code)
                and isinstance(user, ServicePrincipal)
                and user.has_code(code)
            )
        if not getattr(view, "mfa_exempt", False):
            enforce_mfa(request)
        if code == AUTHENTICATED:
            return True
        if getattr(user, "must_change_password", False):
            raise PasswordChangeRequired()
        if not is_known(code):
            logger.error("Denied: %s references unknown permission %s", type(view).__name__, code)
            return False
        facility = request_facility(request)
        if facility is None:
            return False
        return policies.has_permission(user, code, facility=facility)

    def has_object_permission(self, request: "Request", view: "APIView", obj: Model) -> bool:
        code = policy_for(view, request)
        if code in SENTINELS:
            return True
        if getattr(request.user, "is_service_account", False):
            return True
        facility = object_facility(view, obj)
        if facility is None:
            return True
        return policies.has_permission(request.user, code, facility=facility)


class FacilityScopedMixin:
    """Helpers for views whose querysets must be limited to the request's facility."""

    request: "Request"

    def current_facility_id(self) -> int | None:
        return request_facility(self.request)
