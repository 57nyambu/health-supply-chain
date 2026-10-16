"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, TextInput } from "@/components/ui/field";
import { Callout } from "@/components/ui/status";
import { ApiError, problemMessage, send } from "@/lib/api/client";
import { displayName, type Me } from "@/lib/auth/me";
import { useMe, useSignedIn } from "@/lib/auth/session";
import { useHydrated } from "@/lib/use-hydrated";

const failure = (caught: unknown) =>
  caught instanceof ApiError ? problemMessage(caught.problem) : "Cannot reach AfyaSync. Try again.";

/** Shared workstation: unlock with your PIN, or let a colleague switch in with theirs (DESIGN §7.2). */
export function LockScreen() {
  const router = useRouter();
  const signedIn = useSignedIn();
  const { data: me, error: meError } = useMe();
  const [mode, setMode] = useState<"unlock" | "switch">("unlock");
  const hydrated = useHydrated();
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);

  async function passwordInstead() {
    await send("/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
    router.replace("/login");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const pin = String(form.get("pin") ?? "");
    const email = String(form.get("email") ?? "");
    setSaving(true);
    setError(undefined);
    try {
      const result =
        mode === "unlock"
          ? await send<Me>("/api/v1/auth/unlock", { method: "POST", body: { pin } })
          : await send<Me>("/api/v1/auth/switch", { method: "POST", body: { email, pin } });
      signedIn(result);
    } catch (caught) {
      if (caught instanceof ApiError && caught.problem.code === "full_login_required" && mode === "unlock") {
        await passwordInstead();
        return;
      }
      setError(failure(caught));
      const pinField = formElement.elements.namedItem("pin") as HTMLInputElement | null;
      if (pinField) {
        pinField.value = "";
        pinField.focus();
      }
      setSaving(false);
    }
  }

  const signedOut = Boolean(meError);
  const switching = mode === "switch" || signedOut;
  return (
    <form method="post" onSubmit={submit} noValidate className="flex flex-col gap-5">
      <h1 className="text-xl font-bold">Workstation locked</h1>
      {me && !switching && (
        <p className="text-ink">
          Signed in as <span className="font-semibold">{displayName(me)}</span>. Enter your PIN to continue.
        </p>
      )}
      {switching && <p className="text-ink">Another member of staff can sign in here with their e-mail address and PIN.</p>}
      {me && !me.workstation.pin_set && !switching && (
        <Callout tone="info" title="You have no PIN yet.">
          Sign in with your password, then set a PIN from your account menu.
        </Callout>
      )}
      {error && <Callout tone="danger" title={error} />}
      {switching && (
        <Field label="E-mail address" required>
          {(control) => (
            <TextInput {...control} name="email" type="email" autoComplete="username" autoFocus />
          )}
        </Field>
      )}
      <Field label="PIN" required hint="6 digits">
        {(control) => (
          <TextInput
            {...control}
            key={mode}
            type="password"
            inputMode="numeric"
            autoComplete="off"
            maxLength={6}
            autoFocus={!switching}
            name="pin"
            className="tabular"
          />
        )}
      </Field>
      <Button type="submit" loading={saving} loadingLabel="Checking…" disabled={!hydrated}>
        {switching ? "Switch user" : "Unlock"}
      </Button>
      <div className="flex flex-wrap gap-3">
        {!signedOut && (
          <Button
            variant="quiet"
            onClick={() => {
              setMode(mode === "unlock" ? "switch" : "unlock");
              setError(undefined);
            }}
          >
            {mode === "unlock" ? "Switch user" : "Back to unlock"}
          </Button>
        )}
        <Button variant="quiet" onClick={passwordInstead}>
          Sign in with a password instead
        </Button>
      </div>
    </form>
  );
}
