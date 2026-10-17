"use client";

/**
 * Extension slot owned by the Phase 3 lane (ADR-024, docs/agent/lanes/SEAMS.md, W2).
 * The Phase 2 cashier screen renders it next to cash and M-Pesa; Phase 3 fills it with bank
 * (Jenga, Buni) and card (Pesapal hosted page, PDQ) methods. Renders nothing until then.
 */
export type ExtraPaymentMethodsProps = {
  invoiceId: string;
  /** Amount due as the API's decimal string (never a float). */
  amountDue: string;
  /** Phase 3 calls this when a payment intent it started succeeds or fails. */
  onSettled?: (outcome: { intentId: string; status: "succeeded" | "failed" }) => void;
};

export function ExtraPaymentMethods(props: ExtraPaymentMethodsProps): null {
  void props;
  return null;
}
