"""Transport to the national Health Information Exchange (INSURANCE.md §3.1; ADR-072).

One client serves every HIE adapter (Client Registry, Health Worker Registry, Facility
Registry, SHA eligibility, consent and eClaims). Field names follow the HIE's published
OpenAPI specs (DECISIONS.md, Phase 3 findings; ``docs/integrations/sha-hie/SPEC-NOTES.md``).

- Auth: ``POST /tenants/token`` (form ``client_id``, ``client_secret``) → bearer token. Tokens
  are cached per credential and refreshed at 80 % of their lifetime by one caller while the
  others wait (single flight). A 401 refreshes once and replays the request once.
- Facility scoping: a multi-facility credential sends ``X-Facility-Id`` and
  ``X-Facility-Id-Type`` on every call; a facility credential sends neither (the token
  carries the facility, and DHA discourages sending both).
- Reads are retried (with jitter) on connection errors, 429 and 5xx; writes never are. A
  write that times out or gets a 5xx raises ``HieOutcomeUnknown``: the caller queries first.
- Every call is written to ``integrations.ExchangeLog`` (encrypted body) with secrets and
  identifiers removed from the logged copies (INSURANCE.md §10).
"""

from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

import httpx
from django.conf import settings

from apps.integrations.exchange import exchange
from apps.integrations.models import ExchangeLog

from .errors import (
    HieAuthError,
    HieConfigurationError,
    HieError,
    HieForbidden,
    HieNotFound,
    HieOutcomeUnknown,
    HieRateLimited,
    HieRejected,
    HieUnavailable,
)

TIMEOUT = httpx.Timeout(30.0, connect=5.0)
READ_ATTEMPTS = 3
DEFAULT_TOKEN_SECONDS = 60  # when the HIE sends no usable ``expires_in``
UAT_BASE_URL = "https://ilm-dev.dha.go.ke/uat-middleware/api/v1"
FAKE_BASE_URL = "https://hie.fake.invalid/api/v1"
MODES = ("fake", "sandbox", "live")

# Keys whose values never reach a log row, even encrypted (INSURANCE.md §10).
REDACTED = "[redacted]"
SECRET_KEYS = frozenset(
    {
        "access_token",
        "client_secret",
        "otp",
        "token",
        "consent_token",
        "authorization_code",
        "auth_guid",
        "embededtoken",
        "ekyctoken",
        "identification_number",
        "idnumber",
        "member_number",
        "membernumber",
        "membercrnumber",
        "requestidnumber",
        "nhif_number",
        "sha_number",
        "shanumber",
        "nationalid",
        "phone",
        "contactvalue",
        "kra_pin",
        "requesturl",
    }
)


def redact(value: Any) -> Any:
    """A copy of ``value`` with secret and identifier fields replaced."""
    if isinstance(value, Mapping):
        return {
            k: REDACTED if str(k).lower().replace("-", "_") in SECRET_KEYS else redact(v)
            for k, v in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact(v) for v in value]
    return value


@dataclass(frozen=True)
class HieConfig:
    mode: str
    base_url: str
    client_id: str
    client_secret: str = field(repr=False)
    facility_code: str = ""
    facility_id_type: str = "fr-code"
    scope: str = "facility"  # facility | multi_facility

    @property
    def cache_key(self) -> tuple[str, str]:
        return (self.base_url, self.client_id)


def config_from_settings(
    mode: str | None = None, *, setting: str = "SHA_MODE", gap: str = "GAP-HIE-001"
) -> HieConfig:
    """The HIE configuration for ``mode`` (default: ``SHA_MODE``). Sandbox and live refuse to
    start without credentials and name what is missing. The registry adapters pass their own
    mode (``CLIENT_REGISTRY_MODE``, ``HWR_MODE``) and share the HIE credentials."""
    mode = mode or getattr(settings, "SHA_MODE", "fake")
    if mode not in MODES:
        raise HieConfigurationError(f"{setting}={mode!r} is not one of {', '.join(MODES)}.")
    if mode == "fake":
        return HieConfig(
            mode="fake",
            base_url=FAKE_BASE_URL,
            client_id="fake-hie-client",
            client_secret="fake-hie-secret",  # noqa: S106 - the in-process fake's credential
            facility_code=getattr(settings, "SHA_FACILITY_ID", "") or "FID-SYN-000001",
            facility_id_type=getattr(settings, "SHA_FACILITY_ID_TYPE", "fr-code"),
            scope=getattr(settings, "SHA_CREDENTIAL_SCOPE", "facility"),
        )
    names = (
        "SHA_BASE_URL",
        "SHA_CLIENT_ID",
        "SHA_CLIENT_SECRET",
        "SHA_FACILITY_ID",
        "SHA_FACILITY_ID_TYPE",
        "SHA_CREDENTIAL_SCOPE",
    )
    values = {name: str(getattr(settings, name, "") or "") for name in names}
    missing = [name for name in names[:4] if not values[name]]
    if missing:
        raise HieConfigurationError(
            f"{setting}={mode} needs {', '.join(missing)}: HIE UAT credentials and the "
            f"facility FR code come from the HIE integration team (owner action; {gap})."
        )
    return HieConfig(
        mode=mode,
        base_url=values["SHA_BASE_URL"].rstrip("/"),
        client_id=values["SHA_CLIENT_ID"],
        client_secret=values["SHA_CLIENT_SECRET"],
        facility_code=values["SHA_FACILITY_ID"],
        facility_id_type=values["SHA_FACILITY_ID_TYPE"] or "fr-code",
        scope=values["SHA_CREDENTIAL_SCOPE"] or "facility",
    )


# --- Token cache ---------------------------------------------------------------------------


@dataclass
class _Token:
    value: str = field(repr=False)
    refresh_at: float
    expires_at: float


class TokenCache:
    """Bearer tokens per credential, refreshed by a single caller (single flight)."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._tokens: dict[tuple[str, str], _Token] = {}
        self._locks: dict[tuple[str, str], threading.Lock] = {}
        self._guard = threading.Lock()
        self.fetches = 0  # observable for tests: how many token calls were made

    def _lock(self, key: tuple[str, str]) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(key, threading.Lock())

    def get(self, key: tuple[str, str], fetch: Callable[[], tuple[str, int]]) -> str:
        current = self._tokens.get(key)
        if current is not None and self._clock() < current.refresh_at:
            return current.value
        with self._lock(key):
            current = self._tokens.get(key)
            if current is not None and self._clock() < current.refresh_at:
                return current.value  # another caller refreshed while we waited
            value, lifetime = fetch()
            self.fetches += 1
            lifetime = lifetime if lifetime > 0 else DEFAULT_TOKEN_SECONDS
            now = self._clock()
            self._tokens[key] = _Token(value, now + 0.8 * lifetime, now + lifetime)
            return value

    def invalidate(self, key: tuple[str, str], value: str) -> None:
        """Forget ``value`` (it was refused). A token another caller already replaced stays."""
        with self._lock(key):
            current = self._tokens.get(key)
            if current is not None and current.value == value:
                del self._tokens[key]

    def clear(self) -> None:
        with self._guard:
            self._tokens.clear()


TOKENS = TokenCache()


# --- Client ----------------------------------------------------------------------------------


def _payer_text(response: httpx.Response) -> tuple[str, str]:
    try:
        body = response.json()
    except ValueError:
        return "", ""
    if isinstance(body, Mapping):
        return str(body.get("error") or "")[:100], str(body.get("message") or "")[:255]
    return "", ""


class HieClient:
    def __init__(
        self,
        config: HieConfig,
        *,
        transport: httpx.BaseTransport | None = None,
        tokens: TokenCache = TOKENS,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self.mode = config.mode
        self._tokens = tokens
        self._sleep = sleep
        if transport is None and config.mode == "fake":
            from .fake import shared

            transport = shared().transport()
        self._http = httpx.Client(base_url=config.base_url, timeout=TIMEOUT, transport=transport)

    # --- auth ---

    def _fetch_token(self) -> tuple[str, int]:
        form = {"client_id": self.config.client_id, "client_secret": self.config.client_secret}
        with exchange(
            "hie.auth",
            "token",
            mode=self.mode,
            request={"client_id": self.config.client_id, "client_secret": REDACTED},
        ) as call:
            try:
                response = self._http.post("/tenants/token", data=form)
            except httpx.HTTPError as exc:
                call.outcome = ExchangeLog.Outcome.UNAVAILABLE
                raise HieUnavailable("The HIE token service did not answer.") from exc
            call.http_status = response.status_code
            if response.status_code != 200:
                call.outcome = ExchangeLog.Outcome.ERROR
                error, message = _payer_text(response)
                call.response = {"error": error, "message": message}
                if response.status_code >= 500:
                    raise HieUnavailable(
                        "The HIE token service failed.", status=response.status_code
                    )
                raise HieAuthError(
                    "The HIE refused our credentials.",
                    status=response.status_code,
                    payer_message=message,
                )
            body = response.json()
            call.response = redact(body)
            token = str(body.get("access_token") or "")
            if not token:
                call.outcome = ExchangeLog.Outcome.ERROR
                raise HieAuthError("The HIE answered without an access token.")
            try:
                lifetime = int(body.get("expires_in") or 0)
            except (TypeError, ValueError):
                lifetime = 0
            return token, lifetime

    def _headers(self, token: str) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        if self.config.scope == "multi_facility":
            headers["X-Facility-Id"] = self.config.facility_code
            headers["X-Facility-Id-Type"] = self.config.facility_id_type
        return headers

    # --- requests ---

    def get(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        operation: str,
        integration: str = "hie",
        facility_id: int | None = None,
    ) -> Any:
        return self._call(
            "GET",
            path,
            params=params,
            operation=operation,
            integration=integration,
            facility_id=facility_id,
            write=False,
        )

    def post(
        self,
        path: str,
        *,
        json: Any = None,
        operation: str,
        integration: str = "hie",
        facility_id: int | None = None,
        write: bool = True,
        log_path: str | None = None,
    ) -> Any:
        """POSTs are writes unless the caller says otherwise: never retried. ``log_path``
        replaces a path that carries a secret (e.g. a consent token) in the exchange log."""
        return self._call(
            "POST",
            path,
            json=json,
            operation=operation,
            integration=integration,
            facility_id=facility_id,
            write=write,
            log_path=log_path,
        )

    def _call(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        operation: str,
        integration: str,
        facility_id: int | None,
        write: bool,
        log_path: str | None = None,
    ) -> Any:
        logged = {
            "method": method,
            "path": log_path or path,
            "params": redact(dict(params or {})),
        }
        if json is not None:
            logged["json"] = redact(json)
        with exchange(
            integration, operation, mode=self.mode, facility_id=facility_id, request=logged
        ) as call:
            attempts = 1 if write else READ_ATTEMPTS
            replayed = False
            attempt = 0
            while True:
                attempt += 1
                token = self._tokens.get(self.config.cache_key, self._fetch_token)
                try:
                    response = self._http.request(
                        method, path, params=params, json=json, headers=self._headers(token)
                    )
                except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout) as exc:
                    # Never left this process: safe to retry a read, and a write was not sent.
                    if attempt < attempts:
                        self._backoff(attempt)
                        continue
                    call.outcome = ExchangeLog.Outcome.UNAVAILABLE
                    raise HieUnavailable("The HIE did not answer.") from exc
                except httpx.HTTPError as exc:  # read/write timeouts, dropped connections
                    if write:
                        call.outcome = ExchangeLog.Outcome.TIMEOUT
                        raise HieOutcomeUnknown(
                            "The HIE did not confirm the change; check its status before trying again."
                        ) from exc
                    if attempt < attempts:
                        self._backoff(attempt)
                        continue
                    call.outcome = ExchangeLog.Outcome.TIMEOUT
                    raise HieUnavailable("The HIE did not answer in time.") from exc
                call.http_status = response.status_code
                status = response.status_code
                if status == 401 and not replayed:
                    replayed = True
                    self._tokens.invalidate(self.config.cache_key, token)
                    attempt -= 1  # the replay is not a retry
                    continue
                if status == 429 and not write and attempt < attempts:
                    self._backoff(attempt, response.headers.get("Retry-After"))
                    continue
                if status >= 500 and not write and attempt < attempts:
                    self._backoff(attempt)
                    continue
                return self._result(call, response, write=write)

    def _result(self, call: Any, response: httpx.Response, *, write: bool) -> Any:
        status = response.status_code
        error, message = _payer_text(response)
        if 200 <= status < 300:
            if not response.content:
                call.response = None
                return None
            try:
                body = response.json()
            except ValueError as exc:
                call.outcome = ExchangeLog.Outcome.ERROR
                if write:
                    raise HieOutcomeUnknown("The HIE's answer could not be read.") from exc
                raise HieUnavailable("The HIE's answer could not be read.") from exc
            call.response = redact(body)
            call.outcome = ExchangeLog.Outcome.SUCCESS
            return body
        call.response = {"error": error, "message": message}
        if status == 404:
            call.outcome = ExchangeLog.Outcome.NOT_FOUND
            raise HieNotFound("The HIE has no such record.", status=status, payer_message=message)
        call.outcome = ExchangeLog.Outcome.ERROR
        if status == 401:
            raise HieAuthError(
                "The HIE refused our credentials.", status=status, payer_message=message
            )
        if status == 403:
            raise HieForbidden(
                "The HIE does not allow this for our facility or credential.",
                status=status,
                payer_message=message,
            )
        if status == 429:
            retry_after = response.headers.get("Retry-After")
            raise HieRateLimited(
                int(retry_after) if retry_after and retry_after.isdigit() else None
            )
        if status >= 500:
            call.outcome = ExchangeLog.Outcome.UNAVAILABLE
            if write:
                raise HieOutcomeUnknown(
                    "The HIE failed while handling the change; check its status before trying again.",
                    status=status,
                    payer_message=message,
                )
            raise HieUnavailable("The HIE failed to answer.", status=status, payer_message=message)
        raise HieRejected(
            "The HIE refused the request.", status=status, payer_message=message, error=error
        )

    def _backoff(self, attempt: int, retry_after: str | None = None) -> None:
        if retry_after and retry_after.isdigit():
            delay = min(float(retry_after), 5.0)
        else:
            delay = min(0.25 * (2 ** (attempt - 1)), 2.0) + random.uniform(0, 0.1)  # noqa: S311 - jitter
        self._sleep(delay)

    def close(self) -> None:
        self._http.close()


def client(*, transport: httpx.BaseTransport | None = None) -> HieClient:
    return HieClient(config_from_settings(), transport=transport)


__all__ = ["HieClient", "HieConfig", "HieError", "TokenCache", "client", "config_from_settings"]
