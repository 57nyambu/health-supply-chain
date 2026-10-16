"""Browser authentication over a same-origin session (ADR-005, P1-UAC-04).

1. GET /api/v1/auth/csrf sets the CSRF cookie.
2. POST /api/v1/auth/login with X-CSRFToken starts a Django session (httpOnly cookie).
3. Every unsafe request sends X-CSRFToken; no bearer tokens exist for browsers.
"""

from typing import Any, cast

from django.contrib.auth import logout, update_session_auth_hash
from django.middleware.csrf import get_token
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.access.drf import AUTHENTICATED, PUBLIC
from apps.accounts import login as auth
from apps.accounts import mfa
from apps.accounts.me import choose_facility, me_payload
from apps.accounts.models import User
from apps.audit.services import record
from apps.core.problems import problem_response

MFA_PENDING_USER = "mfa_pending_user"
MFA_PENDING_AT = "mfa_pending_at"
MFA_FAILURES = "mfa_failures"
MFA_PENDING_SECONDS = 300
MFA_MAX_FAILURES = 5


def enforce_csrf(request: Request) -> None:
    """Login has no session yet, so DRF would skip CSRF; check it explicitly (login CSRF)."""

    def get_response(_request: Any) -> None:
        return None

    check = CSRFCheck(cast(Any, get_response))
    check.process_request(request._request)
    reason = check.process_view(request._request, cast(Any, None), (), {})
    if reason:
        raise PermissionDenied("CSRF verification failed. Reload the page and try again.")


class LoginSerializer(serializers.Serializer[None]):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class PasswordChangeSerializer(serializers.Serializer[None]):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)


class FacilityChoiceSerializer(serializers.Serializer[None]):
    facility = serializers.IntegerField()


class CsrfView(APIView):
    policy = PUBLIC
    authentication_classes: list[Any] = []

    def get(self, request: Request) -> Response:
        return Response({"csrf_token": get_token(request._request)})


class LoginView(APIView):
    policy = PUBLIC
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"
    serializer_class = LoginSerializer

    def post(self, request: Request) -> Response:
        enforce_csrf(request)
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = auth.attempt_login(
            request._request,
            serializer.validated_data["email"],
            serializer.validated_data["password"],
        )
        if result.outcome == "throttled":
            return problem_response(
                429,
                "login_throttled",
                f"Too many failed attempts. Wait {result.retry_after} seconds and try again.",
                headers={"Retry-After": str(result.retry_after)},
            )
        if result.outcome == "locked":
            return problem_response(
                423,
                "account_locked",
                "This account is locked. Ask your facility administrator to unlock it.",
            )
        if result.outcome != "ok":
            return problem_response(
                401, "invalid_credentials", "The e-mail address or password is not correct."
            )
        user = cast(User, result.user)
        session = request._request.session
        if mfa.active_device(user) is not None:
            # Second factor first: no session until the code is verified.
            session.cycle_key()
            session[MFA_PENDING_USER] = user.pk
            session[MFA_PENDING_AT] = timezone.now().timestamp()
            session[MFA_FAILURES] = 0
            record("auth.login.mfa_challenged", user, user)
            return Response({"status": "mfa_required"})
        auth.complete_login(request._request, user, mfa_verified=False)
        request.user = cast(Any, user)  # DRF cached the anonymous user before login()
        choose_facility(request._request, None)
        return Response(me_payload(request))


class MfaCodeSerializer(serializers.Serializer[None]):
    code = serializers.CharField(required=False, allow_blank=True, max_length=6)
    recovery_code = serializers.CharField(required=False, allow_blank=True, max_length=20)


class MfaVerifyView(APIView):
    """Second step of sign-in, or re-verification of a signed-in session."""

    policy = PUBLIC
    mfa_exempt = True
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"
    serializer_class = MfaCodeSerializer

    def post(self, request: Request) -> Response:
        enforce_csrf(request)
        serializer = MfaCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = request._request.session
        pending = not request.user.is_authenticated
        if pending:
            started = session.get(MFA_PENDING_AT, 0)
            user = User.objects.filter(
                pk=session.get(MFA_PENDING_USER) or 0, is_active=True
            ).first()
            if user is None or timezone.now().timestamp() - started > MFA_PENDING_SECONDS:
                for key in (MFA_PENDING_USER, MFA_PENDING_AT, MFA_FAILURES):
                    session.pop(key, None)
                return problem_response(401, "mfa_session_expired", "Sign in again.")
        else:
            user = cast(User, request.user)
        method = mfa.verify(
            user,
            code=serializer.validated_data.get("code", ""),
            recovery_code=serializer.validated_data.get("recovery_code", ""),
        )
        if method is None:
            failures = session.get(MFA_FAILURES, 0) + 1
            session[MFA_FAILURES] = failures
            if pending and failures >= MFA_MAX_FAILURES:
                for key in (MFA_PENDING_USER, MFA_PENDING_AT, MFA_FAILURES):
                    session.pop(key, None)
                return problem_response(
                    401, "mfa_session_expired", "Too many wrong codes. Sign in again."
                )
            return problem_response(401, "invalid_code", "The code is not correct.")
        for key in (MFA_PENDING_USER, MFA_PENDING_AT, MFA_FAILURES):
            session.pop(key, None)
        if pending:
            auth.complete_login(request._request, user, mfa_verified=True)
            request.user = cast(Any, user)
            choose_facility(request._request, None)
        else:
            session[mfa.SESSION_VERIFIED] = True
        return Response(me_payload(request))


class TotpSetupView(APIView):
    """Start enrolling an authenticator app; returns the otpauth URI once."""

    policy = AUTHENTICATED
    mfa_exempt = True

    def post(self, request: Request) -> Response:
        user = cast(User, request.user)
        if mfa.active_device(user) is not None and mfa.state(request) != "ok":
            raise PermissionDenied("Verify your current authenticator before replacing it.")
        device, uri = mfa.begin_totp_setup(user)
        return Response({"otpauth_uri": uri, "secret": device.secret})


class TotpConfirmView(APIView):
    policy = AUTHENTICATED
    mfa_exempt = True
    serializer_class = MfaCodeSerializer

    def post(self, request: Request) -> Response:
        serializer = MfaCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        codes = mfa.confirm_totp_setup(
            cast(User, request.user), serializer.validated_data.get("code", "")
        )
        if codes is None:
            return problem_response(
                400, "invalid_code", "The code is not correct; check the time on your phone."
            )
        request._request.session[mfa.SESSION_VERIFIED] = True
        return Response({"recovery_codes": codes})


class RecoveryCodesView(APIView):
    """Replace recovery codes (old unused codes stop working)."""

    policy = AUTHENTICATED

    def post(self, request: Request) -> Response:
        return Response({"recovery_codes": mfa.issue_recovery_codes(cast(User, request.user))})


class LogoutView(APIView):
    policy = PUBLIC
    mfa_exempt = True

    def post(self, request: Request) -> Response:
        if request.user.is_authenticated:
            record("auth.logout", request.user, request.user)
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    policy = AUTHENTICATED
    mfa_exempt = True

    def get(self, request: Request) -> Response:
        return Response(me_payload(request))


class MeFacilityView(APIView):
    """Switch the active facility (workspace) for this session."""

    policy = AUTHENTICATED
    serializer_class = FacilityChoiceSerializer

    def post(self, request: Request) -> Response:
        serializer = FacilityChoiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        facility = choose_facility(request._request, serializer.validated_data["facility"])
        if facility is None:
            raise PermissionDenied("You hold no role in that facility.")
        record("auth.facility.switched", request.user, facility, facility=facility)
        return Response(me_payload(request))


class PasswordChangeView(APIView):
    policy = AUTHENTICATED
    mfa_exempt = True
    serializer_class = PasswordChangeSerializer

    def post(self, request: Request) -> Response:
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = cast(User, request.user)
        auth.change_password(
            user,
            current=serializer.validated_data["current_password"],
            new=serializer.validated_data["new_password"],
        )
        # Keep this session; other sessions of the user stop validating with the new hash.
        update_session_auth_hash(request._request, user)
        return Response(status=status.HTTP_204_NO_CONTENT)
