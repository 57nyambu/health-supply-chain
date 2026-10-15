from django.conf import settings
from rest_framework.permissions import BasePermission

from apps.core.permissions import IsTier1 as CoreIsTier1
from apps.core.permissions import IsTier1OrTier2 as CoreIsTier1OrTier2


class IsTier1(CoreIsTier1):
    pass


class IsTier1OrTier2(CoreIsTier1OrTier2):
    pass


class HasPublicAPIKey(BasePermission):
    """Allows requests authenticated with the shared PUBLIC_API_KEY header."""

    def has_permission(self, request, view):
        key = request.headers.get("X-API-Key")
        expected = getattr(settings, "PUBLIC_API_KEY", "")
        return bool(expected and key and key == expected)


# --- Permission catalogue (DESIGN §7.5). Endpoints stay off until a DPIA (ADR-014). ----------------
from apps.access.catalogue import PermissionDef as P  # noqa: E402
from apps.access.catalogue import Sensitivity as S  # noqa: E402

PERMISSIONS = [
    P("ai.assistant.use", "Use the supply assistant (disabled until a DPIA covers it)", S.ADMIN),
    P("ai.ocr.use", "Use OCR stock intake (disabled until a DPIA covers it)", S.ADMIN),
    P("ai.forecast.read", "View stock forecasts"),
    P("ai.redistribution.read", "View stock redistribution suggestions"),
    P("public.facility.read", "Read the public facility directory and alerts (API key)"),
]
