"use client";

import { useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, TextInput } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { Callout } from "@/components/ui/status";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, problemMessage } from "@/lib/api/client";
import { type Schemas, unwrap } from "@/lib/api/query";
import { GATE_CONTEXT_LABEL, GATE_LABEL, PAYER_TYPE_LABEL } from "@/lib/visits";

type Policy = Schemas["GatePolicy"];
type Change = Schemas["GatePolicyChangeRequest"];
const PAYERS = ["cash", "sha", "insurer", "corporate", "waiver"];
const CONTEXTS = Object.keys(GATE_CONTEXT_LABEL);

/** Payment gates per context and payer (DESIGN §6.4). Emergencies and discharge are never
 * gated and cannot be configured here (ADR-013, ADR-041). Changes need a second administrator. */
export default function GatesPage() {
  const policies = useQuery({ queryKey: ["visits", "gate-policies"], queryFn: () => unwrap(api.GET("/api/v1/visits/gate-policies/")) });
  const [editing, setEditing] = useState<{ context: string; payer: string; policy?: Policy } | null>(null);
  const cell = (context: string, payer: string) => policies.data?.find((p) => p.context === context && p.payer_type === payer);
  return (
    <div className="flex flex-col gap-4">
      <Callout tone="info" title="Emergency care and discharge are never held for payment.">
        No setting here can change that. Overrides by the medical superintendent or nurse in charge are recorded and shown on the bill.
      </Callout>
      {policies.isError && <Callout tone="danger" title="Gate policies could not be loaded." />}
      <div className="overflow-auto border border-border-strong bg-surface">
        <table className="w-full border-collapse text-left">
          <caption className="sr-only">Payment gate for each service and payer</caption>
          <thead className="bg-surface-sunken">
            <tr>
              <th scope="col" className="px-4 py-2.5 font-semibold">
                Service
              </th>
              {PAYERS.map((p) => (
                <th key={p} scope="col" className="px-4 py-2.5 font-semibold">
                  {PAYER_TYPE_LABEL[p]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {CONTEXTS.map((context) => (
              <tr key={context} className="border-t border-border-subtle">
                <th scope="row" className="px-4 py-2.5 font-semibold">
                  {GATE_CONTEXT_LABEL[context]}
                </th>
                {PAYERS.map((payer) => {
                  const policy = cell(context, payer);
                  return (
                    <td key={payer} className="px-4 py-2.5">
                      <button
                        type="button"
                        className="text-left text-primary hover:underline"
                        onClick={() => setEditing({ context, payer, policy })}
                        aria-label={`Change gate for ${GATE_CONTEXT_LABEL[context]}, ${PAYER_TYPE_LABEL[payer]}: ${policy ? GATE_LABEL[policy.gate] : "none"}`}
                      >
                        {policy ? GATE_LABEL[policy.gate] : "—"}
                        {policy?.condition === "if_flagged" && <span className="block text-sm text-ink-muted">only when flagged</span>}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {editing && <ChangeDialog {...editing} onClose={() => setEditing(null)} />}
    </div>
  );
}

function ChangeDialog({ context, payer, policy, onClose }: { context: string; payer: string; policy?: Policy; onClose: () => void }) {
  const toast = useToast();
  const [gate, setGate] = useState<string>(policy?.gate ?? "none");
  const [condition, setCondition] = useState<string>(policy?.condition ?? "always");
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const reason = String(new FormData(event.currentTarget).get("reason") ?? "").trim();
    if (!reason) return setError("Say why the gate changes.");
    setSaving(true);
    try {
      await unwrap(
        api.POST("/api/v1/visits/gate-policies/", {
          body: {
            context: context as Change["context"],
            payer_type: payer as Change["payer_type"],
            gate: gate as Change["gate"],
            condition: condition as Change["condition"],
            reason,
          },
        }),
      );
      toast({ title: "Gate change sent for approval", tone: "success" });
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
      title={`${GATE_CONTEXT_LABEL[context]} — ${PAYER_TYPE_LABEL[payer]}`}
      description="A second administrator approves the change under Approvals."
    >
      <form method="post" onSubmit={save} noValidate className="flex flex-col gap-4">
        {error && <Callout tone="danger" title={error} />}
        <Field label="Gate" required>
          {(control) => (
            <Select {...control} value={gate} onValueChange={setGate} options={Object.entries(GATE_LABEL).map(([value, label]) => ({ value, label }))} />
          )}
        </Field>
        <Field label="Applies">
          {(control) => (
            <Select
              {...control}
              value={condition}
              onValueChange={setCondition}
              options={[
                { value: "always", label: "Always" },
                { value: "if_flagged", label: "Only when the scheme or intervention flags it" },
              ]}
            />
          )}
        </Field>
        <Field label="Reason" required>
          {(control) => <TextInput {...control} name="reason" maxLength={255} />}
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            Send for approval
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
