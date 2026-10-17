import type { JourneyStep } from "@/components/clinical/journey-rail";
import type { Tone, TriageLevel } from "@/components/ui/status";

/** Visit labels and the journey rail driven by `Visit.status` (DESIGN §6.2, DESIGN-SYSTEM §7). */

export const VISIT_TYPES = [
  { value: "opd", label: "Outpatient (OPD)" },
  { value: "emergency", label: "Emergency" },
  { value: "walk_in_pharmacy", label: "Walk-in pharmacy" },
  { value: "walk_in_lab", label: "Walk-in laboratory" },
];

export const VISIT_TYPE_LABEL: Record<string, string> = {
  ...Object.fromEntries(VISIT_TYPES.map((t) => [t.value, t.label])),
  inpatient: "Inpatient",
};

export const STATUS_LABEL: Record<string, string> = {
  registered: "Registered",
  awaiting_triage: "Waiting for triage",
  in_triage: "In triage",
  awaiting_consultation: "Waiting for consultation",
  in_consultation: "In consultation",
  awaiting_services: "Waiting for services",
  in_service: "At a service point",
  awaiting_review: "Waiting for review",
  admitted: "Admitted",
  clinically_complete: "Clinically complete",
  financially_cleared: "Financially cleared",
  closed: "Closed",
  cancelled: "Cancelled",
  left_before_seen: "Left before being seen",
  deceased: "Deceased",
};

const STEP: Record<string, JourneyStep> = {
  registered: "Reception",
  cancelled: "Reception",
  left_before_seen: "Reception",
  awaiting_triage: "Triage",
  in_triage: "Triage",
  awaiting_consultation: "Consultation",
  in_consultation: "Consultation",
  awaiting_services: "Services",
  in_service: "Services",
  awaiting_review: "Review",
  admitted: "Disposition",
  deceased: "Disposition",
  clinically_complete: "Settlement",
  financially_cleared: "Settlement",
  closed: "Settlement",
};

/** The journey step a visit status belongs to; no visit means the patient is at reception. */
export function journeyStep(status: string | undefined | null): JourneyStep {
  return (status && STEP[status]) || "Reception";
}

export function statusTone(status: string): Tone {
  if (["closed", "financially_cleared", "clinically_complete"].includes(status)) return "success";
  if (["cancelled", "left_before_seen", "deceased"].includes(status)) return "neutral";
  if (status.startsWith("awaiting")) return "warning";
  return "info";
}

export const OPEN_STATUSES = Object.keys(STATUS_LABEL).filter(
  (s) => !["clinically_complete", "financially_cleared", "closed", "cancelled", "left_before_seen", "deceased"].includes(s),
);

export const PAYER_TYPE_LABEL: Record<string, string> = {
  cash: "Cash",
  sha: "SHA",
  insurer: "Private insurer",
  corporate: "Corporate",
  waiver: "Waiver",
};

export const PRIORITY_REASONS = [
  { value: "elderly", label: "Elderly" },
  { value: "disabled", label: "Disability" },
  { value: "pregnant", label: "Pregnant" },
  { value: "child", label: "Young child" },
  { value: "clinical", label: "Clinical concern" },
  { value: "vip", label: "VIP" },
];

export const GATE_LABEL: Record<string, string> = {
  none: "No gate",
  pay_before_service: "Pay before service",
  eligibility_verified: "Eligibility verified",
  member_verified: "Member verified",
  preauth_approved: "Pre-authorisation approved",
  deposit: "Deposit paid",
  credit_limit: "Within credit limit",
};

export const GATE_CONTEXT_LABEL: Record<string, string> = {
  consultation: "OPD consultation",
  lab: "Laboratory",
  imaging: "Imaging",
  procedure: "Procedure",
  pharmacy: "Pharmacy",
  elective_admission: "Elective admission",
};

export function triageLevel(category: string | null | undefined): TriageLevel | null {
  return category && ["red", "orange", "yellow", "green", "blue"].includes(category) ? (category as TriageLevel) : null;
}

/** "12 min" / "1 h 05 min" since an ISO timestamp. */
export function waitText(since: string, now: number = Date.now()): string {
  const minutes = Math.max(0, Math.floor((now - new Date(since).getTime()) / 60000));
  if (minutes < 60) return `${minutes} min`;
  return `${Math.floor(minutes / 60)} h ${String(minutes % 60).padStart(2, "0")} min`;
}
