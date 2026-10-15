"""RFC 9457 problem details for every API error (DESIGN §17).

Error bodies carry a stable machine-readable ``code`` and the ``request_id``
and never echo request input: built-in DRF messages that interpolate the
submitted value ("'Wanjiku' is not a valid choice") are replaced by fixed
text, and any other message that contains a submitted value is replaced too.
"""

import logging
from collections.abc import Iterator
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404, JsonResponse
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import set_rollback

from apps.core.request_id import get_request_id

logger = logging.getLogger(__name__)

PROBLEM_CONTENT_TYPE = "application/problem+json"
GENERIC_INVALID = "Invalid value."
MIN_ECHO_LENGTH = 3

# DRF/Django validation codes whose default message interpolates the input value.
INTERPOLATING_CODES = {
    "invalid_choice": "Not a valid choice.",
    "does_not_exist": "The referenced object does not exist.",
    "incorrect_type": "Incorrect type.",
    "invalid_pk_value": "Invalid identifier.",
    "invalid_list": "Expected a list of values.",
    "not_a_list": "Expected a list of items.",
    "not_a_dict": "Expected an object.",
    "unique": "A record with this value already exists.",
}


class ApiProblem(exceptions.APIException):
    """Base for project API errors; ``detail`` must never contain PHI."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    default_detail = "The request could not be processed."
    default_code = "bad_request"


class Conflict(ApiProblem):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The resource was changed by someone else; reload and try again."
    default_code = "conflict"


class PreconditionRequired(ApiProblem):
    status_code = status.HTTP_428_PRECONDITION_REQUIRED
    default_detail = "A required request header is missing."
    default_code = "precondition_required"


class Forbidden(ApiProblem):
    """403 with a project-written (PHI-free) explanation, e.g. "You cannot approve your own request"."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = "permission_denied"


class UnprocessableEntity(ApiProblem):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "The request cannot be processed."
    default_code = "unprocessable"


TITLES = {
    400: "Bad request",
    401: "Not authenticated",
    403: "Forbidden",
    404: "Not found",
    405: "Method not allowed",
    406: "Not acceptable",
    409: "Conflict",
    415: "Unsupported media type",
    422: "Unprocessable request",
    423: "Locked",
    428: "Precondition required",
    429: "Too many requests",
    500: "Internal server error",
    503: "Service unavailable",
}

# Messages for built-in exceptions whose default text is generic and safe.
SAFE_BUILTIN_DETAILS = {
    "not_authenticated": "Authentication credentials were not provided.",
    "authentication_failed": "Authentication failed.",
    "permission_denied": "You do not have permission to perform this action.",
    "not_found": "Not found.",
    "method_not_allowed": "Method not allowed.",
    "not_acceptable": "Could not satisfy the request Accept header.",
    "unsupported_media_type": "Unsupported media type in request.",
    "parse_error": "Malformed request body.",
    "throttled": "Request was throttled; try again later.",
}


def problem(status_code: int, code: str, detail: str, errors: list | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": f"urn:afyasync:problem:{code}",
        "title": TITLES.get(status_code, "Error"),
        "status": status_code,
        "detail": detail,
        "code": code,
        "request_id": get_request_id(),
    }
    if errors is not None:
        body["errors"] = errors
    return body


def problem_response(
    status_code: int, code: str, detail: str, errors=None, headers=None
) -> Response:
    return Response(
        problem(status_code, code, detail, errors),
        status=status_code,
        headers=headers,
        content_type=PROBLEM_CONTENT_TYPE,
    )


def _submitted_strings(request) -> set[str]:
    """Every string the client sent (body and query), lower-cased, long enough to matter."""
    found: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, str):
            if len(value.strip()) >= MIN_ECHO_LENGTH:
                found.add(value.strip().lower())
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list | tuple):
            for item in value:
                walk(item)
        elif hasattr(value, "lists"):  # QueryDict
            for _key, items in value.lists():
                walk(items)

    if request is not None:
        try:
            walk(getattr(request, "data", None))
        except Exception:
            logger.debug("request body not parseable while building a problem response")
        walk(getattr(request, "query_params", None) or getattr(request, "GET", None))
    return found


def _safe_message(message: str, code: str, submitted: set[str]) -> str:
    if code in INTERPOLATING_CODES:
        return INTERPOLATING_CODES[code]
    lowered = message.lower()
    if any(value in lowered for value in submitted):
        return GENERIC_INVALID
    return message


def _flatten(detail: Any, path: str = "") -> Iterator[tuple[str | None, exceptions.ErrorDetail]]:
    if isinstance(detail, dict):
        for key, value in detail.items():
            name = str(key)
            child = name if not path else f"{path}.{name}"
            if name in ("non_field_errors", "__all__"):
                child = path
            yield from _flatten(value, child)
    elif isinstance(detail, list):
        for index, value in enumerate(detail):
            if isinstance(value, dict | list):
                yield from _flatten(value, f"{path}.{index}" if path else str(index))
            else:
                yield from _flatten(value, path)
    else:
        yield (path or None), detail


def validation_errors(detail: Any, request) -> list[dict[str, Any]]:
    submitted = _submitted_strings(request)
    errors = []
    for field, error in _flatten(detail):
        code = getattr(error, "code", None) or "invalid"
        errors.append(
            {"field": field, "code": code, "message": _safe_message(str(error), code, submitted)}
        )
    return errors


def exception_handler(exc, context):
    """DRF EXCEPTION_HANDLER: every error becomes application/problem+json."""
    request = context.get("request")

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        # Service-layer denials carry messages written by us, never PHI.
        exc = Forbidden(detail=str(exc)) if str(exc) else exceptions.PermissionDenied()
    elif isinstance(exc, DjangoValidationError):
        # Service-layer validation: same problem+json as serializer errors.
        exc = exceptions.ValidationError(
            detail=exc.message_dict if hasattr(exc, "error_dict") else exc.messages
        )

    if isinstance(exc, exceptions.ValidationError):
        set_rollback()
        return problem_response(
            status.HTTP_400_BAD_REQUEST,
            "validation_error",
            "One or more fields are invalid.",
            errors=validation_errors(exc.detail, request),
        )

    if isinstance(exc, exceptions.APIException):
        set_rollback()
        headers = {}
        if getattr(exc, "auth_header", None):
            headers["WWW-Authenticate"] = exc.auth_header
        if getattr(exc, "wait", None):
            headers["Retry-After"] = str(int(exc.wait))
        codes = exc.get_codes()
        code = codes if isinstance(codes, str) else exc.default_code
        if isinstance(exc, ApiProblem):
            detail = str(exc.detail)
        else:
            detail = SAFE_BUILTIN_DETAILS.get(code) or _safe_message(
                str(exc.detail), code, _submitted_strings(request)
            )
        return problem_response(exc.status_code, code, detail, headers=headers or None)

    # Unexpected error: log it (no request data) and answer with a generic 500.
    set_rollback()
    logger.exception("Unhandled API error", extra={"request_id": get_request_id()})
    return problem_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "server_error",
        "An unexpected error occurred. Quote the request ID when reporting it.",
    )


def _json_problem(status_code: int, code: str, detail: str) -> JsonResponse:
    return JsonResponse(
        problem(status_code, code, detail), status=status_code, content_type=PROBLEM_CONTENT_TYPE
    )


def _is_api(request) -> bool:
    return request.path.startswith("/api/")


def handler404(request, exception=None):
    if _is_api(request):
        return _json_problem(404, "not_found", "Not found.")
    from django.views.defaults import page_not_found

    return page_not_found(request, exception)


def handler500(request):
    if _is_api(request):
        return _json_problem(
            500,
            "server_error",
            "An unexpected error occurred. Quote the request ID when reporting it.",
        )
    from django.views.defaults import server_error

    return server_error(request)


def csrf_failure(request, reason=""):
    """CSRF_FAILURE_VIEW: problem+json for the API (the reason never contains PHI)."""
    if _is_api(request):
        return _json_problem(
            403, "csrf_failed", "CSRF verification failed. Reload the page and try again."
        )
    from django.views.csrf import csrf_failure as default_csrf_failure

    return default_csrf_failure(request, reason=reason)
