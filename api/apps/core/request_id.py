"""Request IDs: one per request, echoed in X-Request-ID, available to logs and error bodies."""

import re
import uuid
from contextvars import ContextVar

REQUEST_ID_HEADER = "X-Request-ID"
_SAFE_INCOMING_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")

_current_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return _current_request_id.get()


class RequestIdMiddleware:
    """Accept a well-formed X-Request-ID from nginx, otherwise generate one."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if _SAFE_INCOMING_ID.match(incoming) else uuid.uuid4().hex
        request.request_id = request_id
        token = _current_request_id.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            _current_request_id.reset(token)
        response[REQUEST_ID_HEADER] = request_id
        return response
