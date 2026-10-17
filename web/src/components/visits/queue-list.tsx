"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { BellRing, Megaphone } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { Callout, StatusPill, TriageTag, triageRail } from "@/components/ui/status";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, problemMessage } from "@/lib/api/client";
import { rows, type Schemas, unwrap } from "@/lib/api/query";
import { SEX_SHORT } from "@/lib/patients";
import { PAYER_TYPE_LABEL, PRIORITY_REASONS, triageLevel, waitText } from "@/lib/visits";

export type Ticket = Schemas["Ticket"];

type QueueListProps = {
  /** Service point whose queue this is. */
  pointId: number;
  /** Open the patient/work pane for a ticket (Enter on a row). */
  onOpen?: (ticket: Ticket) => void;
  /** The ticket currently open in the work pane. */
  selectedId?: string;
  density?: "comfortable" | "compact";
  /** Minutes after which a wait is highlighted (facility threshold). */
  overdueMinutes?: number;
};

const STATUS_TEXT: Record<string, string> = { waiting: "Waiting", called: "Called", serving: "Being seen" };

/** Ticket, name, age/sex, wait, triage rail, payer; "Call next" (Alt+C). DESIGN-SYSTEM §7 QueueList. */
export function QueueList({ pointId, onOpen, selectedId, density = "comfortable", overdueMinutes = 60 }: QueueListProps) {
  const client = useQueryClient();
  const toast = useToast();
  const [now, setNow] = useState(() => Date.now());
  const [transfer, setTransfer] = useState<{ ticket: Ticket; sendBack: boolean } | null>(null);
  const [priority, setPriority] = useState<Ticket | null>(null);
  const [busy, setBusy] = useState<string>();
  const callRef = useRef<HTMLButtonElement>(null);
  const key = ["queue", pointId];
  const queue = useQuery({
    queryKey: key,
    queryFn: () => unwrap(api.GET("/api/v1/visits/queues/{id}/", { params: { path: { id: pointId } } })),
    refetchInterval: 15_000,
  });
  const tickets = queue.data ?? [];

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 30_000);
    const onKey = (event: KeyboardEvent) => {
      if (event.altKey && event.code === "KeyC") {
        event.preventDefault();
        callRef.current?.click();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      clearInterval(timer);
      window.removeEventListener("keydown", onKey);
    };
  }, []);

  async function run(label: string, call: () => Promise<unknown>, done?: string) {
    setBusy(label);
    try {
      await call();
      if (done) toast({ title: done, tone: "success" });
      await client.invalidateQueries({ queryKey: key });
    } catch (caught) {
      toast({ title: caught instanceof ApiError ? problemMessage(caught.problem) : "That did not work. Try again.", tone: "danger" });
    } finally {
      setBusy(undefined);
    }
  }

  const callNext = () =>
    run("next", async () => {
      const { data, response } = await api.POST("/api/v1/visits/queues/{id}/call-next/", {
        params: { path: { id: pointId } },
        body: { room: "" },
      });
      if (response.status === 204) {
        toast({ title: "Nobody is waiting." });
        return;
      }
      if (!response.ok || !data) throw new ApiError(response.status, {});
      toast({ title: `Called ${data.number}`, tone: "success" });
      onOpen?.(data);
    });

  const ticketAction = (ticket: Ticket, action: "call" | "start" | "finish" | "skip", done: string) => {
    const params = { path: { id: ticket.id } };
    const call = () => {
      switch (action) {
        case "call":
          return unwrap(api.POST("/api/v1/visits/tickets/{id}/call/", { params, body: { room: ticket.room } }));
        case "start":
          return unwrap(api.POST("/api/v1/visits/tickets/{id}/start/", { params }));
        case "finish":
          return unwrap(api.POST("/api/v1/visits/tickets/{id}/finish/", { params }));
        case "skip":
          return unwrap(api.POST("/api/v1/visits/tickets/{id}/skip/", { params }));
      }
    };
    return run(`${action}-${ticket.id}`, call, done);
  };

  const waiting = tickets.filter((t) => t.status === "waiting").length;
  return (
    <section aria-label="Queue" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <Button ref={callRef} onClick={callNext} loading={busy === "next"} loadingLabel="Calling…" disabled={waiting === 0}>
          <Megaphone aria-hidden className="size-4" />
          Call next
        </Button>
        <span className="text-sm text-ink-muted">Alt+C · {waiting} waiting</span>
      </div>
      {queue.isError && <Callout tone="danger" title="The queue could not be loaded." />}
      <div className="overflow-auto border border-border-strong bg-surface">
        <table className="w-full border-collapse text-left">
          <caption className="sr-only">Patients in this queue, in the order they will be called</caption>
          <thead className="sticky top-0 bg-surface-sunken shadow-sticky">
            <tr>
              {["Ticket", "Patient", "Triage", "Payer", "Wait", "Status", "Actions"].map((h) => (
                <th key={h} scope="col" className={density === "compact" ? "px-3 py-1.5 font-semibold" : "px-4 py-2.5 font-semibold"}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tickets.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-ink-muted">
                  No patients waiting. New arrivals appear here when reception opens a visit.
                </td>
              </tr>
            ) : (
              tickets.map((t) => {
                const level = triageLevel(t.visit.triage_category);
                const minutes = (now - new Date(t.arrived_at).getTime()) / 60000;
                const overdue = t.status === "waiting" && minutes > overdueMinutes;
                const pad = density === "compact" ? "px-3 py-1.5" : "px-4 py-2.5";
                return (
                  <tr
                    key={t.id}
                    tabIndex={0}
                    aria-selected={onOpen ? t.id === selectedId : undefined}
                    style={level ? triageRail(level) : undefined}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && onOpen && event.target === event.currentTarget) onOpen(t);
                    }}
                    className={
                      t.id === selectedId
                        ? "border-t border-border-subtle bg-selected"
                        : overdue
                          ? "border-t border-border-subtle bg-warning-tint"
                          : "border-t border-border-subtle hover:bg-surface-hover"
                    }
                  >
                    <td className={`${pad} tabular font-bold whitespace-nowrap`}>{t.number}</td>
                    <td className={pad}>
                      {onOpen ? (
                        <button type="button" className="font-semibold text-primary hover:underline" onClick={() => onOpen(t)}>
                          {t.visit.patient.display_name}
                        </button>
                      ) : (
                        <span className="font-semibold">{t.visit.patient.display_name}</span>
                      )}
                      <span className="ml-2 text-ink-muted">
                        {SEX_SHORT[t.visit.patient.sex] ?? t.visit.patient.sex} {t.visit.patient.age ?? ""}
                      </span>
                      {t.visit.visit_type === "emergency" && <StatusPill tone="danger">Emergency</StatusPill>}
                      {t.priority_reason && <StatusPill tone="info">Priority</StatusPill>}
                      {t.note && <p className="text-sm text-ink-muted">Note: {t.note}</p>}
                    </td>
                    <td className={pad}>{level ? <TriageTag level={level} /> : <span className="text-ink-muted">Not triaged</span>}</td>
                    <td className={pad}>{t.visit.scheme_name ?? PAYER_TYPE_LABEL[t.visit.payer_type] ?? t.visit.payer_type}</td>
                    <td className={`${pad} tabular whitespace-nowrap`}>
                      {waitText(t.arrived_at, now)}
                      {overdue && <span className="sr-only"> (long wait)</span>}
                    </td>
                    <td className={pad}>
                      <StatusPill tone={t.status === "waiting" ? "warning" : "info"}>
                        {STATUS_TEXT[t.status] ?? t.status}
                        {t.status === "called" && t.call_count > 1 ? ` (${t.call_count}×)` : ""}
                      </StatusPill>
                      {t.lwbs_flagged_at && <StatusPill tone="danger">May have left</StatusPill>}
                    </td>
                    <td className={pad}>
                      <div className="flex flex-wrap gap-1">
                        {t.status !== "serving" && (
                          <Button density="compact" variant="secondary" onClick={() => ticketAction(t, "call", `Called ${t.number}`)}>
                            <BellRing aria-hidden className="size-4" />
                            {t.status === "called" ? "Recall" : "Call"}
                          </Button>
                        )}
                        {t.status === "called" && (
                          <>
                            <Button density="compact" onClick={() => ticketAction(t, "start", `${t.number} is being seen`)}>
                              Start
                            </Button>
                            <Button density="compact" variant="secondary" onClick={() => ticketAction(t, "skip", `${t.number} skipped`)}>
                              Skip
                            </Button>
                          </>
                        )}
                        {t.status === "serving" && (
                          <Button density="compact" variant="success" onClick={() => ticketAction(t, "finish", `${t.number} done`)}>
                            Done
                          </Button>
                        )}
                        <Button density="compact" variant="quiet" onClick={() => setTransfer({ ticket: t, sendBack: false })}>
                          Transfer
                        </Button>
                        <Button density="compact" variant="quiet" onClick={() => setTransfer({ ticket: t, sendBack: true })}>
                          Send back
                        </Button>
                        {!t.priority_reason && (
                          <Button density="compact" variant="quiet" onClick={() => setPriority(t)}>
                            Prioritise
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
      {transfer && (
        <TransferDialog
          ticket={transfer.ticket}
          sendBack={transfer.sendBack}
          excludePoint={pointId}
          onClose={() => setTransfer(null)}
          onDone={() => client.invalidateQueries({ queryKey: key })}
        />
      )}
      {priority && (
        <PriorityDialog ticket={priority} onClose={() => setPriority(null)} onDone={() => client.invalidateQueries({ queryKey: key })} />
      )}
    </section>
  );
}

function TransferDialog({
  ticket,
  sendBack,
  excludePoint,
  onClose,
  onDone,
}: {
  ticket: Ticket;
  sendBack: boolean;
  excludePoint: number;
  onClose: () => void;
  onDone: () => Promise<unknown>;
}) {
  const toast = useToast();
  const [to, setTo] = useState<string>();
  const [note, setNote] = useState("");
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);
  const points = useQuery({ queryKey: ["service-points"], queryFn: () => unwrap(api.GET("/api/v1/facilities/service-points/")) });
  const options = rows(points.data)
    .filter((p) => p.active && p.id !== excludePoint)
    .map((p) => ({ value: String(p.id), label: p.name }));

  async function save() {
    if (!to) return setError("Choose where the patient goes.");
    if (sendBack && !note.trim()) return setError("Add a note saying why the patient is sent back.");
    setSaving(true);
    try {
      await unwrap(
        api.POST(sendBack ? "/api/v1/visits/tickets/{id}/send-back/" : "/api/v1/visits/tickets/{id}/transfer/", {
          params: { path: { id: ticket.id } },
          body: { service_point: Number(to), note },
        }),
      );
      toast({ title: sendBack ? `${ticket.number} sent back` : `${ticket.number} transferred`, tone: "success" });
      await onDone();
      onClose();
    } catch (caught) {
      setError(caught instanceof ApiError ? problemMessage(caught.problem) : "That did not work. Try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => !open && onClose()}
      title={sendBack ? `Send ${ticket.number} back` : `Transfer ${ticket.number}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={save} loading={saving}>
            {sendBack ? "Send back" : "Transfer"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <Callout tone="danger" title={error} />}
        <Field label="Service point" required>
          {(control) => <Select {...control} value={to} onValueChange={setTo} options={options} />}
        </Field>
        <Field label="Note" required={sendBack} hint="Shown to the next service point. No more detail than needed.">
          {(control) => (
            <input
              {...control}
              value={note}
              maxLength={255}
              onChange={(e) => setNote(e.target.value)}
              className="h-10 rounded-control border border-border-strong bg-surface px-3"
            />
          )}
        </Field>
      </div>
    </Dialog>
  );
}

function PriorityDialog({ ticket, onClose, onDone }: { ticket: Ticket; onClose: () => void; onDone: () => Promise<unknown> }) {
  const toast = useToast();
  const [reason, setReason] = useState<string>();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>();

  async function save() {
    if (!reason) return setError("Choose a reason.");
    setSaving(true);
    try {
      await unwrap(
        api.POST("/api/v1/visits/tickets/{id}/prioritise/", {
          params: { path: { id: ticket.id } },
          body: { reason_code: reason as Schemas["PrioritiseRequest"]["reason_code"] },
        }),
      );
      toast({ title: `${ticket.number} prioritised`, tone: "success" });
      await onDone();
      onClose();
    } catch (caught) {
      setError(caught instanceof ApiError ? problemMessage(caught.problem) : "That did not work. Try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => !open && onClose()}
      title={`Prioritise ${ticket.number}`}
      description="Moves the patient ahead of others with the same triage colour. Recorded in the audit log."
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={save} loading={saving}>
            Prioritise
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <Callout tone="danger" title={error} />}
        <Field label="Reason" required>
          {(control) => <Select {...control} value={reason} onValueChange={setReason} options={PRIORITY_REASONS} />}
        </Field>
      </div>
    </Dialog>
  );
}
