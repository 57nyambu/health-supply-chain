"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, TextInput } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { Callout, StatusPill, type Tone } from "@/components/ui/status";
import { ApiError, problemMessage } from "@/lib/api/client";
import { formatDateTime } from "@/lib/format";

import {
  benefitsOf,
  checkEligibility,
  completeConsent,
  type ConsentStep,
  consentMethodOf,
  coveragesOf,
  type EligibilityCheck,
  latestEligibility,
  type PayerConsent,
  rejectPending,
  slotStatus,
  startConsent,
} from "./api";

/**
 * Extension slot owned by the Phase 3 lane (ADR-024, docs/agent/lanes/SEAMS.md, W1).
 * The Phase 2 visit-opening form renders it under the payer choice: it shows the cover's
 * eligibility (checking with the payer on request) and, for SHA and SMART, takes the
 * member's consent for the visit. Emergencies never wait on it (ADR-013): it reports a
 * status and never blocks the form.
 */
export type PayerEligibilityProps = {
  patientId: string;
  /** The cover chosen for the visit; null for cash / self-pay. */
  coverageId: string | null;
  /** Phase 3 reports whether the visit may proceed under this cover (emergencies never wait). */
  onStatusChange?: (status: "not_applicable" | "pending" | "verified" | "failed") => void;
  /** Optional (Phase 3 addition): the visit type, so consent uses the right service type. */
  serviceType?: "outpatient" | "inpatient" | "capitation" | "emergency";
};

const STATUS: Record<EligibilityCheck["status"], { tone: Tone; label: string }> = {
  eligible: { tone: "success", label: "Eligible" },
  inactive: { tone: "warning", label: "Cover inactive" },
  not_eligible: { tone: "danger", label: "Not eligible" },
  not_found: { tone: "danger", label: "Member not found" },
  pending_verification: { tone: "warning", label: "Not verified yet" },
};

function message(caught: unknown, fallback: string) {
  return caught instanceof ApiError ? problemMessage(caught.problem, fallback) : fallback;
}

export function PayerEligibility({ patientId, coverageId, onStatusChange, serviceType = "outpatient" }: PayerEligibilityProps) {
  const client = useQueryClient();
  const covers = useQuery({
    queryKey: ["insurance", "coverages", patientId],
    queryFn: () => coveragesOf(patientId),
    enabled: Boolean(coverageId),
  });
  const latest = useQuery({
    queryKey: ["insurance", "eligibility", coverageId],
    queryFn: () => latestEligibility(coverageId as string),
    enabled: Boolean(coverageId),
  });
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string>();

  const status = coverageId ? slotStatus(latest.data) : "not_applicable";
  useEffect(() => {
    if (!coverageId || !latest.isFetched) {
      if (!coverageId) onStatusChange?.("not_applicable");
      return;
    }
    onStatusChange?.(status);
  }, [coverageId, latest.isFetched, status, onStatusChange]);

  if (!coverageId) return null;
  const cover = covers.data?.find((c) => c.id === coverageId);

  async function check() {
    setChecking(true);
    setError(undefined);
    try {
      const result = await checkEligibility(coverageId as string);
      client.setQueryData(["insurance", "eligibility", coverageId], result);
    } catch (caught) {
      setError(message(caught, "The eligibility check did not work. Try again."));
    } finally {
      setChecking(false);
    }
  }

  const check_ = latest.data;
  const shown = check_ ? STATUS[check_.status] : { tone: "neutral" as Tone, label: "Not checked" };
  const method = cover ? consentMethodOf(cover.scheme.payer.gateway) : null;
  return (
    <section aria-labelledby={`cover-${coverageId}`} className="flex flex-col gap-3 rounded-card border border-border bg-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 id={`cover-${coverageId}`} className="font-semibold text-ink">
            {cover ? `${cover.scheme.payer.name} — ${cover.scheme.name}` : "Insurance cover"}
          </h3>
          {cover && <p className="text-sm text-ink-muted">Member number {cover.member_number}</p>}
        </div>
        <StatusPill tone={shown.tone}>{shown.label}</StatusPill>
      </div>
      {check_ && (
        <p className="text-sm text-ink">
          {check_.message} <span className="text-ink-muted">Checked {formatDateTime(check_.checked_at)}.</span>
        </p>
      )}
      {check_?.status === "pending_verification" && (
        <Callout tone="warning" title="The payer did not answer">
          Carry on with the visit; the cover stays unverified until you check again.
        </Callout>
      )}
      {error && (
        <Callout tone="danger" title="Eligibility not checked">
          {error}
        </Callout>
      )}
      <div>
        <Button variant="secondary" onClick={check} loading={checking} loadingLabel="Checking…">
          {check_ ? "Check again" : "Check eligibility"}
        </Button>
      </div>
      {check_?.status === "eligible" && method && (
        <VisitConsent
          coverageId={coverageId}
          method={method}
          otpAllowed={check_.otp_allowed}
          serviceType={serviceType}
        />
      )}
    </section>
  );
}

function VisitConsent({
  coverageId,
  method,
  otpAllowed,
  serviceType,
}: {
  coverageId: string;
  method: "otp" | "card_or_code";
  otpAllowed: boolean;
  serviceType: NonNullable<PayerEligibilityProps["serviceType"]>;
}) {
  const benefits = useQuery({
    queryKey: ["insurance", "benefits", coverageId],
    queryFn: () => benefitsOf(coverageId),
  });
  const options = (benefits.data ?? []).map((b) => ({ value: b.code, label: b.name, code: b.code }));
  const [code, setCode] = useState<string>();
  const [step, setStep] = useState<ConsentStep>();
  const [contact, setContact] = useState<string>();
  const [done, setDone] = useState<PayerConsent>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [blocked, setBlocked] = useState(false);
  const chosen = code ?? options[0]?.value;
  const codes = chosen ? [chosen] : [];

  async function run(action: () => Promise<void>, fallback: string) {
    setBusy(true);
    setError(undefined);
    try {
      await action();
    } catch (caught) {
      if (caught instanceof ApiError && caught.problem.code === "pending_authorisation") setBlocked(true);
      setError(message(caught, fallback));
    } finally {
      setBusy(false);
    }
  }

  const start = (contactId = "") =>
    run(async () => {
      const next = await startConsent({ coverage: coverageId, service_type: serviceType, codes, method, contact_id: contactId });
      setStep(next);
      const [only] = next.contacts;
      if (next.status === "choose_contact" && next.contacts.length === 1 && only) setContact(only.contact_id);
    }, "The payer did not take the request. Try again.");

  function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = String(new FormData(event.currentTarget).get("proof") ?? "").trim();
    if (!value) {
      setError(method === "otp" ? "Enter the code the member received." : "Enter the member's code.");
      return;
    }
    const id = step?.consent?.id;
    if (!id) return;
    void run(async () => {
      setDone(await completeConsent(id, method === "otp" ? { otp: value, member_code: "" } : { otp: "", member_code: value }));
    }, "The payer did not confirm the consent. Try again.");
  }

  if (done) {
    return (
      <Callout tone="success" title="Consent recorded for this visit">
        The payer opened the visit{done.service_codes.length ? ` for ${done.service_codes.join(", ")}` : ""}.
      </Callout>
    );
  }
  if (method === "otp" && !otpAllowed) {
    return (
      <Callout tone="info" title="This facility must use fingerprints">
        SHA requires fingerprint consent here. Use the fingerprint workstation.
      </Callout>
    );
  }
  const waitingForProof = step?.consent && ["otp_sent", "awaiting_code"].includes(step.consent.status);
  return (
    <div className="flex flex-col gap-3 border-t border-border pt-3">
      <h4 className="font-semibold text-ink">Visit consent</h4>
      {error && (
        <Callout tone="danger" title="Consent not recorded">
          {error}
        </Callout>
      )}
      {blocked && (
        <Button
          variant="secondary"
          onClick={() =>
            run(async () => {
              await rejectPending(coverageId);
              setBlocked(false);
            }, "The pending authorisation was not cleared.")
          }
        >
          Clear the pending fingerprint request
        </Button>
      )}
      {!step && (
        <Field label="Service for this visit" hint="The payer's benefit the visit opens with.">
          {(control) => (
            <Select {...control} value={chosen} onValueChange={setCode} options={options} disabled={!options.length} />
          )}
        </Field>
      )}
      {method === "otp" && !step && (
        <>
          <div>
            <Button onClick={() => start()} loading={busy} loadingLabel="Asking SHA…" disabled={!chosen}>
              Send SMS code
            </Button>
          </div>
        </>
      )}
      {method === "card_or_code" && !step && (
        <div>
          <Button onClick={() => start()} loading={busy} loadingLabel="Starting…" disabled={!chosen}>
            Enter member code
          </Button>
        </div>
      )}
      {step?.status === "choose_contact" && (
        <fieldset className="flex flex-col gap-2">
          <legend className="font-semibold text-ink">Which phone should get the code?</legend>
          <p className="text-sm text-ink-muted">Confirm the number with the member.</p>
          {step.contacts.map((c) => (
            <label key={c.contact_id} className="flex items-center gap-2 text-ink">
              <input
                type="radio"
                name="contact"
                value={c.contact_id}
                checked={contact === c.contact_id}
                onChange={() => setContact(c.contact_id)}
              />
              {c.masked}
            </label>
          ))}
          <div>
            <Button onClick={() => start(contact)} loading={busy} loadingLabel="Sending…" disabled={!contact}>
              Send code
            </Button>
          </div>
        </fieldset>
      )}
      {waitingForProof && (
        <form onSubmit={confirm} className="flex flex-col gap-3" noValidate>
          <Field label={method === "otp" ? "Code the member received" : "Member code"} required>
            {(control) => <TextInput {...control} name="proof" inputMode="numeric" autoComplete="one-time-code" />}
          </Field>
          <div className="flex gap-2">
            <Button type="submit" loading={busy} loadingLabel="Confirming…">
              Confirm consent
            </Button>
            {method === "otp" && (
              <Button variant="quiet" onClick={() => setStep(undefined)}>
                Send a new code
              </Button>
            )}
          </div>
        </form>
      )}
    </div>
  );
}
