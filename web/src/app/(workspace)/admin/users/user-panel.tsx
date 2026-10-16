"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, TextInput } from "@/components/ui/field";
import { ReasonDialog } from "@/components/ui/reason-dialog";
import { Select } from "@/components/ui/select";
import { Callout, StatusPill } from "@/components/ui/status";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, problemMessage } from "@/lib/api/client";
import { rows, type Schemas, unwrap } from "@/lib/api/query";
import { useMe } from "@/lib/auth/session";
import { formatDate, parseDate } from "@/lib/format";

import { type AdminUser, USERS_KEY, userName, UserStatus } from "./page";

type Assignment = Schemas["Assignment"];
type Licence = Schemas["Licence"];
type Role = Schemas["Role"];

const REGULATORS = [
  { value: "KMPDC", label: "Kenya Medical Practitioners and Dentists Council" },
  { value: "COC", label: "Clinical Officers Council" },
  { value: "NCK", label: "Nursing Council of Kenya" },
  { value: "PPB", label: "Pharmacy and Poisons Board" },
  { value: "KMLTTB", label: "Kenya Medical Laboratory Technicians and Technologists Board" },
  { value: "OTHER", label: "Other regulator" },
];

const failure = (caught: unknown, fallback: string) =>
  caught instanceof ApiError ? problemMessage(caught.problem) : fallback;

/** One user's account, role assignments and licences (DESIGN §7.6, §7.10). */
export function UserPanel({ user, onClose }: { user: AdminUser; onClose: () => void }) {
  const client = useQueryClient();
  const toast = useToast();
  const { data: me } = useMe();
  const can = (code: string) => me?.permissions.includes(code) ?? false;
  const [dialog, setDialog] = useState<"deactivate" | "revoke" | null>(null);
  const [revoking, setRevoking] = useState<Assignment>();
  const [temporary, setTemporary] = useState<string>();

  const assignments = useQuery({
    queryKey: ["admin", "assignments", user.id],
    queryFn: () => unwrap(api.GET("/api/v1/access/assignments/", { params: { query: { user: user.id } as never } })),
  });
  const licences = useQuery({
    queryKey: ["admin", "licences", user.id],
    enabled: can("access.licence.read"),
    queryFn: () => unwrap(api.GET("/api/v1/accounts/licences/", { params: { query: { user: user.id } as never } })),
  });
  const refresh = () =>
    Promise.all([
      client.invalidateQueries({ queryKey: USERS_KEY }),
      client.invalidateQueries({ queryKey: ["admin", "assignments", user.id] }),
      client.invalidateQueries({ queryKey: ["admin", "licences", user.id] }),
    ]);

  async function act(run: () => Promise<unknown>, done: string) {
    try {
      await run();
      await refresh();
      toast({ title: done, tone: "success" });
    } catch (caught) {
      toast({ title: failure(caught, "That did not work. Try again."), tone: "danger" });
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()} title={userName(user)} description={user.email} size="lg">
      <div className="flex flex-col gap-6">
        <section aria-label="Account" className="flex flex-wrap items-center gap-3">
          <UserStatus user={user} />
          <StatusPill tone={user.mfa_enrolled ? "success" : "neutral"}>Two-step sign-in {user.mfa_enrolled ? "on" : "off"}</StatusPill>
          <div className="ml-auto flex flex-wrap gap-2">
            {user.account_locked && can("admin.user.unlock") && (
              <Button variant="secondary" onClick={() => act(() => unwrap(api.POST("/api/v1/accounts/users/{id}/unlock/", { params: { path: { id: user.id } } })), "Account unlocked")}>
                Unlock account
              </Button>
            )}
            {user.is_active && can("admin.user.reset_credentials") && user.id !== me?.id && (
              <Button
                variant="secondary"
                onClick={() =>
                  act(async () => {
                    const result = (await unwrap(
                      api.POST("/api/v1/accounts/users/{id}/reset-credentials/", { params: { path: { id: user.id } } }),
                    )) as unknown as { temporary_password: string };
                    setTemporary(result.temporary_password);
                  }, "Credentials reset")
                }
              >
                Reset password and two-step
              </Button>
            )}
            {user.is_active && can("admin.user.deactivate") && user.id !== me?.id && (
              <Button variant="danger" onClick={() => setDialog("deactivate")}>
                Deactivate
              </Button>
            )}
          </div>
        </section>
        {temporary && (
          <Callout tone="warning" title="Hand this one-time password over in person.">
            <p data-testid="temporary-password" className="tabular mt-1 text-lg font-semibold">
              {temporary}
            </p>
            They must choose a new password and set up two-step sign-in again.
          </Callout>
        )}

        <section aria-labelledby="roles-heading" className="flex flex-col gap-3">
          <h3 id="roles-heading" className="text-lg font-bold">
            Roles at this facility
          </h3>
          <ul className="flex flex-col border border-border-strong">
            {rows<Assignment>(assignments.data)
              .filter((a) => a.status !== "revoked")
              .map((a) => (
                <li key={a.id} className="flex flex-wrap items-center gap-3 border-b border-border-subtle px-4 py-2 last:border-b-0">
                  <span className="font-semibold">{a.role}</span>
                  {a.status === "pending_approval" ? (
                    <StatusPill tone="warning">Waiting for a second administrator</StatusPill>
                  ) : (
                    <StatusPill tone="success">Active</StatusPill>
                  )}
                  <span className="text-sm text-ink-muted">{a.reason}</span>
                  {can("access.assignment.manage") && (
                    <Button
                      className="ml-auto"
                      density="compact"
                      variant="secondary"
                      onClick={() => {
                        setRevoking(a);
                        setDialog("revoke");
                      }}
                    >
                      Revoke {a.role}
                    </Button>
                  )}
                </li>
              ))}
            {rows<Assignment>(assignments.data).every((a) => a.status === "revoked") && (
              <li className="px-4 py-3 text-ink-muted">No roles yet. Grant one below so they can work.</li>
            )}
          </ul>
          {can("access.assignment.manage") && <GrantRole user={user} onGranted={refresh} />}
        </section>

        {can("access.licence.read") && (
          <section aria-labelledby="licences-heading" className="flex flex-col gap-3">
            <h3 id="licences-heading" className="text-lg font-bold">
              Professional licences
            </h3>
            <ul className="flex flex-col border border-border-strong">
              {rows<Licence>(licences.data).map((l) => (
                <li key={l.id} className="flex flex-wrap items-center gap-3 border-b border-border-subtle px-4 py-2 last:border-b-0">
                  <span className="font-semibold">{l.regulator}</span>
                  <span className="tabular">{l.registration_number}</span>
                  <span className="text-sm text-ink-muted">valid to {formatDate(l.valid_to)}</span>
                  {l.verified_at ? (
                    <StatusPill tone="success">Verified</StatusPill>
                  ) : can("access.licence.manage") ? (
                    <Button
                      className="ml-auto"
                      density="compact"
                      variant="secondary"
                      onClick={() => act(() => unwrap(api.POST("/api/v1/accounts/licences/{id}/verify/", { params: { path: { id: l.id } } })), "Licence verified")}
                    >
                      Verify with the registry
                    </Button>
                  ) : (
                    <StatusPill tone="warning">Not verified</StatusPill>
                  )}
                </li>
              ))}
              {rows<Licence>(licences.data).length === 0 && <li className="px-4 py-3 text-ink-muted">No licence recorded.</li>}
            </ul>
            {can("access.licence.manage") && <AddLicence user={user} onAdded={refresh} />}
          </section>
        )}
      </div>

      <ReasonDialog
        open={dialog === "deactivate"}
        onOpenChange={(open) => !open && setDialog(null)}
        title={`Deactivate ${userName(user)}`}
        description="They are signed out everywhere now and cannot sign in again. Their records stay."
        action="Deactivate"
        variant="danger"
        onConfirm={async (reason) => {
          await unwrap(api.POST("/api/v1/accounts/users/{id}/deactivate/", { params: { path: { id: user.id } }, body: { reason } }));
          await refresh();
          toast({ title: "User deactivated", tone: "success" });
        }}
      />
      <ReasonDialog
        open={dialog === "revoke"}
        onOpenChange={(open) => !open && setDialog(null)}
        title={`Revoke ${revoking?.role ?? "role"}`}
        action="Revoke role"
        variant="danger"
        onConfirm={async (reason) => {
          if (!revoking) return;
          await unwrap(api.POST("/api/v1/access/assignments/{id}/revoke/", { params: { path: { id: revoking.id } }, body: { reason } }));
          await refresh();
          toast({ title: "Role revoked", tone: "success" });
        }}
      />
    </Dialog>
  );
}

function GrantRole({ user, onGranted }: { user: AdminUser; onGranted: () => Promise<unknown> }) {
  const toast = useToast();
  const [role, setRole] = useState<string>();
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);
  const roles = useQuery({ queryKey: ["admin", "roles"], queryFn: () => unwrap(api.GET("/api/v1/access/roles/")) });
  const chosen = rows<Role>(roles.data).find((r) => r.code === role);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const reason = String(new FormData(form).get("reason") ?? "");
    if (!role) {
      setError("Choose a role.");
      return;
    }
    setSaving(true);
    setError(undefined);
    try {
      const created = await unwrap(api.POST("/api/v1/access/assignments/", { body: { user: user.id, role, reason } }));
      // Clear before refreshing: the list updates mid-refresh, and a quick next entry must not be wiped.
      form.reset();
      setRole(undefined);
      await onGranted();
      toast({
        title: created.status === "pending_approval" ? "Role requested — a second administrator must approve" : "Role granted",
        tone: "success",
      });
    } catch (caught) {
      setError(failure(caught, "Could not grant the role."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form method="post" onSubmit={submit} noValidate className="grid gap-3 border border-border-subtle bg-surface-sunken p-4 md:grid-cols-[1fr_1fr_auto] md:items-end">
      {error && <div className="md:col-span-3"><Callout tone="danger" title={error} /></div>}
      <Field label="Role" required hint={chosen?.privileged ? "Privileged: a second administrator approves it." : undefined}>
        {(control) => (
          <Select
            {...control}
            value={role}
            onValueChange={setRole}
            placeholder="Choose a role"
            options={rows<Role>(roles.data)
              .filter((r) => r.code !== "public_api_client")
              .map((r) => ({ value: r.code, label: r.name }))}
          />
        )}
      </Field>
      <Field label="Reason" required>
        {(control) => <TextInput {...control} name="reason" maxLength={255} />}
      </Field>
      <Button type="submit" loading={saving}>
        Grant role
      </Button>
    </form>
  );
}

function AddLicence({ user, onAdded }: { user: AdminUser; onAdded: () => Promise<unknown> }) {
  const toast = useToast();
  const [regulator, setRegulator] = useState<string>();
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const validTo = parseDate(String(data.get("valid_to") ?? ""));
    if (!regulator || !validTo) {
      setError(!regulator ? "Choose the regulator." : "Enter the expiry date as DD/MM/YYYY.");
      return;
    }
    setSaving(true);
    setError(undefined);
    try {
      await unwrap(
        api.POST("/api/v1/accounts/licences/", {
          body: {
            user: user.id,
            regulator: regulator as Schemas["RegulatorEnum"],
            registration_number: String(data.get("registration_number") ?? ""),
            valid_to: validTo,
          },
        }),
      );
      form.reset();
      setRegulator(undefined);
      await onAdded();
      toast({ title: "Licence recorded", tone: "success" });
    } catch (caught) {
      setError(failure(caught, "Could not record the licence."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form method="post" onSubmit={submit} noValidate className="grid gap-3 border border-border-subtle bg-surface-sunken p-4 md:grid-cols-[1fr_1fr_10rem_auto] md:items-end">
      {error && <div className="md:col-span-4"><Callout tone="danger" title={error} /></div>}
      <Field label="Regulator" required>
        {(control) => <Select {...control} value={regulator} onValueChange={setRegulator} placeholder="Choose" options={REGULATORS} />}
      </Field>
      <Field label="Registration number" required>
        {(control) => <TextInput {...control} name="registration_number" autoComplete="off" />}
      </Field>
      <Field label="Valid to" required hint="DD/MM/YYYY">
        {(control) => <TextInput {...control} name="valid_to" inputMode="numeric" autoComplete="off" />}
      </Field>
      <Button type="submit" loading={saving}>
        Record licence
      </Button>
    </form>
  );
}
