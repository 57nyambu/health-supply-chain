from apps.access.catalogue import PermissionDef as P
from apps.access.catalogue import Sensitivity as S

PERMISSIONS = [
    P("sales.pos.sell", "Sell over the counter at the pharmacy point of sale", S.FINANCIAL),
    P("sales.order.read", "View over-the-counter orders and receipts", S.FINANCIAL),
]
