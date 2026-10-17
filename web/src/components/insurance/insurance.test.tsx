import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/lib/api/client";

import { consentMethodOf, idempotencyKey, slotStatus } from "./api";
import { PayerEligibility } from "./payer-eligibility";

const COVER = {
  id: "c0000000-0000-7000-8000-000000000001",
  patient: "p0000000-0000-7000-8000-000000000001",
  scheme: { id: "s1", code: "shif", name: "Social Health Insurance Fund (SHIF)", kind: "shif", payer: { id: "p1", code: "sha", name: "Social Health Authority (SHA)", kind: "sha", gateway: "sha_hie" } },
  member_number: "SHA-****0016",
  relationship: "principal",
  valid_from: null,
  valid_to: null,
  verification: "unverified",
  verified_at: null,
  active: true,
  current: true,
  version: 1,
};

const ELIGIBLE = {
  id: "e1",
  coverage: COVER.id,
  status: "eligible",
  message: "Eligible.",
  checked_on: "2026-10-17",
  checked_at: "2026-10-17T07:00:00Z",
  gateway: "sha_hie",
  mode: "fake",
  schemes: [],
  otp_allowed: true,
  biometrics_enforced: false,
  verification: "verified",
};

const BENEFIT = {
  code: "SYN-SHA-OP-001",
  name: "Synthetic outpatient consultation",
  fund: "SHIF",
  sub_benefit_code: "",
  access_point: "OP",
  payment_mechanism: "FEE_FOR_SERVICE",
  needs_preauth: false,
  needs_manual_preauth_approval: false,
  needs_doctor_authorization: false,
  tariff: "1500.00",
};

type Answer = { status?: number; body: unknown };
type Call = { method: string; path: string; init: Record<string, unknown> };

/** Answer typed-client calls by method + path (the API client is the component's boundary). */
function serve(routes: Record<string, Answer | Answer[]>) {
  const calls: Call[] = [];
  const answer = (method: string) => async (path: string, init: Record<string, unknown> = {}) => {
    calls.push({ method, path, init });
    const entry = routes[`${method} ${path}`];
    const next = Array.isArray(entry) ? (entry.length > 1 ? entry.shift() : entry[0]) : entry;
    const { status = 200, body } = next ?? { status: 500, body: { detail: "no route" } };
    const ok = status < 400;
    return { data: ok ? body : undefined, error: ok ? undefined : body, response: new Response(null, { status: status === 204 ? 204 : status }) };
  };
  vi.spyOn(api, "GET").mockImplementation(answer("GET") as never);
  vi.spyOn(api, "POST").mockImplementation(answer("POST") as never);
  return calls;
}

function wrap(children: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

afterEach(() => vi.restoreAllMocks());

describe("insurance helpers", () => {
  it("maps snapshots to slot statuses and payers to consent methods", () => {
    expect(slotStatus(null)).toBe("pending");
    expect(slotStatus({ ...ELIGIBLE } as never)).toBe("verified");
    expect(slotStatus({ ...ELIGIBLE, status: "pending_verification" } as never)).toBe("pending");
    expect(slotStatus({ ...ELIGIBLE, status: "inactive" } as never)).toBe("failed");
    expect(consentMethodOf("sha_hie")).toBe("otp");
    expect(consentMethodOf("smart")).toBe("card_or_code");
    expect(consentMethodOf("slade360")).toBeNull();
    expect(idempotencyKey()).not.toBe(idempotencyKey());
  });
});

describe("PayerEligibility (slot W1)", () => {
  it("renders nothing and reports not_applicable for cash", () => {
    const onStatus = vi.fn();
    const { container } = render(wrap(<PayerEligibility patientId="p" coverageId={null} onStatusChange={onStatus} />));
    expect(container).toBeEmptyDOMElement();
    expect(onStatus).toHaveBeenCalledWith("not_applicable");
  });

  it("checks eligibility with an idempotency key and reports the result", async () => {
    const calls = serve({
      "GET /api/v1/insurance/coverages/": { body: [COVER] },
      "GET /api/v1/insurance/coverages/{id}/eligibility/": { status: 404, body: { detail: "This cover has not been checked yet.", code: "not_found" } },
      "POST /api/v1/insurance/coverages/{id}/eligibility/": { status: 201, body: { ...ELIGIBLE, status: "inactive", message: "Contributions in arrears.", verification: "failed" } },
    });
    const onStatus = vi.fn();
    render(wrap(<PayerEligibility patientId={COVER.patient} coverageId={COVER.id} onStatusChange={onStatus} />));
    expect(await screen.findByText("Not checked")).toBeInTheDocument();
    expect(await screen.findByText("Social Health Authority (SHA) — Social Health Insurance Fund (SHIF)")).toBeInTheDocument();
    await waitFor(() => expect(onStatus).toHaveBeenLastCalledWith("pending"));
    await userEvent.click(screen.getByRole("button", { name: "Check eligibility" }));
    expect(await screen.findByText("Cover inactive")).toBeInTheDocument();
    expect(screen.getByText(/Contributions in arrears/)).toBeInTheDocument();
    await waitFor(() => expect(onStatus).toHaveBeenLastCalledWith("failed"));
    const post = calls.find((c) => c.method === "POST");
    expect((post?.init.headers as Record<string, string>)["Idempotency-Key"]).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("says when the payer did not answer, without blocking", async () => {
    serve({
      "GET /api/v1/insurance/coverages/": { body: [COVER] },
      "GET /api/v1/insurance/coverages/{id}/eligibility/": { body: { ...ELIGIBLE, status: "pending_verification", message: "The payer is not answering." } },
    });
    const onStatus = vi.fn();
    render(wrap(<PayerEligibility patientId={COVER.patient} coverageId={COVER.id} onStatusChange={onStatus} />));
    expect(await screen.findByText("The payer did not answer")).toBeInTheDocument();
    await waitFor(() => expect(onStatus).toHaveBeenLastCalledWith("pending"));
  });

  it("takes SHA consent by SMS code after the member confirms the phone", async () => {
    const consent = { id: "k1", coverage: COVER.id, visit_id: null, gateway: "sha_hie", method: "otp", status: "otp_sent", service_type: "outpatient", service_codes: ["SYN-SHA-OP-001"], reason: "", attempts: 0, expires_at: null, authorized_at: null, has_token: false, version: 1 };
    const calls = serve({
      "GET /api/v1/insurance/coverages/": { body: [COVER] },
      "GET /api/v1/insurance/coverages/{id}/eligibility/": { body: ELIGIBLE },
      "GET /api/v1/insurance/coverages/{id}/benefits/": { body: [BENEFIT] },
      "POST /api/v1/insurance/consents/": [
        { body: { status: "choose_contact", consent: null, contacts: [{ contact_id: "1", masked: "+254700***001", confirmed: true }], capture_url: "", reason: "", otp_fallback: false } },
        { status: 201, body: { status: "otp_sent", consent, contacts: [], capture_url: "", reason: "", otp_fallback: false } },
      ],
      "POST /api/v1/insurance/consents/{id}/complete/": { body: { ...consent, status: "visit_open", has_token: true } },
    });
    render(wrap(<PayerEligibility patientId={COVER.patient} coverageId={COVER.id} />));
    await userEvent.click(await screen.findByRole("button", { name: "Send SMS code" }));
    expect(await screen.findByText("Which phone should get the code?")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "+254700***001" })).toBeChecked();
    await userEvent.click(screen.getByRole("button", { name: "Send code" }));
    await userEvent.type(await screen.findByLabelText(/Code the member received/), "123456");
    await userEvent.click(screen.getByRole("button", { name: "Confirm consent" }));
    expect(await screen.findByText("Consent recorded for this visit")).toBeInTheDocument();
    const starts = calls.filter((c) => c.path === "/api/v1/insurance/consents/");
    expect(starts.map((c) => (c.init.body as { contact_id: string }).contact_id)).toEqual(["", "1"]);
    const complete = calls.find((c) => c.path.endsWith("/complete/"));
    expect(complete?.init.body).toEqual({ otp: "123456", member_code: "" });
    expect(document.body.innerHTML).not.toContain("123456");
  });

  it("offers to clear a stuck fingerprint request", async () => {
    serve({
      "GET /api/v1/insurance/coverages/": { body: [COVER] },
      "GET /api/v1/insurance/coverages/{id}/eligibility/": { body: ELIGIBLE },
      "GET /api/v1/insurance/coverages/{id}/benefits/": { body: [BENEFIT] },
      "POST /api/v1/insurance/consents/": { status: 409, body: { detail: "A fingerprint authorisation for this member is still pending with SHA.", code: "pending_authorisation" } },
      "POST /api/v1/insurance/coverages/{id}/pending-authorisations/reject/": { body: { pending: 0 } },
    });
    render(wrap(<PayerEligibility patientId={COVER.patient} coverageId={COVER.id} />));
    await userEvent.click(await screen.findByRole("button", { name: "Send SMS code" }));
    await userEvent.click(await screen.findByRole("button", { name: "Clear the pending fingerprint request" }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Clear the pending fingerprint request" })).toBeNull());
  });
});
