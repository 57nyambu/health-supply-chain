"use client";

import { type FormEvent, useState } from "react";

import { ApiError, problemMessage } from "@/lib/api/client";

import { Button, type ButtonVariant } from "./button";
import { Dialog } from "./dialog";
import { Field, TextInput } from "./field";
import { Callout } from "./status";

type ReasonDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  label?: string;
  action: string;
  variant?: ButtonVariant;
  required?: boolean;
  onConfirm: (reason: string) => Promise<void>;
};

/** Ask for the reason an audited action needs (revoke, deactivate, reject, escalate…). */
export function ReasonDialog({
  open,
  onOpenChange,
  title,
  description,
  label = "Reason",
  action,
  variant = "primary",
  required = true,
  onConfirm,
}: ReasonDialogProps) {
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const reason = String(new FormData(event.currentTarget).get("reason") ?? "").trim();
    if (required && !reason) {
      setError(`Enter the ${label.toLowerCase()}.`);
      return;
    }
    setSaving(true);
    setError(undefined);
    try {
      await onConfirm(reason);
      onOpenChange(false);
    } catch (caught) {
      setError(caught instanceof ApiError ? problemMessage(caught.problem) : "Something went wrong. Try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange} title={title} description={description}>
      <form method="post" onSubmit={submit} noValidate className="flex flex-col gap-4">
        {error && <Callout tone="danger" title={error} />}
        <Field label={label} required={required}>
          {(control) => <TextInput {...control} name="reason" autoFocus maxLength={255} />}
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" variant={variant} loading={saving}>
            {action}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
