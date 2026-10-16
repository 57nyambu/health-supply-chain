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

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const signedIn = useSignedIn();
  const hydrated = useHydrated();
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);
  const next = params.get("next");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSaving(true);
    setError(undefined);
    try {
      const result = await send<Me | { status: "mfa_required" }>("/api/v1/auth/login", {
        method: "POST",
        body: { email: String(form.get("email") ?? ""), password: String(form.get("password") ?? "") },
      });
      if ("status" in result) router.replace(next ? `/mfa?next=${encodeURIComponent(next)}` : "/mfa");
      else signedIn(result, next);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? problemMessage(caught.problem)
          : "Cannot reach AfyaSync. Check the network and try again.",
      );
      setSaving(false);
    }
  }

  // method="post": even a submission before the page is ready never puts credentials in the URL.
  return (
    <form method="post" onSubmit={submit} noValidate className="flex flex-col gap-5">
      <h1 className="text-xl font-bold">Sign in</h1>
      {params.get("reason") === "signed-out" && <Callout tone="info" title="You have signed out." />}
      {error && <Callout tone="danger" title={error} />}
      <Field label="E-mail address" required>
        {(control) => <TextInput {...control} name="email" type="email" autoComplete="username" autoFocus />}
      </Field>
      <Field label="Password" required>
        {(control) => <TextInput {...control} name="password" type="password" autoComplete="current-password" />}
      </Field>
      <Button type="submit" loading={saving} loadingLabel="Signing in…" disabled={!hydrated}>
        Sign in
      </Button>
    </form>
  );
}
