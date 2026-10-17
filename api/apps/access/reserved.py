"""Permission codes of domains whose Django app does not exist yet.

Roles (DESIGN §7.4) reference these codes from day one so the role matrix is
complete. When a domain's app is created, its definitions move into
``apps/<app>/permissions.py`` in the same commit (the catalogue rejects a code
declared twice).
"""

from apps.access.catalogue import PermissionDef as P
from apps.access.catalogue import Sensitivity as S

PERMISSIONS = [
    # --- privacy (Phase 3 breach workflow) -----------------------------------------------------------
    P("privacy.breach.read", "View privacy incidents", S.SENSITIVE),
    P(
        "privacy.breach.manage",
        "Record and manage privacy incidents and notifications",
        S.SENSITIVE,
    ),
    # --- clinical (Phase 2) ----------------------------------------------------------------------------
    P(
        "clinical.record.read_summary",
        "View the clinical summary (allergies, alerts, problems, medications)",
        S.PHI,
    ),
    P("clinical.record.read_full", "View the full clinical record", S.PHI, requires_licence=True),
    P(
        "clinical.record.read_sensitive",
        "View sensitive-category clinical data",
        S.SENSITIVE,
        requires_licence=True,
    ),
    P("clinical.vitals.record", "Record vital signs", S.PHI, requires_licence=True),
    P("clinical.triage.record", "Record triage assessments", S.PHI, requires_licence=True),
    P("clinical.note.write", "Write clinical notes", S.PHI, requires_licence=True),
    P("clinical.nursing_note.write", "Write nursing notes", S.PHI, requires_licence=True),
    P("clinical.diagnosis.write", "Record diagnoses (ICD-11)", S.PHI, requires_licence=True),
    P(
        "clinical.allergy.write",
        "Record allergies and adverse reactions",
        S.PHI,
        requires_licence=True,
    ),
    P(
        "clinical.note.cosign",
        "Co-sign notes and prescriptions of supervised interns",
        S.PHI,
        requires_licence=True,
    ),
    # --- orders (Phase 2) ------------------------------------------------------------------------------
    P("orders.lab.create", "Order laboratory tests", S.PHI, requires_licence=True),
    P("orders.imaging.create", "Order imaging studies", S.PHI, requires_licence=True),
    P("orders.procedure.create", "Order procedures", S.PHI, requires_licence=True),
    P(
        "orders.procedure.perform",
        "Perform and record ordered procedures",
        S.PHI,
        requires_licence=True,
    ),
    P("orders.order.cancel", "Cancel orders with a reason", S.PHI, requires_licence=True),
    # --- laboratory (Phase 2) ------------------------------------------------------------------------------
    P("laboratory.specimen.collect", "Collect and receive specimens", S.PHI, requires_licence=True),
    P("laboratory.result.enter", "Enter laboratory results", S.PHI, requires_licence=True),
    P("laboratory.result.validate", "Validate laboratory results", S.PHI, requires_licence=True),
    P(
        "laboratory.result.release",
        "Release validated results to clinicians",
        S.PHI,
        requires_licence=True,
    ),
    # --- imaging (Phase 2) -----------------------------------------------------------------------------------
    P("imaging.study.perform", "Perform imaging studies", S.PHI, requires_licence=True),
    P("imaging.report.sign", "Sign imaging reports", S.PHI, requires_licence=True),
    # --- pharmacy (Phase 2) -----------------------------------------------------------------------------------
    P("pharmacy.prescription.create", "Prescribe medicines", S.PHI, requires_licence=True),
    P("pharmacy.prescription.verify", "Verify prescriptions", S.PHI, requires_licence=True),
    P("pharmacy.medicine.dispense", "Dispense medicines", S.PHI, requires_licence=True),
    P("pharmacy.controlled.dispense", "Dispense controlled drugs", S.PHI, requires_licence=True),
    P("pharmacy.mar.record", "Record medication administration", S.PHI, requires_licence=True),
    P("pharmacy.stock_adjustment.request", "Request a pharmacy stock adjustment"),
    P(
        "pharmacy.stock_adjustment.approve",
        "Approve controlled-drug stock adjustments",
        privileged=True,
    ),
    # --- inpatient (Phase 2) ------------------------------------------------------------------------------------
    P("inpatient.admission.create", "Admit a patient", S.PHI, requires_licence=True),
    P("inpatient.bed.allocate", "Allocate and transfer beds", S.PHI),
    P("inpatient.discharge.sign", "Sign discharge summaries", S.PHI, requires_licence=True),
    # --- referrals (Phase 2) ------------------------------------------------------------------------------------
    P("referrals.referral.create", "Refer a patient", S.PHI, requires_licence=True),
    # --- payments (Phase 2/3) --------------------------------------------------------------------------------------
    P("payments.receive.cash", "Receive cash payments", S.FINANCIAL),
    P("payments.receive.mpesa", "Initiate and receive M-Pesa payments", S.FINANCIAL),
    P("payments.receive.card", "Receive card payments (hosted page or PDQ)", S.FINANCIAL),
    P("payments.receive.bank", "Receive bank payments", S.FINANCIAL),
    P("payments.shift.own", "Open, run and close one's own cashier shift", S.FINANCIAL),
    P("payments.shift.supervise", "Supervise cashier shifts and variances", S.FINANCIAL),
    P("payments.void.approve", "Approve voiding a receipt", S.FINANCIAL, privileged=True),
    P("payments.refund.request", "Request a refund", S.FINANCIAL),
    P("payments.refund.approve", "Approve refunds", S.FINANCIAL, privileged=True),
    P("payments.reconciliation.run", "Run payment reconciliation", S.FINANCIAL),
    P("payments.reconciliation.signoff", "Sign off reconciliation", S.FINANCIAL, privileged=True),
    P(
        "payments.suspense.allocate_approve",
        "Approve allocation from the suspense account",
        S.FINANCIAL,
        privileged=True,
    ),
    # --- reporting --------------------------------------------------------------------------------------------------------
    P("reporting.moh.read", "View MOH registers and summaries", S.PHI),
    P("reporting.moh.export", "Export MOH reports and KHIS data", S.PHI),
    P("reports.financial.read", "View financial reports", S.FINANCIAL),
    P("reports.aggregate.read", "View aggregated, de-identified reports"),
]
