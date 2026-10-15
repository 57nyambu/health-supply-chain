"""API-key authentication for service accounts (non-PHI integrations only, DESIGN §17).

Keys look like ``<prefix>.<secret>``; only an HMAC of the key is stored. The
principal has the permissions of the client's service-account role and nothing
else — it is never a staff user and holds no facility assignment.
"""

import hashlib
import hmac
import secrets
from typing import Any

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from apps.access.models import ApiClient, Role
from apps.audit.context import client_ip

HEADER = "X-API-Key"


def hash_key(key: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), key.encode(), hashlib.sha256).hexdigest()


def issue_key(
    *, name: str, role: Role, allowed_ips: list[str] | None = None
) -> tuple[ApiClient, str]:
    """Create a client and return its key; the key is shown once and never stored."""
    if not role.service_account:
        raise ValueError("API clients need a service-account role.")
    prefix = secrets.token_hex(4)
    key = f"{prefix}.{secrets.token_urlsafe(32)}"
    client = ApiClient.objects.create(
        name=name,
        key_prefix=prefix,
        key_hash=hash_key(key),
        role=role,
        allowed_ips=allowed_ips or [],
    )
    return client, key


class ServicePrincipal:
    """``request.user`` for API-key requests."""

    is_authenticated = True
    is_active = True
    is_anonymous = False
    is_service_account = True
    is_staff = False
    is_superuser = False
    pk = None

    def __init__(self, client: ApiClient) -> None:
        self.client = client
        self._codes = set(
            client.role.permissions.filter(active=True).values_list("code", flat=True)
        )

    def has_code(self, code: str) -> bool:
        return code in self._codes

    def __str__(self) -> str:
        return f"api-client:{self.client.name}"


class ApiKeyAuthentication(BaseAuthentication):
    def authenticate(self, request: Request) -> tuple[Any, Any] | None:
        key = request.headers.get(HEADER)
        if not key:
            return None
        prefix, _, _secret = key.partition(".")
        client = (
            ApiClient.objects.select_related("role").filter(key_prefix=prefix, active=True).first()
        )
        if client is None or not hmac.compare_digest(client.key_hash, hash_key(key)):
            raise AuthenticationFailed("Invalid API key.")
        if client.allowed_ips and client_ip(request._request) not in client.allowed_ips:
            raise AuthenticationFailed("This API key is not allowed from this address.")
        ApiClient.objects.filter(pk=client.pk).update(last_used_at=timezone.now())
        return ServicePrincipal(client), client

    def authenticate_header(self, request: Request) -> str:
        return HEADER
