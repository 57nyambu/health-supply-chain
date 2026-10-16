"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { Dialog } from "@/components/ui/dialog";
import { Field, TextInput } from "@/components/ui/field";
import { Callout, StatusPill } from "@/components/ui/status";
import { api, ApiError, problemMessage } from "@/lib/api/client";
import { rows, type Schemas, unwrap } from "@/lib/api/query";
import { useMe } from "@/lib/auth/session";

import { UserPanel } from "./user-panel";

export type AdminUser = Schemas["User"];
export const USERS_KEY = ["admin", "users"] as const;

export function userName(user: Pick<AdminUser, "first_name" | "last_name" | "email">) {
  return [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email;
}

export function UserStatus({ user }: { user: AdminUser }) {
  if (!user.is_active) return <StatusPill>Deactivated</StatusPill>;
  if (user.account_locked) return <StatusPill tone="danger">Locked</StatusPill>;
  if (user.must_change_password) return <StatusPill tone="warning">Must change password</StatusPill>;
  return <StatusPill tone="success">Active</StatusPill>;
}

export default function UsersPage() {
  const { data: me } = useMe();
  const [filter, setFilter] = useState("");
  const [adding, setAdding] = useState(false);
  const [openId, setOpenId] = useState<number>();
  const users = useQuery({
    queryKey: USERS_KEY,
    queryFn: () => unwrap(api.GET("/api/v1/accounts/users/", { params: { query: { page_size: 200 } as never } })),
  });

  const list = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    return rows<AdminUser>(users.data).filter(
      (u) => !needle || `${userName(u)} ${u.email} ${u.roles.join(" ")}`.toLowerCase().includes(needle),
    );
  }, [users.data, filter]);
  const opened = list.find((u) => u.id === openId) ?? rows<AdminUser>(users.data).find((u) => u.id === openId);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-3">
        <Field label="Find a user" className="w-80">
          {(control) => <TextInput {...control} type="search" value={filter} onChange={(e) => setFilter(e.target.value)} />}
        </Field>
        {me?.permissions.includes("admin.user.create") && (
          <Button className="ml-auto" onClick={() => setAdding(true)}>
            Add user
          </Button>
        )}
      </div>
      {users.isError && <Callout tone="danger" title="The user list could not be loaded." />}
      <DataTable
        caption="Users at this facility"
        rows={list}
        rowKey={(u) => String(u.id)}
        selectedKey={openId ? String(openId) : undefined}
        onOpen={(u) => setOpenId(u.id)}
        empty={users.isPending ? "Loading…" : "No users match. Add a user to give them access."}
        columns={[
          { key: "name", header: "Name", cell: (u) => <button type="button" className="font-semibold text-primary hover:underline" onClick={() => setOpenId(u.id)}>{userName(u)}</button>, sortValue: (u) => userName(u) },
          { key: "email", header: "E-mail", cell: (u) => u.email, sortValue: (u) => u.email },
          { key: "roles", header: "Roles here", cell: (u) => (u.roles.length ? u.roles.join(", ") : <span className="text-ink-muted">None</span>) },
          { key: "mfa", header: "Two-step", cell: (u) => (u.mfa_enrolled ? "On" : "Off") },
          { key: "status", header: "Status", cell: (u) => <UserStatus user={u} /> },
        ]}
      />
      <AddUserDialog open={adding} onOpenChange={setAdding} onCreated={(id) => setOpenId(id)} />
      {opened && <UserPanel user={opened} onClose={() => setOpenId(undefined)} />}
    </div>
  );
}

function AddUserDialog({ open, onOpenChange, onCreated }: { open: boolean; onOpenChange: (open: boolean) => void; onCreated: (id: number) => void }) {
  const client = useQueryClient();
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);
  const [created, setCreated] = useState<{ id: number; email: string; temporary: string }>();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSaving(true);
    setError(undefined);
    try {
      const user = (await unwrap(
        api.POST("/api/v1/accounts/users/", {
          body: {
            email: String(form.get("email") ?? ""),
            first_name: String(form.get("first_name") ?? ""),
            last_name: String(form.get("last_name") ?? ""),
            is_approved: true,
          } as Schemas["UserCreateRequest"],
        }),
      )) as unknown as AdminUser & { temporary_password: string };
      await client.invalidateQueries({ queryKey: USERS_KEY });
      setCreated({ id: user.id, email: user.email, temporary: user.temporary_password });
    } catch (caught) {
      setError(caught instanceof ApiError ? problemMessage(caught.problem) : "Could not add the user.");
    } finally {
      setSaving(false);
    }
  }

  function close(next: boolean) {
    if (!next && created) {
      onCreated(created.id);
      setCreated(undefined);
    }
    onOpenChange(next);
  }

  return (
    <Dialog open={open} onOpenChange={close} title={created ? "User added" : "Add user"}>
      {created ? (
        <div className="flex flex-col gap-4">
          <Callout tone="warning" title="Hand this one-time password over in person.">
            It is shown only now. {created.email} must choose a new password at first sign-in. Next, grant them a role.
          </Callout>
          <p data-testid="temporary-password" className="tabular border border-border-strong bg-surface-sunken p-3 text-lg font-semibold">
            {created.temporary}
          </p>
          <Button autoFocus onClick={() => close(false)}>
            Done, grant roles
          </Button>
        </div>
      ) : (
        <form method="post" onSubmit={submit} noValidate className="flex flex-col gap-4">
          {error && <Callout tone="danger" title={error} />}
          <Field label="E-mail address" required>
            {(control) => <TextInput {...control} name="email" type="email" autoComplete="off" autoFocus />}
          </Field>
          <Field label="Given name">{(control) => <TextInput {...control} name="first_name" autoComplete="off" />}</Field>
          <Field label="Family name">{(control) => <TextInput {...control} name="last_name" autoComplete="off" />}</Field>
          <Button type="submit" loading={saving}>
            Add user
          </Button>
        </form>
      )}
    </Dialog>
  );
}
