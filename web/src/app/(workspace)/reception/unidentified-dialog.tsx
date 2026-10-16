"use client";

import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, TextInput } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { Callout } from "@/components/ui/status";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, problemMessage } from "@/lib/api/client";
import { type Schemas, unwrap } from "@/lib/api/query";
import { SEX_OPTIONS } from "@/lib/patients";

/** Emergency quick registration: a temporary ID now, identity later (DESIGN §6.6). Never gated. */
export function UnidentifiedDialog({
  open,
  onOpenChange,
  onRegistered,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRegistered: (id: string) => void;
}) {
  const toast = useToast();
  const [sex, setSex] = useState("unknown");
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const raw = String(new FormData(event.currentTarget).get("age") ?? "").trim();
    const age = raw ? Number(raw) : null;
    if (age !== null && (!Number.isInteger(age) || age < 0 || age > 130)) {
      setError("Enter the approximate age in whole years (0–130), or leave it empty.");
      return;
    }
    setSaving(true);
    setError(undefined);
    try {
      const created = await unwrap(
        api.POST("/api/v1/patients/unidentified/", {
          body: { sex: sex as Schemas["UnidentifiedRequest"]["sex"], approx_age_years: age },
        }),
      );
      const temporary = created.identifiers.find((i) => i.type === "temporary")?.value;
      toast({ title: `Unidentified patient registered${temporary ? ` — ${temporary}` : ""}`, tone: "success" });
      onOpenChange(false);
      onRegistered(created.id);
    } catch (caught) {
      setError(caught instanceof ApiError ? problemMessage(caught.problem) : "Could not register. Try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="Unidentified emergency patient"
      description="Registers now with a temporary ID so care can start. Add the name and IDs when known."
    >
      <form method="post" onSubmit={submit} noValidate className="flex flex-col gap-4">
        {error && <Callout tone="danger" title={error} />}
        <Field label="Sex" required>
          {(control) => <Select {...control} value={sex} onValueChange={setSex} options={SEX_OPTIONS} />}
        </Field>
        <Field label="Approximate age (years)" hint="Leave empty if you cannot tell.">
          {(control) => <TextInput {...control} name="age" inputMode="numeric" autoComplete="off" className="w-24 text-right" />}
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" variant="danger" loading={saving}>
            Register unidentified patient
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
