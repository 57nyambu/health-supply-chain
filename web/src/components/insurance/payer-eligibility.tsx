"use client";

/**
 * Extension slot owned by the Phase 3 lane (ADR-024, docs/agent/lanes/SEAMS.md, W1).
 * The Phase 2 visit-opening form renders it under the payer choice; Phase 3 fills it with
 * eligibility and consent (OTP or biometrics) for the chosen cover. Renders nothing until then.
 */
export type PayerEligibilityProps = {
  patientId: string;
  /** The cover chosen for the visit; null for cash / self-pay. */
  coverageId: string | null;
  /** Phase 3 reports whether the visit may proceed under this cover (emergencies never wait). */
  onStatusChange?: (status: "not_applicable" | "pending" | "verified" | "failed") => void;
};

export function PayerEligibility(props: PayerEligibilityProps): null {
  void props;
  return null;
}
