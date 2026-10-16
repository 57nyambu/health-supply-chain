"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, TextInput } from "@/components/ui/field";
import { Callout } from "@/components/ui/status";
import { ApiError, problemMessage, send } from "@/lib/api/client";
import type { Me } from "@/lib/auth/me";
import { useSignedIn } from "@/lib/auth/session";
import { useHydrated } from "@/lib/use-hydrated";

export function MfaChallenge() {
  const router = useRouter();
  const params = useSearchParams();
  const signedIn = useSignedIn();
  const [recovery, setRecovery] = useState(false);
  const hydrated = useHydrated();
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = String(new FormData(event.currentTarget).get("code") ?? "");
    setSaving(true);
    setError(undefined);
    try {
      const me = await send<Me>("/api/v1/auth/mfa/verify", {
        method: "POST",
        body: recovery ? { recovery_code: value.trim() } : { code: value.trim() },
      });
      signedIn(me, params.get("next"));
    } catch (caught) {
      if (caught instanceof ApiError && caught.problem.code === "mfa_session_expired") {
        router.replace("/login");
        return;
      }
      setError(caught instanceof ApiError ? problemMessage(caught.problem) : "Cannot reach AfyaSync. Try again.");
      setSaving(false);
    }
  }

  return (
    <form method="post" onSubmit={submit} noValidate className="flex flex-col gap-5">
      <h1 className="text-xl font-bold">Enter your code</h1>
      <p className="text-ink-muted">
        {recovery
          ? "Enter one of your recovery codes. Each code works once."
          : "Open your authenticator app and enter the 6-digit code for AfyaSync."}
      </p>
      {error && <Callout tone="danger" title={error} />}
      <Field label={recovery ? "Recovery code" : "6-digit code"} required>
        {(control) => (
          <TextInput
            {...control}
            key={recovery ? "recovery" : "code"}
            autoFocus
            autoComplete="one-time-code"
            inputMode={recovery ? "text" : "numeric"}
            maxLength={recovery ? 20 : 6}
            name="code"
            className="tabular"
          />
        )}
      </Field>
      <Button type="submit" loading={saving} loadingLabel="Checking…" disabled={!hydrated}>
        Verify
      </Button>
      <Button
        variant="quiet"
        onClick={() => setRecovery(!recovery)}
      >
        {recovery ? "Use the authenticator app instead" : "Use a recovery code instead"}
      </Button>
    </form>
  );
}
