from apps.access.catalogue import PermissionDef as P
from apps.access.catalogue import Sensitivity as S

PERMISSIONS = [
    P("integrations.sha.configure", "Configure the HIE/SHA integration", S.ADMIN, privileged=True),
    P(
        "integrations.payments.configure",
        "Configure payment providers (M-Pesa, banks, cards)",
        S.ADMIN,
        privileged=True,
    ),
    P(
        "integrations.insurers.configure",
        "Configure private insurer switches",
        S.ADMIN,
        privileged=True,
    ),
    P("integrations.messaging.configure", "Configure SMS and e-mail", S.ADMIN),
    P(
        "integrations.exchange_log.read",
        "View integration exchange logs (encrypted payloads stay hidden)",
        S.ADMIN,
    ),
]
