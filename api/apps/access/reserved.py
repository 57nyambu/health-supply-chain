"""Permission codes of domains whose Django app does not exist yet.

Roles (DESIGN §7.4) reference these codes from day one so the role matrix is
complete. When a domain's app is created, its definitions move into
``apps/<app>/permissions.py`` in the same commit (the catalogue rejects a code
declared twice).
"""

from apps.access.catalogue import PermissionDef as P
from apps.access.catalogue import Sensitivity as S

PERMISSIONS = [
    # --- facilities (P1-FAC-01) ---------------------------------------------------------------
    P("facilities.facility.read", "View facility registry details"),
    P(
        "facilities.facility.manage",
        "Edit facility identifiers and settings",
        S.ADMIN,
        privileged=True,
    ),
    P("facilities.location.read", "View departments, service points, wards and beds"),
    P(
        "facilities.location.manage",
        "Create and edit departments, service points, wards and beds",
        S.ADMIN,
    ),
    P("facilities.bed.update_status", "Change bed status (available, cleaning, out of service)"),
    # --- patients (P1-PAT-01, P1-DATA-02) ----------------------------------------------------------
    P("patients.patient.search", "Search the patient registry", S.PHI),
    P("patients.patient.read", "View patient demographics, identifiers and contacts", S.PHI),
    P("patients.patient.create", "Register a patient", S.PHI),
    P("patients.patient.update", "Update patient demographics and contacts", S.PHI),
    P(
        "patients.patient.register_unidentified",
        "Quick-register an unidentified emergency patient",
        S.PHI,
    ),
    P(
        "patients.duplicate.override",
        "Create a record despite a likely duplicate, with a reason",
        S.PHI,
    ),
    P("patients.registry.search", "Search the national Client Registry", S.PHI),
    P("patients.registry.import", "Import a Client Registry match into a local record", S.PHI),
    P("patients.consent.record", "Record privacy-notice acknowledgement and consents", S.PHI),
    P("patients.merge.request", "Request a patient merge or unmerge", S.PHI),
    P("patients.merge.approve", "Approve a patient merge or unmerge", S.PHI, privileged=True),
    P("patients.dsar.read", "View data subject requests", S.PHI),
    P("patients.dsar.process", "Process data subject requests and produce exports", S.PHI),
    # --- audit (P1-AUD-01) -------------------------------------------------------------------------
    P("audit.log.read", "View the audit log", S.SENSITIVE),
    # --- privacy (Phase 3 breach workflow) -----------------------------------------------------------
    P("privacy.breach.read", "View privacy incidents", S.SENSITIVE),
    P(
        "privacy.breach.manage",
        "Record and manage privacy incidents and notifications",
        S.SENSITIVE,
    ),
    # --- documents (P1-STO-01) ---------------------------------------------------------------------
    P("documents.document.read", "View patient documents through the audited stream", S.PHI),
    P("documents.document.upload", "Upload patient documents", S.PHI),
    P(
        "documents.storage.manage",
        "Run storage migration and verification",
        S.ADMIN,
        privileged=True,
    ),
    # --- visits (Phase 2) --------------------------------------------------------------------------
    P("visits.visit.read", "View visits and their status", S.PHI),
    P("visits.visit.create", "Open a visit", S.PHI),
    P("visits.queue.manage", "Call, skip, transfer and prioritise queue tickets", S.PHI),
    P("visits.gate.override", "Override a payment gate with a reason", S.FINANCIAL),
    P("visits.appointment.manage", "Book and change appointments", S.PHI),
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
    # --- billing (Phase 2) ----------------------------------------------------------------------------------------
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
    # --- insurance (Phase 3) ---------------------------------------------------------------------------------------------
    P("insurance.eligibility.check", "Check SHA and insurer eligibility", S.PHI),
    P("insurance.consent.request", "Request payer consent (OTP or biometrics)", S.PHI),
    P("insurance.preauth.request", "Request pre-authorisation", S.PHI),
    P(
        "insurance.preauth.clinical_signoff",
        "Clinically sign off pre-authorisation requests",
        S.PHI,
        requires_licence=True,
    ),
    P("insurance.claim.prepare", "Prepare and scrub claims", S.PHI),
    P("insurance.claim.submit", "Submit claims to payers", S.PHI),
    P("insurance.claim.cancel_submitted", "Cancel a submitted claim", S.PHI, privileged=True),
    P("insurance.remittance.post", "Post insurer remittances", S.FINANCIAL),
    # --- reporting --------------------------------------------------------------------------------------------------------
    P("reporting.moh.read", "View MOH registers and summaries", S.PHI),
    P("reporting.moh.export", "Export MOH reports and KHIS data", S.PHI),
    P("reports.financial.read", "View financial reports", S.FINANCIAL),
    P("reports.aggregate.read", "View aggregated, de-identified reports"),
]
