"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, TextInput } from "@/components/ui/field";
import { Callout } from "@/components/ui/status";
import { ApiError, problemMessage, send } from "@/lib/api/client";
import type { Me } from "@/lib/auth/me";
import { destination, ME_KEY } from "@/lib/auth/session";

/** Required after an administrator resets the account; also reachable from the account menu. */
export default function PasswordPage() {
  const router = useRouter();
  const client = useQueryClient();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (next !== repeat) {
      setError("The new passwords do not match.");
      return;
    }
    setSaving(true);
    setError(undefined);
    try {
      await send("/api/v1/auth/password", { method: "POST", body: { current_password: current, new_password: next } });
      const me = await send<Me>("/api/v1/me");
      client.setQueryData(ME_KEY, me);
      router.replace(destination(me));
    } catch (caught) {
      setError(caught instanceof ApiError ? problemMessage(caught.problem) : "Cannot reach AfyaSync. Try again.");
      setSaving(false);
    }
  }

  return (
    <form method="post" onSubmit={submit} noValidate className="flex flex-col gap-5">
      <h1 className="text-xl font-bold">Choose a new password</h1>
      <p className="text-ink-muted">At least 12 characters. A short sentence you can remember works well.</p>
      {error && <Callout tone="danger" title={error} />}
      <Field label="Current password" required>
        {(control) => (
          <TextInput {...control} type="password" autoComplete="current-password" autoFocus value={current} onChange={(e) => setCurrent(e.target.value)} />
        )}
      </Field>
      <Field label="New password" required>
        {(control) => (
          <TextInput {...control} type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />
        )}
      </Field>
      <Field label="New password again" required>
        {(control) => (
          <TextInput {...control} type="password" autoComplete="new-password" value={repeat} onChange={(e) => setRepeat(e.target.value)} />
        )}
      </Field>
      <Button type="submit" loading={saving}>
        Change password
      </Button>
    </form>
  );
}
