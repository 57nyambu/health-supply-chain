from apps.access.catalogue import PermissionDef as P
from apps.access.catalogue import Sensitivity as S

PERMISSIONS = [
    P("visits.visit.read", "View visits and their status", S.PHI),
    P("visits.visit.create", "Open a visit", S.PHI),
    P("visits.queue.manage", "Call, skip, transfer and prioritise queue tickets", S.PHI),
    P("visits.gate.override", "Override a payment gate with a reason", S.FINANCIAL),
    P("visits.appointment.manage", "Book and change appointments", S.PHI),
    P(
        "visits.gate.manage",
        "Change payment-gate policies (second administrator approves)",
        S.ADMIN,
    ),
    P("visits.board.manage", "Set up queue display boards and their device tokens", S.ADMIN),
    P("visits.board.display", "Show a queue board (board device tokens only; no names)"),
]
