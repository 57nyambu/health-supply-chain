"use client";

import { useQuery } from "@tanstack/react-query";
import { DoorOpen, Siren } from "lucide-react";
import { type FormEvent, useEffect, useRef, useState } from "react";

import { PayerEligibility } from "@/components/insurance/payer-eligibility";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { Callout, StatusPill } from "@/components/ui/status";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, problemMessage } from "@/lib/api/client";
import { rows, type Schemas, unwrap } from "@/lib/api/query";
import { formatTime } from "@/lib/format";
import { PAYER_TYPE_LABEL, STATUS_LABEL, statusTone, VISIT_TYPE_LABEL, VISIT_TYPES } from "@/lib/visits";

export type Visit = Schemas["Visit"];

const CASH = "cash";
const FIRST_KIND: Record<string, string> = {
  opd: "triage",
  emergency: "emergency",
  walk_in_pharmacy: "pharmacy",
  walk_in_lab: "lab",
};

/** The patient's open visit, or the form that opens one (DESIGN-SYSTEM §6.2). Alt+N opens. */
export function VisitPanel({
  patientId,
  visit,
  canOpen,
  onOpened,
}: {
  patientId: string;
  visit: Visit | null | undefined;
  canOpen: boolean;
  onOpened: (visit: Visit) => Promise<unknown>;
}) {
  if (visit) return <OpenVisit visit={visit} />;
  if (!canOpen) {
    return (
      <section aria-labelledby="visit-heading" className="flex flex-col gap-2 border border-border-strong bg-surface p-4">
        <h2 id="visit-heading" className="text-lg font-bold">
          Visit
        </h2>
        <p className="text-ink-muted">No open visit. Reception opens visits.</p>
      </section>
    );
  }
  return <OpenVisitForm patientId={patientId} onOpened={onOpened} />;
}

function OpenVisit({ visit }: { visit: Visit }) {
  const detail = useQuery({
    queryKey: ["visit", visit.id, "detail"],
    queryFn: () => unwrap(api.GET("/api/v1/visits/{id}/", { params: { path: { id: visit.id }, query: { purpose: "care" } } })),
  });
  const tickets = (detail.data?.tickets ?? []).filter((t) => ["waiting", "called", "serving"].includes(t.status));
  return (
    <section aria-labelledby="visit-heading" className="flex flex-col gap-3 border border-border-strong bg-surface p-4">
      <div className="flex flex-wrap items-center gap-2">
        <h2 id="visit-heading" className="mr-auto text-lg font-bold">
          Visit <span className="tabular">{visit.number}</span>
        </h2>
        {visit.visit_type === "emergency" && (
          <span className="inline-flex items-center gap-1 rounded-control bg-triage-red px-2 py-0.5 text-sm font-semibold text-triage-red-text">
            <Siren aria-hidden className="size-4" />
            Emergency
          </span>
        )}
        <StatusPill tone={statusTone(visit.status)}>{STATUS_LABEL[visit.status] ?? visit.status}</StatusPill>
      </div>
      <dl className="grid grid-cols-[10rem_1fr] gap-x-4 gap-y-1">
        <dt className="text-ink-muted">Type</dt>
        <dd>{VISIT_TYPE_LABEL[visit.visit_type] ?? visit.visit_type}</dd>
        <dt className="text-ink-muted">Payer</dt>
        <dd>{visit.scheme_name ?? PAYER_TYPE_LABEL[visit.payer_type] ?? visit.payer_type}</dd>
        <dt className="text-ink-muted">Opened</dt>
        <dd className="tabular">{formatTime(visit.opened_at)}</dd>
      </dl>
      {tickets.length > 0 && (
        <ul aria-label="Queue tickets" className="flex flex-col divide-y divide-border-subtle border border-border-subtle">
          {tickets.map((t) => (
            <li key={t.id} className="flex flex-wrap items-center gap-3 px-3 py-2">
              <span className="tabular text-lg font-bold">{t.number}</span>
              <span>{t.service_point_name}</span>
              <StatusPill tone={t.status === "waiting" ? "warning" : "info"}>
                {t.status === "waiting" ? "Waiting" : t.status === "called" ? `Called to ${t.room}` : "Being seen"}
              </StatusPill>
            </li>
          ))}
        </ul>
      )}
      {detail.data?.gate_overrides.length ? (
        <p className="text-sm text-ink-muted">
          Payment gate overridden: {detail.data.gate_overrides.map((o) => o.context).join(", ")} (shown on the bill)
        </p>
      ) : null}
    </section>
  );
}

function OpenVisitForm({ patientId, onOpened }: { patientId: string; onOpened: (visit: Visit) => Promise<unknown> }) {
  const toast = useToast();
  const [visitType, setVisitType] = useState("opd");
  const [point, setPoint] = useState<string>();
  const [payer, setPayer] = useState(CASH);
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);
  const submitRef = useRef<HTMLButtonElement>(null);
  const points = useQuery({
    queryKey: ["service-points"],
    queryFn: () => unwrap(api.GET("/api/v1/facilities/service-points/")),
  });
  const coverages = useQuery({
    queryKey: ["patient", patientId, "coverages"],
    queryFn: () =>
      unwrap(api.GET("/api/v1/insurance/coverages/", { params: { query: { patient: patientId, purpose: "registration" } } })),
  });
  const current = rows(coverages.data).filter((c) => c.current);
  const allPoints = rows(points.data).filter((p) => p.active);
  const firstKind = FIRST_KIND[visitType];
  const suggested = allPoints.filter((p) => p.kind === firstKind);
  const pointOptions = (suggested.length ? suggested : allPoints).map((p) => ({ value: String(p.id), label: p.name }));

  // Alt+N focuses "Open visit" (DESIGN-SYSTEM §8).
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.altKey && event.code === "KeyN") {
        event.preventDefault();
        submitRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(undefined);
    try {
      const opened = await unwrap(
        api.POST("/api/v1/visits/", {
          body: {
            patient: patientId,
            visit_type: visitType as Schemas["VisitOpenRequest"]["visit_type"],
            coverage: payer === CASH ? null : payer,
            service_point: point ? Number(point) : null,
            waiver: false,
            arrival_mode: "walk_in",
            brought_by: "",
          },
        }),
      );
      toast({ title: `Visit opened — ticket for ${opened.number}`, tone: "success" });
      await onOpened(opened);
    } catch (caught) {
      setError(caught instanceof ApiError ? problemMessage(caught.problem) : "The visit could not be opened. Try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section aria-labelledby="visit-heading" className="flex flex-col gap-3 border border-border-strong bg-surface p-4">
      <h2 id="visit-heading" className="text-lg font-bold">
        Open a visit
      </h2>
      {error && <Callout tone="danger" title={error} />}
      <form method="post" onSubmit={submit} noValidate className="grid gap-3 md:grid-cols-3 md:items-end">
        <Field label="Visit type" required>
          {(control) => (
            <Select
              {...control}
              value={visitType}
              onValueChange={(value) => {
                setVisitType(value);
                setPoint(undefined);
              }}
              options={VISIT_TYPES}
            />
          )}
        </Field>
        <Field label="Service point" hint={`Default: the first ${firstKind?.replace("_", " ")} point`}>
          {(control) => <Select {...control} value={point} onValueChange={setPoint} options={pointOptions} placeholder="Default" />}
        </Field>
        <Field label="Payer" hint={visitType === "emergency" ? "Emergency care never waits for cover checks." : undefined}>
          {(control) => (
            <Select
              {...control}
              value={payer}
              onValueChange={setPayer}
              options={[
                { value: CASH, label: "Cash / self-pay" },
                ...current.map((c) => ({ value: c.id, label: `${c.scheme.name} (${c.member_number})` })),
              ]}
            />
          )}
        </Field>
        <div className="md:col-span-3">
          <PayerEligibility patientId={patientId} coverageId={payer === CASH ? null : payer} />
        </div>
        <div className="md:col-span-3">
          <Button ref={submitRef} type="submit" variant={visitType === "emergency" ? "danger" : "primary"} loading={saving} loadingLabel="Opening…">
            <DoorOpen aria-hidden className="size-4" />
            Open visit
          </Button>
          <span className="ml-3 text-sm text-ink-muted">Alt+N</span>
        </div>
      </form>
    </section>
  );
}
