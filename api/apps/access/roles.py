"""Seeded system roles (DESIGN §7.4). ``sync_access`` writes them to the database.

Chart access: ``chart_baseline`` applies to any patient in the user's scope;
``chart_care_team`` applies when the user is on the patient's care team (DESIGN §7.7).
The sensitive level additionally needs ``clinical.record.read_sensitive``.
"""

from dataclasses import dataclass
from enum import StrEnum

from apps.access.catalogue import expand


class ChartAccess(StrEnum):
    NONE = "none"
    DEMOGRAPHICS = "demographics"
    SUMMARY = "summary"
    FULL = "full"
    SENSITIVE = "sensitive"


CHART_LEVELS = list(ChartAccess)  # ordered from least to most access


@dataclass(frozen=True)
class RoleDef:
    code: str
    name: str
    description: str
    grants: tuple[str, ...]
    chart_baseline: ChartAccess = ChartAccess.NONE
    chart_care_team: ChartAccess = ChartAccess.NONE
    privileged: bool = False
    mfa_required: bool = False
    addon: bool = False
    requires_cosign: bool = False
    service_account: bool = False
    # Regulators whose licence covers this role's licensed permissions (KE-PRF-01).
    licence_regulators: tuple[str, ...] = ()

    def permission_codes(self) -> set[str]:
        codes: set[str] = set()
        for pattern in self.grants:
            codes |= expand(pattern)
        return codes


# Shared grant bundles -------------------------------------------------------------------------------
PATIENT_LOOKUP = ("patients.patient.search", "patients.patient.read", "visits.visit.read")
WORKLIST = (
    *PATIENT_LOOKUP,
    "visits.queue.manage",
    "clinical.record.read_summary",
    "facilities.location.read",
)
CLINICIAN = (
    *WORKLIST,
    "clinical.record.read_full",
    "clinical.note.write",
    "clinical.diagnosis.write",
    "clinical.allergy.write",
    "clinical.vitals.record",
    "orders.lab.create",
    "orders.imaging.create",
    "orders.procedure.create",
    "orders.order.cancel",
    "pharmacy.prescription.create",
    "referrals.referral.create",
    "insurance.preauth.request",
    "access.breakglass.request",
    "documents.document.read",
    "documents.document.upload",
)
MEDICAL_OFFICER = (
    *CLINICIAN,
    "inpatient.admission.create",
    "inpatient.discharge.sign",
    "clinical.note.cosign",
)
LAB = (*WORKLIST, "laboratory.specimen.collect", "laboratory.result.enter")
DISPENSARY = (
    *WORKLIST,
    "pharmacy.medicine.dispense",
    "pharmacy.stock_adjustment.request",
    "inventory.stock.read",
    "inventory.batch.read",
    "sales.pos.sell",
    "sales.order.read",
)
INVENTORY = (
    "inventory.product.*",
    "inventory.stock.*",
    "inventory.batch.*",
    "inventory.store.*",
    "inventory.transfer.*",
    "inventory.alert.read",
    "operations.*",
    "ai.*",
    "facilities.location.read",
)

C = ChartAccess

ROLES: list[RoleDef] = [
    RoleDef(
        "system_admin",
        "System administrator",
        "Technical configuration and integrations",
        (
            "admin.config.*",
            "admin.api.read_schema",
            "integrations.*",
            "access.role.read",
            "access.review.read",
            "documents.storage.manage",
            "facilities.facility.read",
        ),
        privileged=True,
        mfa_required=True,
    ),
    RoleDef(
        "facility_admin",
        "Facility administrator",
        "Users, roles and assignments within the facility",
        (
            "admin.user.*",
            "admin.config.read",
            "access.role.*",
            "access.assignment.*",
            "access.approval.read",
            "access.licence.*",
            "access.review.read",
            "facilities.*",
            "operations.*",
        ),
        privileged=True,
        mfa_required=True,
    ),
    RoleDef(
        "medical_superintendent",
        "Medical superintendent",
        "Clinical oversight, approvals, break-glass review",
        (
            *WORKLIST,
            "clinical.record.read_full",
            "clinical.record.read_sensitive",
            "clinical.note.cosign",
            "visits.gate.override",
            "billing.waiver.approve_high",
            "access.breakglass.review",
            "access.approval.read",
            "inpatient.discharge.sign",
            "reporting.moh.read",
            "reports.aggregate.read",
            "documents.document.read",
        ),
        chart_baseline=C.FULL,
        chart_care_team=C.SENSITIVE,
        privileged=True,
        mfa_required=True,
        licence_regulators=("KMPDC",),
    ),
    RoleDef(
        "hrio",
        "Health records officer",
        "Registration quality, merges, MOH reporting, record release",
        (
            "patients.patient.*",
            "patients.duplicate.override",
            "patients.registry.*",
            "patients.consent.record",
            "patients.merge.request",
            "patients.dsar.read",
            "patients.dsar.process",
            "reporting.moh.*",
            "visits.visit.read",
            "clinical.record.read_summary",
            "documents.document.read",
            "facilities.location.read",
        ),
        chart_baseline=C.SUMMARY,
        chart_care_team=C.SUMMARY,
    ),
    RoleDef(
        "receptionist",
        "Receptionist",
        "Registration, visits, queues, eligibility",
        (
            "patients.patient.*",
            "patients.duplicate.override",
            "patients.registry.*",
            "patients.consent.record",
            "visits.visit.create",
            "visits.visit.read",
            "visits.queue.manage",
            "visits.appointment.manage",
            "insurance.eligibility.check",
            "insurance.consent.request",
            "facilities.location.read",
        ),
        chart_baseline=C.DEMOGRAPHICS,
        chart_care_team=C.DEMOGRAPHICS,
    ),
    RoleDef(
        "triage_nurse",
        "Triage nurse",
        "Vital signs and triage",
        (*WORKLIST, "clinical.vitals.record", "clinical.triage.record", "clinical.allergy.write"),
        chart_baseline=C.SUMMARY,
        chart_care_team=C.SUMMARY,
        licence_regulators=("NCK",),
    ),
    RoleDef(
        "nurse",
        "Nurse",
        "Nursing notes, medication administration, procedures, ward care",
        (
            *WORKLIST,
            "clinical.record.read_full",
            "clinical.nursing_note.write",
            "clinical.vitals.record",
            "clinical.allergy.write",
            "pharmacy.mar.record",
            "orders.procedure.perform",
            "access.breakglass.request",
            "documents.document.read",
            "documents.document.upload",
        ),
        chart_baseline=C.SUMMARY,
        chart_care_team=C.FULL,
        licence_regulators=("NCK",),
    ),
    RoleDef(
        "clinical_officer",
        "Clinical officer",
        "Consultation, diagnosis, orders, prescribing",
        CLINICIAN,
        chart_baseline=C.SUMMARY,
        chart_care_team=C.FULL,
        licence_regulators=("COC",),
    ),
    RoleDef(
        "medical_officer",
        "Medical officer",
        "As clinical officer, plus admission and discharge",
        MEDICAL_OFFICER,
        chart_baseline=C.SUMMARY,
        chart_care_team=C.FULL,
        licence_regulators=("KMPDC",),
    ),
    RoleDef(
        "specialist",
        "Specialist / consultant",
        "As medical officer, plus clinical pre-authorisation sign-off",
        (*MEDICAL_OFFICER, "insurance.preauth.clinical_signoff"),
        chart_baseline=C.SUMMARY,
        chart_care_team=C.FULL,
        licence_regulators=("KMPDC",),
    ),
    RoleDef(
        "intern",
        "Intern (any cadre)",
        "Supervised practice; notes and prescriptions need a co-signature",
        CLINICIAN,
        chart_baseline=C.SUMMARY,
        chart_care_team=C.FULL,
        requires_cosign=True,
        licence_regulators=("KMPDC", "COC", "NCK", "PPB"),
    ),
    RoleDef(
        "lab_technologist",
        "Laboratory technologist",
        "Specimens and results",
        LAB,
        chart_baseline=C.SUMMARY,
        chart_care_team=C.SUMMARY,
        licence_regulators=("KMLTTB",),
    ),
    RoleDef(
        "lab_supervisor",
        "Laboratory supervisor",
        "Result validation and release",
        (*LAB, "laboratory.result.validate", "laboratory.result.release"),
        chart_baseline=C.SUMMARY,
        chart_care_team=C.SUMMARY,
        licence_regulators=("KMLTTB",),
    ),
    RoleDef(
        "radiographer",
        "Radiographer",
        "Performs imaging studies",
        (*WORKLIST, "imaging.study.perform"),
        chart_baseline=C.SUMMARY,
        chart_care_team=C.SUMMARY,
        licence_regulators=("OTHER",),
    ),
    RoleDef(
        "radiologist",
        "Radiologist",
        "Reports imaging studies",
        (*WORKLIST, "imaging.study.perform", "imaging.report.sign"),
        chart_baseline=C.SUMMARY,
        chart_care_team=C.SUMMARY,
        licence_regulators=("KMPDC",),
    ),
    RoleDef(
        "pharmacist",
        "Pharmacist",
        "Verifies and dispenses, including controlled drugs",
        (*DISPENSARY, "pharmacy.prescription.verify", "pharmacy.controlled.dispense"),
        chart_baseline=C.SUMMARY,
        chart_care_team=C.SUMMARY,
        licence_regulators=("PPB",),
    ),
    RoleDef(
        "pharm_tech",
        "Pharmaceutical technologist",
        "Dispenses",
        DISPENSARY,
        chart_baseline=C.SUMMARY,
        chart_care_team=C.SUMMARY,
        licence_regulators=("PPB",),
    ),
    RoleDef(
        "cashier",
        "Cashier",
        "Receives payments, issues receipts, runs own shift",
        (
            *PATIENT_LOOKUP,
            "visits.queue.manage",
            "payments.receive.*",
            "payments.shift.own",
            "payments.refund.request",
            "billing.charge.read",
            "sales.pos.sell",
            "sales.order.read",
        ),
        chart_baseline=C.DEMOGRAPHICS,
        chart_care_team=C.DEMOGRAPHICS,
    ),
    RoleDef(
        "billing_officer",
        "Billing officer",
        "Charges, invoices, adjustments",
        (
            *PATIENT_LOOKUP,
            "billing.charge.read",
            "billing.charge.adjust_request",
            "billing.invoice.finalize",
            "billing.waiver.request",
            "billing.pricelist.manage",
        ),
        chart_baseline=C.DEMOGRAPHICS,
        chart_care_team=C.DEMOGRAPHICS,
    ),
    RoleDef(
        "claims_officer",
        "Claims officer",
        "Eligibility, pre-authorisations, claims, rejections",
        (
            *PATIENT_LOOKUP,
            "insurance.eligibility.check",
            "insurance.consent.request",
            "insurance.preauth.request",
            "insurance.claim.prepare",
            "insurance.claim.submit",
            "insurance.remittance.post",
            "billing.charge.read",
        ),
        chart_baseline=C.DEMOGRAPHICS,
        chart_care_team=C.DEMOGRAPHICS,
        mfa_required=True,
    ),
    RoleDef(
        "finance_manager",
        "Finance manager",
        "Approvals, reconciliation, write-offs",
        (
            "payments.refund.approve",
            "billing.waiver.approve",
            "billing.writeoff.approve",
            "payments.reconciliation.run",
            "payments.reconciliation.signoff",
            "billing.pricelist.approve",
            "payments.suspense.allocate_approve",
            "reports.financial.read",
            "billing.charge.read",
            "access.approval.read",
        ),
        privileged=True,
        mfa_required=True,
    ),
    RoleDef(
        "store_keeper",
        "Store keeper / procurement",
        "Inventory, requisitions, purchasing",
        INVENTORY,
    ),
    RoleDef(
        "dpo",
        "Data protection officer",
        "DSARs, consents, breach log, audit review",
        (
            "audit.log.read",
            "patients.dsar.*",
            "privacy.breach.*",
            "access.breakglass.review",
            "access.review.read",
        ),
        mfa_required=True,
    ),
    RoleDef(
        "auditor",
        "Auditor",
        "Read-only audit of finance and access",
        ("audit.log.read", "reports.financial.read", "access.review.read"),
        mfa_required=True,
    ),
    RoleDef(
        "report_viewer",
        "Report viewer",
        "Aggregated, de-identified reports",
        (
            "reports.aggregate.read",
            "operations.stats.read",
            "operations.alert.read",
            "inventory.alert.read",
        ),
    ),
    # Supervisor add-on roles: assigned on top of a base role (DESIGN §7.4, §7.9).
    RoleDef(
        "cashier_supervisor",
        "Cashier supervisor",
        "Shift supervision and voids",
        ("payments.shift.supervise", "payments.void.approve"),
        addon=True,
    ),
    RoleDef(
        "billing_supervisor",
        "Billing supervisor",
        "Approves waivers up to threshold A",
        ("billing.waiver.approve_low",),
        addon=True,
    ),
    RoleDef(
        "claims_supervisor",
        "Claims supervisor",
        "Cancels submitted claims",
        ("insurance.claim.cancel_submitted",),
        addon=True,
    ),
    RoleDef(
        "hrio_supervisor",
        "HRIO supervisor",
        "Approves patient merges and unmerges",
        ("patients.merge.approve",),
        addon=True,
    ),
    RoleDef(
        "nurse_in_charge",
        "Nurse in charge",
        "Gate overrides and ward bed allocation",
        ("visits.gate.override", "inpatient.bed.allocate", "facilities.bed.update_status"),
        addon=True,
    ),
    RoleDef(
        "pharmacy_in_charge",
        "Pharmacy in-charge",
        "Approves controlled-drug stock adjustments",
        ("pharmacy.stock_adjustment.approve",),
        addon=True,
    ),
    # Service accounts (API keys; no PHI scopes without an ADR).
    RoleDef(
        "public_api_client",
        "Public API client",
        "Third-party integrators on the public, non-PHI API",
        ("public.facility.read",),
        service_account=True,
    ),
]

ROLES_BY_CODE = {role.code: role for role in ROLES}
