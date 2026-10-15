"""Liveness and readiness probes. Unauthenticated; they reveal component status only."""

import logging
import uuid
from collections.abc import Callable

import redis
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


def check_database() -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()


def check_redis() -> None:
    client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
    try:
        client.ping()
    finally:
        client.close()


def check_storage() -> None:
    """The local object store is writable (replaced by the storage backend probe in P1-STO-01)."""
    probe = settings.DATA_DIR / f".readyz-{uuid.uuid4().hex}"
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    probe.write_bytes(b"ok")
    probe.unlink()


CHECKS: dict[str, Callable[[], None]] = {
    "database": check_database,
    "redis": check_redis,
    "storage": check_storage,
}


@never_cache
@require_GET
def healthz(request):
    return JsonResponse({"status": "ok"})


@never_cache
@require_GET
def readyz(request):
    results = {}
    for name, check in CHECKS.items():
        try:
            check()
            results[name] = "ok"
        except Exception:
            logger.exception("Readiness check failed: %s", name)
            results[name] = "fail"
    ready = all(value == "ok" for value in results.values())
    return JsonResponse(
        {"status": "ok" if ready else "fail", "checks": results}, status=200 if ready else 503
    )
