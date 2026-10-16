"""Idempotency-Key handling for unsafe API requests (DESIGN §17, ADR-012).

A client that sends ``Idempotency-Key`` gets exactly one execution per key:
the first response (2xx/4xx) is stored for 24 hours and replayed for the same
request; the same key with a different request is rejected with 422; a key
whose first request is still running gets 409. 5xx responses are not stored,
so the client may retry. Views that call external systems or move money set
``idempotency_required = True`` (or a set of viewset action names) and get 428
without the header.
"""

import hashlib
from datetime import timedelta
from typing import cast

from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

from apps.core.models import IdempotencyRecord
from apps.core.problems import PROBLEM_CONTENT_TYPE, problem

HEADER = "Idempotency-Key"
REPLAY_HEADER = "Idempotent-Replayed"
TTL = timedelta(hours=24)
MAX_KEY_LENGTH = 255
MAX_STORED_BODY = 1024 * 1024
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _problem(status_code: int, code: str, detail: str) -> JsonResponse:
    return JsonResponse(
        problem(status_code, code, detail), status=status_code, content_type=PROBLEM_CONTENT_TYPE
    )


def _principal(request) -> str:
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return f"user:{user.pk}"
    credential = request.headers.get("Authorization") or request.headers.get("X-API-Key")
    if credential:
        return "cred:" + hashlib.sha256(credential.encode()).hexdigest()[:40]
    return "anon"


def _request_hash(request) -> str:
    digest = hashlib.sha256()
    digest.update(request.method.encode())
    digest.update(b"\n")
    digest.update(request.get_full_path().encode())
    digest.update(b"\n")
    digest.update(request.body)
    return digest.hexdigest()


def _is_required(view_func, method: str) -> bool:
    view_class = getattr(view_func, "cls", None)
    required = getattr(view_class, "idempotency_required", False)
    if isinstance(required, set | frozenset | list | tuple):
        actions = getattr(view_func, "actions", None) or {}
        return actions.get(method.lower()) in required
    return bool(required)


def _replay(record: IdempotencyRecord) -> HttpResponse:
    response = HttpResponse(
        cast(bytes, record.response_body),
        status=record.status_code,
        content_type=record.content_type or None,
    )
    response[REPLAY_HEADER] = "true"
    return response


class IdempotencyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
        except BaseException:
            record = getattr(request, "_idempotency_record", None)
            if record is not None:
                IdempotencyRecord.objects.filter(pk=record.pk).delete()
            raise
        record = getattr(request, "_idempotency_record", None)
        if record is not None:
            self._finish(record, response)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method not in UNSAFE_METHODS or not request.path.startswith("/api/"):
            return None
        key = request.headers.get(HEADER)
        if key is None:
            if _is_required(view_func, request.method):
                return _problem(
                    428, "idempotency_key_required", f"This request needs an {HEADER} header."
                )
            return None
        if not key or len(key) > MAX_KEY_LENGTH or not key.isprintable():
            return _problem(
                400,
                "idempotency_key_invalid",
                f"{HEADER} must be 1-{MAX_KEY_LENGTH} printable characters.",
            )

        principal = _principal(request)
        request_hash = _request_hash(request)
        now = timezone.now()
        try:
            with transaction.atomic():
                record = IdempotencyRecord.objects.create(
                    principal=principal,
                    key=key,
                    method=request.method,
                    path=request.path[:500],
                    request_hash=request_hash,
                    expires_at=now + TTL,
                )
        except IntegrityError:
            with transaction.atomic():
                existing = IdempotencyRecord.objects.select_for_update().get(
                    principal=principal, key=key
                )
                if existing.expires_at <= now:
                    existing.delete()
                    record = IdempotencyRecord.objects.create(
                        principal=principal,
                        key=key,
                        method=request.method,
                        path=request.path[:500],
                        request_hash=request_hash,
                        expires_at=now + TTL,
                    )
                elif existing.request_hash != request_hash:
                    return _problem(
                        422,
                        "idempotency_key_reused",
                        f"This {HEADER} was already used for a different request.",
                    )
                elif existing.state == IdempotencyRecord.State.IN_PROGRESS:
                    return _problem(
                        409,
                        "idempotency_in_progress",
                        f"A request with this {HEADER} is still being processed; retry shortly.",
                    )
                else:
                    return _replay(existing)
        request._idempotency_record = record
        return None

    @staticmethod
    def _finish(record: IdempotencyRecord, response) -> None:
        storable = (
            response.status_code < 500
            and not getattr(response, "streaming", False)
            and len(response.content) <= MAX_STORED_BODY
        )
        if not storable:
            IdempotencyRecord.objects.filter(pk=record.pk).delete()
            return
        IdempotencyRecord.objects.filter(pk=record.pk).update(
            state=IdempotencyRecord.State.COMPLETED,
            status_code=response.status_code,
            content_type=response.get("Content-Type", ""),
            response_body=response.content,
        )


def purge_expired_records() -> int:
    deleted, _ = IdempotencyRecord.objects.filter(expires_at__lte=timezone.now()).delete()
    return deleted
