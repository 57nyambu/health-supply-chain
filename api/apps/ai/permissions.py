"""Permission catalogue for this app (DESIGN §7.5). Legacy role checks were removed in P1-UAC-03."""

from apps.access.catalogue import PermissionDef as P
from apps.access.catalogue import Sensitivity as S

PERMISSIONS = [
    P("ai.assistant.use", "Use the supply assistant (disabled until a DPIA covers it)", S.ADMIN),
    P("ai.ocr.use", "Use OCR stock intake (disabled until a DPIA covers it)", S.ADMIN),
    P("ai.forecast.read", "View stock forecasts"),
    P("ai.redistribution.read", "View stock redistribution suggestions"),
    P("public.facility.read", "Read the public facility directory and alerts (API key)"),
]
