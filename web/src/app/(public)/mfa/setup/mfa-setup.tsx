"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, TextInput } from "@/components/ui/field";
import { Callout } from "@/components/ui/status";
import { ApiError, problemMessage, send } from "@/lib/api/client";
import type { Me } from "@/lib/auth/me";
import { destination, ME_KEY } from "@/lib/auth/session";

type Setup = { otpauth_uri: string; secret: string };

const failure = (caught: unknown) =>
  caught instanceof ApiError ? problemMessage(caught.problem) : "Cannot reach AfyaSync. Try again.";

/** Enrol an authenticator app (TOTP), then show the one-time recovery codes. */
export function MfaSetup() {
  const router = useRouter();
  const client = useQueryClient();
  const started = useRef(false);
  const [setup, setSetup] = useState<Setup>();
  const [codes, setCodes] = useState<string[]>();
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (started.current) return; // React strict mode runs effects twice in development
    started.current = true;
    send<Setup>("/api/v1/auth/mfa/totp/setup", { method: "POST" })
      .then(setSetup)
      .catch((caught) => setError(failure(caught)));
  }, []);

  async function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const code = String(new FormData(event.currentTarget).get("code") ?? "");
    setSaving(true);
    setError(undefined);
    try {
      const result = await send<{ recovery_codes: string[] }>("/api/v1/auth/mfa/totp/confirm", {
        method: "POST",
        body: { code: code.trim() },
      });
      setCodes(result.recovery_codes);
    } catch (caught) {
      setError(failure(caught));
    } finally {
      setSaving(false);
    }
  }

  async function finish() {
    const me = await send<Me>("/api/v1/me");
    client.setQueryData(ME_KEY, me);
    router.replace(destination(me));
  }

  if (codes) {
    return (
      <div className="flex flex-col gap-5">
        <h1 className="text-xl font-bold">Save your recovery codes</h1>
        <Callout tone="warning" title="Each code works once, and they are shown only now.">
          Print them or write them down and keep them somewhere safe. They let you sign in if you lose your phone.
        </Callout>
        <ol aria-label="Recovery codes" className="tabular grid grid-cols-2 gap-2 border border-border-strong bg-surface-sunken p-4 font-semibold">
          {codes.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ol>
        <div className="flex flex-wrap gap-3">
          <Button variant="secondary" onClick={() => window.print()}>
            Print codes
          </Button>
          <Button autoFocus onClick={finish}>
            I have saved them, continue
          </Button>
        </div>
      </div>
    );
  }

  return (
    <form method="post" onSubmit={confirm} noValidate className="flex flex-col gap-5">
      <h1 className="text-xl font-bold">Set up two-step sign-in</h1>
      <p className="text-ink-muted">
        Your role needs a second step when you sign in. Add AfyaSync to an authenticator app on your phone, then
        enter the code it shows.
      </p>
      {error && <Callout tone="danger" title={error} />}
      {setup && (
        <div className="flex flex-col gap-2">
          <p className="font-semibold">Setup key</p>
          <p
            data-testid="totp-secret"
            className="tabular border border-border-strong bg-surface-sunken p-3 text-lg font-semibold tracking-wider break-all"
          >
            {setup.secret.match(/.{1,4}/g)?.join(" ")}
          </p>
          <a className="text-primary underline" href={setup.otpauth_uri}>
            Open in an authenticator app on this device
          </a>
        </div>
      )}
      <Field label="6-digit code" required>
        {(control) => (
          <TextInput
            {...control}
            autoFocus
            autoComplete="one-time-code"
            inputMode="numeric"
            maxLength={6}
            name="code"
            className="tabular"
          />
        )}
      </Field>
      <Button type="submit" loading={saving} loadingLabel="Checking…" disabled={!setup}>
        Turn on two-step sign-in
      </Button>
    </form>
  );
}
