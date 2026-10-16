"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { Field, TextInput } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { Callout, StatusPill } from "@/components/ui/status";
import { api } from "@/lib/api/client";
import { type Schemas, unwrap } from "@/lib/api/query";
import { formatDateTime, parseDate } from "@/lib/format";

type Event = Schemas["AuditEvent"];
type Filters = Partial<Record<"action" | "actor" | "patient" | "outcome" | "date_from" | "date_to", string>>;

const OUTCOMES = [
  { value: "any", label: "Any outcome" },
  { value: "success", label: "Success" },
  { value: "denied", label: "Denied" },
  { value: "failure", label: "Failure" },
];

function cursorOf(next: string | null | undefined): string | undefined {
  if (!next) return undefined;
  return new URL(next, "http://localhost").searchParams.get("cursor") ?? undefined;
}

/** Audit viewer for the DPO and auditors (DESIGN §7.11). Viewing the log is itself audited. */
export default function AuditPage() {
  const [filters, setFilters] = useState<Filters>({});
  const [outcome, setOutcome] = useState("any");
  const [error, setError] = useState<string>();
  const events = useInfiniteQuery({
    queryKey: ["admin", "audit", filters],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      unwrap(api.GET("/api/v1/audit/events/", { params: { query: { ...filters, cursor: pageParam } as never } })),
    getNextPageParam: (page) => cursorOf((page as { next?: string | null }).next),
  });
  const list = events.data?.pages.flatMap((page) => (page as { results: Event[] }).results) ?? [];

  function apply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const next: Filters = {};
    for (const name of ["action", "actor", "patient"] as const) {
      const value = String(form.get(name) ?? "").trim();
      if (value) next[name] = value;
    }
    for (const name of ["date_from", "date_to"] as const) {
      const value = String(form.get(name) ?? "").trim();
      if (!value) continue;
      const iso = parseDate(value);
      if (!iso) {
        setError("Enter dates as DD/MM/YYYY.");
        return;
      }
      next[name] = iso;
    }
    if (outcome !== "any") next.outcome = outcome;
    setError(undefined);
    setFilters(next);
  }

  return (
    <div className="flex flex-col gap-4">
      <form method="post" onSubmit={apply} noValidate className="grid gap-3 border border-border-subtle bg-surface p-4 md:grid-cols-3 lg:grid-cols-6 lg:items-start">
        <Field label="Action" hint="e.g. patients.* or patients.chart.opened">
          {(control) => <TextInput {...control} name="action" autoComplete="off" />}
        </Field>
        <Field label="User ID">{(control) => <TextInput {...control} name="actor" inputMode="numeric" autoComplete="off" />}</Field>
        <Field label="Patient ID">{(control) => <TextInput {...control} name="patient" autoComplete="off" />}</Field>
        <Field label="Outcome">{(control) => <Select {...control} value={outcome} onValueChange={setOutcome} options={OUTCOMES} />}</Field>
        <Field label="From" hint="DD/MM/YYYY">{(control) => <TextInput {...control} name="date_from" inputMode="numeric" autoComplete="off" />}</Field>
        <Field label="To" hint="DD/MM/YYYY">{(control) => <TextInput {...control} name="date_to" inputMode="numeric" autoComplete="off" />}</Field>
        <div className="flex gap-2 lg:col-span-6">
          <Button type="submit">Show events</Button>
        </div>
      </form>
      {error && <Callout tone="danger" title={error} />}
      {events.isError && <Callout tone="danger" title="Audit events could not be loaded. Check the filters." />}
      <DataTable
        caption="Audit events, newest first"
        density="compact"
        rows={list}
        rowKey={(e) => e.id}
        empty={events.isPending ? "Loading…" : "No events match these filters."}
        columns={[
          { key: "ts", header: "Time", cell: (e) => <span className="tabular whitespace-nowrap">{formatDateTime(e.ts)}</span> },
          { key: "action", header: "Action", cell: (e) => <code className="text-sm">{e.action}</code> },
          { key: "actor", header: "User", cell: (e) => (e.actor_id ? `#${e.actor_id}` : "System"), numeric: true },
          { key: "role", header: "Roles", cell: (e) => e.actor_role.split(",").join(", ") || "—" },
          { key: "resource", header: "Record", cell: (e) => (e.resource_type ? `${e.resource_type} ${e.resource_id.slice(0, 8)}` : "—") },
          { key: "patient", header: "Patient", cell: (e) => (e.patient_id ? e.patient_id.slice(0, 8) : "—") },
          { key: "purpose", header: "Purpose", cell: (e) => e.purpose || "—" },
          {
            key: "outcome",
            header: "Outcome",
            cell: (e) => (
              <StatusPill tone={e.outcome === "success" ? (e.severity === "high" ? "warning" : "neutral") : "danger"}>
                {e.outcome}
                {e.severity === "high" ? ", high" : ""}
              </StatusPill>
            ),
          },
        ]}
      />
      {events.hasNextPage && (
        <Button variant="secondary" className="self-start" loading={events.isFetchingNextPage} loadingLabel="Loading…" onClick={() => events.fetchNextPage()}>
          Load older events
        </Button>
      )}
    </div>
  );
}
