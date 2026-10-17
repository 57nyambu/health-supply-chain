"""Errors of the HIE transport. Adapters translate them into their own port's errors
(``apps.insurance.gateway`` for SHA, ``RegistryUnavailable`` for the registries)."""


class HieError(Exception):
    """Base. Messages are safe for staff: no PHI, no secrets."""

    def __init__(self, message: str = "", *, status: int | None = None, payer_message: str = ""):
        super().__init__(message or self.__doc__ or "HIE error")
        self.status = status
        # The HIE's own ``message`` text (its error schema is ``{error, message}``), kept
        # for staff and support tickets; it never contains our secrets.
        self.payer_message = payer_message


class HieConfigurationError(HieError):
    """The HIE integration is not configured for this mode (credentials or a spec gap)."""


class HieUnavailable(HieError):
    """The HIE did not answer, or answered 5xx to a read. Nothing was changed."""


class HieOutcomeUnknown(HieError):
    """A write was sent but no reliable answer came back (timeout, connection lost, 5xx).
    Query before trying again; never resend blindly."""


class HieAuthError(HieError):
    """Our credentials were refused (401 after one token refresh)."""


class HieForbidden(HieError):
    """403: the credential may not do this, or the tenant/facility context is missing."""


class HieNotFound(HieError):
    """404: no such record."""


class HieRejected(HieError):
    """400/409/422: the HIE refused the request; ``error``/``message`` say why."""

    def __init__(
        self,
        message: str = "",
        *,
        status: int | None = None,
        payer_message: str = "",
        error: str = "",
    ):
        super().__init__(message, status=status, payer_message=payer_message)
        self.error = error


class HieRateLimited(HieError):
    """429: slow down."""

    def __init__(self, retry_after: int | None = None):
        super().__init__("The HIE is limiting requests.", status=429)
        self.retry_after = retry_after
