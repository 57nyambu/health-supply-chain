"use client";

import { ShieldAlert } from "lucide-react";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { controlClass, Field } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { Callout, StatusPill } from "@/components/ui/status";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, problemMessage } from "@/lib/api/client";
import { type Schemas, unwrap } from "@/lib/api/query";
import { formatDate, formatTime } from "@/lib/format";

type Item = { id?: string; label?: string; hidden?: string; [key: string]: unknown };
export type ChartSummary = { allergies: Item[]; alerts: Item[]; problems: Item[]; medications: Item[]; current_visit: unknown };
type ChartRecord = { notes: Item[]; diagnoses: Item[]; results: Item[]; documents: Item[] };

const LEVEL_TEXT: Record<string, string> = {
  none: "No access",
  demographics: "Registration details only",
  summary: "Summary",
  full: "Full record",
  sensitive: "Full record, including sensitive items",
};

const REASONS = [
  { value: "emergency", label: "Emergency" },
  { value: "continuity_of_care", label: "Continuity of care" },
  { value: "clinical_review", label: "Clinical review" },
];

/** The chart at the user's level (DESIGN §7.7); break-glass when care needs more (§7.8). */
export function ClinicalRecord({
  patientId,
  access,
  chart,
  error,
  loading,
  canBreakGlass,
  onChanged,
}: {
  patientId: string;
  access: Schemas["Access"];
  chart?: Schemas["Chart"];
  error: unknown;
  loading: boolean;
  canBreakGlass: boolean;
  onChanged: () => Promise<unknown>;
}) {
  const [asking, setAsking] = useState(false);
  const summary = (chart?.summary ?? null) as ChartSummary | null;
  const record = (chart?.record ?? null) as ChartRecord | null;
  const deniedProblem = error instanceof ApiError && error.problem.code === "chart_access_insufficient" ? error.problem : undefined;
  const mayBreakGlass =
    canBreakGlass && !access.break_glass && (access.break_glass_available || Boolean(deniedProblem?.break_glass_available)) && !record;

  return (
    <section aria-labelledby="clinical-heading" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <h2 id="clinical-heading" className="mr-auto text-lg font-bold">
          Clinical record
        </h2>
        <StatusPill tone={access.break_glass ? "danger" : record ? "success" : "neutral"}>{LEVEL_TEXT[access.level] ?? access.level}</StatusPill>
        {access.care_team && <StatusPill tone="success">On the care team</StatusPill>}
      </div>

      {loading && <p className="text-ink-muted">Loading the chart…</p>}
      {error && !deniedProblem ? <Callout tone="danger" title="The chart could not be loaded." /> : null}

      {!record && !loading && access.care_team && !deniedProblem && (
        <Callout tone="info" title="Your role shows the summary of this record." />
      )}
      {(deniedProblem || (!record && !loading && !access.care_team)) && (
        <Callout tone="info" title="You see the summary because you are not on this patient's care team.">
          Notes, results and documents open for the care team. In an emergency you can open the full record now; the
          access is time-limited, logged and reviewed.
          {mayBreakGlass && (
            <div className="mt-3">
              <Button variant="danger" onClick={() => setAsking(true)}>
                <ShieldAlert aria-hidden className="size-4" />
                Use emergency access
              </Button>
            </div>
          )}
        </Callout>
      )}

      {summary && (
        <div className="grid gap-4 md:grid-cols-2">
          <Items title="Allergies" items={summary.allergies} empty="Allergies not recorded yet." />
          <Items title="Alerts" items={summary.alerts} empty="No alerts." />
          <Items title="Problems" items={summary.problems} empty="No problems recorded." />
          <Items title="Current medicines" items={summary.medications} empty="No current medicines." />
        </div>
      )}

      {record && (
        <div className="grid gap-4 md:grid-cols-2">
          <Items title="Notes" items={record.notes} empty="No notes yet." />
          <Items title="Diagnoses" items={record.diagnoses} empty="No diagnoses yet." />
          <Items title="Results" items={record.results} empty="No results yet." />
          <Items
            title="Documents"
            items={record.documents.map((d) =>
              d.hidden ? d : { ...d, label: `${String(d.filename ?? "Document")} · ${formatDate(String(d.created_at ?? ""))}` },
            )}
            empty="No documents yet."
          />
        </div>
      )}

      {asking && <BreakGlassDialog patientId={patientId} onClose={() => setAsking(false)} onGranted={onChanged} />}
    </section>
  );
}

function Items({ title, items, empty }: { title: string; items: Item[]; empty: string }) {
  const hidden = items.filter((i) => i.hidden).length;
  const shown = items.filter((i) => !i.hidden);
  return (
    <div className="flex flex-col gap-2 border border-border-strong bg-surface p-4">
      <h3 className="font-bold">{title}</h3>
      {shown.length === 0 && hidden === 0 && <p className="text-ink-muted">{empty}</p>}
      {shown.length > 0 && (
        <ul className="flex flex-col gap-1">
          {shown.map((item, index) => (
            <li key={item.id ?? index}>{item.label ?? String(item.id ?? "")}</li>
          ))}
        </ul>
      )}
      {hidden > 0 && (
        <p className="text-sm text-ink-muted">
          {hidden} {hidden === 1 ? "item" : "items"} hidden — sensitive category
        </p>
      )}
    </div>
  );
}

function BreakGlassDialog({ patientId, onClose, onGranted }: { patientId: string; onClose: () => void; onGranted: () => Promise<unknown> }) {
  const toast = useToast();
  const [reason, setReason] = useState("emergency");
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const justification = String(new FormData(event.currentTarget).get("justification") ?? "").trim();
    if (justification.length < 10) {
      setError("Say why you need the full record now (at least a short sentence).");
      return;
    }
    setSaving(true);
    setError(undefined);
    try {
      const grant = await unwrap(
        api.POST("/api/v1/patients/{id}/break-glass/", {
          params: { path: { id: patientId } },
          body: { reason: reason as Schemas["BreakGlassRequestRequest"]["reason"], justification },
        }),
      );
      onClose();
      toast({ title: `Emergency access until ${formatTime(grant.expires_at)}`, tone: "info" });
      await onGranted();
    } catch (caught) {
      setError(caught instanceof ApiError ? problemMessage(caught.problem) : "Emergency access was not granted. Try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog
      open
      onOpenChange={(next) => !next && onClose()}
      title="Use emergency access"
      description="Opens the full record for a limited time. The medical superintendent and the data protection officer are told, and every view is reviewed."
    >
      <form method="post" onSubmit={submit} noValidate className="flex flex-col gap-4">
        {error && <Callout tone="danger" title={error} />}
        <Field label="Reason" required>
          {(control) => <Select {...control} value={reason} onValueChange={setReason} options={REASONS} />}
        </Field>
        <Field label="Why you need the full record now" required hint="Recorded and reviewed. Do not include other patients' details.">
          {(control) => <textarea {...control} name="justification" rows={3} maxLength={500} autoFocus className={controlClass(Boolean(control["aria-invalid"]), "h-24 py-2")} />}
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="danger" loading={saving}>
            Open the full record
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
