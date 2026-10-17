/**
 * Insurance calls used by the Phase 3 slots and pages. Calls that reach a payer carry an
 * Idempotency-Key (DESIGN §17): a retried click never asks the payer twice.
 */
import { api } from "@/lib/api/client";
import { rows, type Schemas, unwrap } from "@/lib/api/query";

export type Coverage = Schemas["Coverage"];
export type EligibilityCheck = Schemas["EligibilityCheck"];
export type ConsentStep = Schemas["ConsentStep"];
export type PayerConsent = Schemas["PayerConsent"];
export type PayerServiceCode = Schemas["PayerServiceCode"];

export function idempotencyKey(): string {
  return globalThis.crypto.randomUUID();
}

const keyed = () => ({ "Idempotency-Key": idempotencyKey() });

/** The patient's covers (the API returns a plain list; the schema describes a page). */
export async function coveragesOf(patientId: string): Promise<Coverage[]> {
  return rows(await unwrap(api.GET("/api/v1/insurance/coverages/", { params: { query: { patient: patientId, purpose: "registration" } } })));
}

/** The latest snapshot, or null when the cover was never checked. */
export async function latestEligibility(coverageId: string): Promise<EligibilityCheck | null> {
  const { data, response } = await api.GET("/api/v1/insurance/coverages/{id}/eligibility/", {
    params: { path: { id: coverageId } },
  });
  if (response.status === 404) return null;
  return unwrap(Promise.resolve({ data, response, error: response.ok ? undefined : {} }));
}

export function checkEligibility(coverageId: string) {
  return unwrap(
    api.POST("/api/v1/insurance/coverages/{id}/eligibility/", {
      params: { path: { id: coverageId } },
      headers: keyed(),
    }),
  );
}

export async function benefitsOf(coverageId: string): Promise<PayerServiceCode[]> {
  return rows(await unwrap(api.GET("/api/v1/insurance/coverages/{id}/benefits/", { params: { path: { id: coverageId } } })));
}

export function startConsent(body: Schemas["ConsentStartRequest"]) {
  return unwrap(api.POST("/api/v1/insurance/consents/", { headers: keyed(), body }));
}

export function completeConsent(id: string, body: Schemas["ConsentCompleteRequest"]) {
  return unwrap(api.POST("/api/v1/insurance/consents/{id}/complete/", { params: { path: { id } }, headers: keyed(), body }));
}

export function rejectPending(coverageId: string) {
  return unwrap(
    api.POST("/api/v1/insurance/coverages/{id}/pending-authorisations/reject/", {
      params: { path: { id: coverageId } },
      headers: keyed(),
    }),
  );
}

/** Payers whose visit needs the member's consent step, and how. */
export function consentMethodOf(gateway: string): "otp" | "card_or_code" | null {
  if (gateway === "sha_hie" || gateway === "sha_fhir") return "otp";
  if (gateway === "smart") return "card_or_code";
  return null;
}

export type SlotStatus = "not_applicable" | "pending" | "verified" | "failed";

export function slotStatus(check: EligibilityCheck | null | undefined): SlotStatus {
  if (!check) return "pending";
  if (check.status === "eligible") return "verified";
  if (check.status === "pending_verification") return "pending";
  return "failed";
}
