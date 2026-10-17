from apps.access.catalogue import PermissionDef as P
from apps.access.catalogue import Sensitivity as S

PERMISSIONS = [
    P("billing.service.read", "View the service catalogue and prices"),
    P("billing.charge.read", "View charges and bills", S.FINANCIAL),
    P("billing.charge.adjust_request", "Request a charge adjustment", S.FINANCIAL),
    P("billing.invoice.finalize", "Finalise invoices", S.FINANCIAL),
    P("billing.waiver.request", "Request a waiver", S.FINANCIAL),
    P("billing.waiver.approve_low", "Approve waivers up to threshold A", S.FINANCIAL),
    P("billing.waiver.approve", "Approve waivers above threshold A", S.FINANCIAL, privileged=True),
    P(
        "billing.waiver.approve_high",
        "Co-approve waivers above threshold B",
        S.FINANCIAL,
        privileged=True,
    ),
    P(
        "billing.writeoff.approve",
        "Approve write-offs of patient debt",
        S.FINANCIAL,
        privileged=True,
    ),
    P("billing.pricelist.manage", "Edit price lists and services (maker)", S.FINANCIAL),
    P(
        "billing.pricelist.approve",
        "Approve price list changes and new services",
        S.FINANCIAL,
        privileged=True,
    ),
]
