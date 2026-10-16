"use client";

import * as Menu from "@radix-ui/react-dropdown-menu";
import { useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Keyboard, Lock, LogOut, UserRound } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { type FormEvent, type ReactNode, useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, TextInput } from "@/components/ui/field";
import { Callout } from "@/components/ui/status";
import { useToast } from "@/components/ui/toast";
import { ApiError, problemMessage, send } from "@/lib/api/client";
import { cn } from "@/lib/cn";
import { displayName, type Me, nextStep } from "@/lib/auth/me";
import { destination, ME_KEY, useIdleLock, useMe } from "@/lib/auth/session";
import { type Workspace, workspacesFor } from "@/lib/auth/workspaces";

const SHORTCUTS = [
  ["/", "Focus patient search"],
  ["Alt+L", "Lock workstation"],
  ["?", "Show this help"],
];

const menuItem =
  "flex cursor-default items-center gap-2 rounded-control px-3 py-2 text-ink outline-none data-[highlighted]:bg-selected";

function typing(target: EventTarget | null) {
  const el = target as HTMLElement | null;
  return Boolean(el && (el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName)));
}

/** Role-aware app shell (DESIGN-SYSTEM §6.1): only what /api/v1/me allows is shown. */
export function Shell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const client = useQueryClient();
  const toast = useToast();
  const { data: me, isPending } = useMe();
  const [help, setHelp] = useState(false);
  const [pinOpen, setPinOpen] = useState(false);

  const lock = useCallback(async () => {
    await send("/api/v1/auth/lock", { method: "POST" }).catch(() => undefined);
    client.removeQueries({ queryKey: ME_KEY });
    router.replace("/locked");
  }, [client, router]);

  useIdleLock(me?.session.lock_minutes, lock);

  const canSearch = me?.permissions.includes("patients.patient.search") ?? false;

  useEffect(() => {
    if (me && nextStep(me) !== "workspace") router.replace(destination(me, pathname));
  }, [me, pathname, router]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      // By physical key, so Alt+L works on every layout (Option+L on a Mac types "¬").
      if (event.altKey && event.code === "KeyL") {
        event.preventDefault();
        void lock();
      } else if (event.key === "?" && !typing(event.target)) {
        event.preventDefault();
        setHelp(true);
      } else if (event.key === "/" && !typing(event.target) && !event.altKey && !event.ctrlKey && !event.metaKey) {
        // Patient search: the box on this page, or reception's (DESIGN-SYSTEM §8).
        const box = document.querySelector<HTMLInputElement>("[data-patient-search]");
        if (box) {
          event.preventDefault();
          box.focus();
          box.select();
        } else if (canSearch) {
          event.preventDefault();
          router.push("/reception");
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [lock, router, canSearch]);

  if (isPending || !me || nextStep(me) !== "workspace") {
    return (
      <p role="status" className="p-8 text-ink-muted">
        Loading…
      </p>
    );
  }

  const workspaces = workspacesFor(me.permissions);
  // A patient's record (/patients/<uuid>) opens from reception's search for now; later
  // phases open it from their own worklists.
  const patientRoute = pathname.startsWith("/patients/") && me.permissions.includes("patients.patient.read");
  const current =
    workspaces.find((w) => pathname === `/${w.key}` || pathname.startsWith(`/${w.key}/`)) ??
    (patientRoute ? workspaces.find((w) => w.key === "reception") : undefined);

  async function signOut() {
    await send("/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
    client.clear();
    router.replace("/login?reason=signed-out");
  }

  async function switchFacility(id: number) {
    try {
      const updated = await send<Me>("/api/v1/me/facility", { method: "POST", body: { facility: id } });
      client.setQueryData(ME_KEY, updated);
      router.replace(destination(updated));
    } catch (caught) {
      toast({ title: caught instanceof ApiError ? problemMessage(caught.problem) : "Could not switch facility.", tone: "danger" });
    }
  }

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-surface focus:p-2">
        Skip to content
      </a>
      <header className="flex h-14 items-center gap-4 border-b border-border-strong bg-surface px-4">
        <span className="font-bold text-ink">AfyaSync</span>
        {me.facilities.length > 1 ? (
          <Picker
            label="Facility"
            value={me.facility?.name ?? "Choose facility"}
            items={me.facilities.map((f) => ({ key: String(f.id), label: f.name, onSelect: () => switchFacility(f.id) }))}
          />
        ) : (
          <span className="text-ink-muted">{me.facility?.name}</span>
        )}
        {workspaces.length > 1 && (
          <Picker
            label="Workspace"
            value={current?.label ?? "Choose workspace"}
            items={workspaces.map((w) => ({ key: w.key, label: w.label, onSelect: () => router.push(`/${w.key}`) }))}
          />
        )}
        <div className="ml-auto" />
        <Menu.Root>
          <Menu.Trigger className="inline-flex items-center gap-2 rounded-control px-2 py-1 font-semibold text-ink hover:bg-surface-hover">
            <UserRound aria-hidden className="size-5" />
            {displayName(me)}
            <ChevronDown aria-hidden className="size-4" />
          </Menu.Trigger>
          <Menu.Portal>
            <Menu.Content align="end" sideOffset={4} className="z-50 min-w-56 rounded-overlay border border-border-strong bg-surface p-1 shadow-menu">
              <Menu.Item className={menuItem} onSelect={() => setPinOpen(true)}>
                <Keyboard aria-hidden className="size-4" />
                {me.workstation.pin_set ? "Change PIN" : "Set PIN"}
              </Menu.Item>
              <Menu.Item className={menuItem} onSelect={() => router.push("/account/password")}>
                <UserRound aria-hidden className="size-4" />
                Change password
              </Menu.Item>
              <Menu.Item className={menuItem} onSelect={() => void lock()}>
                <Lock aria-hidden className="size-4" />
                Lock workstation <span className="ml-auto text-sm text-ink-muted">Alt+L</span>
              </Menu.Item>
              <Menu.Separator className="my-1 h-px bg-border-subtle" />
              <Menu.Item className={menuItem} onSelect={() => void signOut()}>
                <LogOut aria-hidden className="size-4" />
                Sign out
              </Menu.Item>
            </Menu.Content>
          </Menu.Portal>
        </Menu.Root>
      </header>
      <div className="flex flex-1">
        <nav aria-label="Workspaces" className="w-[72px] shrink-0 border-r border-border-strong bg-surface-sunken lg:w-48">
          <ul className="flex flex-col gap-1 p-2">
            {workspaces.map((w) => (
              <NavItem key={w.key} workspace={w} active={w.key === current?.key} />
            ))}
          </ul>
        </nav>
        <main id="main" tabIndex={-1} className="min-w-0 flex-1 outline-none">
          {current || patientRoute || pathname === "/" ? (
            children
          ) : (
            <div className="p-8">
              <Callout tone="warning" title="This workspace is not available to your roles.">
                Choose one of your workspaces on the left.
              </Callout>
            </div>
          )}
        </main>
      </div>
      <Dialog open={help} onOpenChange={setHelp} title="Keyboard shortcuts">
        <dl className="grid grid-cols-[8rem_1fr] gap-2">
          {SHORTCUTS.map(([keys, action]) => (
            <div key={keys} className="contents">
              <dt>
                <kbd className="rounded-control border border-border-strong bg-surface-sunken px-2 py-0.5 font-semibold">{keys}</kbd>
              </dt>
              <dd>{action}</dd>
            </div>
          ))}
        </dl>
      </Dialog>
      <PinDialog open={pinOpen} onOpenChange={setPinOpen} />
    </div>
  );
}

function NavItem({ workspace, active }: { workspace: Workspace; active: boolean }) {
  const Icon = workspace.icon;
  return (
    <li>
      <Link
        href={`/${workspace.key}`}
        aria-current={active ? "page" : undefined}
        className={cn(
          "flex flex-col items-center gap-1 rounded-control px-2 py-2 text-center text-sm font-semibold text-ink lg:flex-row lg:text-left",
          active ? "bg-selected shadow-[inset_4px_0_0_var(--color-primary)]" : "hover:bg-surface-hover",
        )}
      >
        <Icon aria-hidden className="size-5 shrink-0" />
        {workspace.label}
      </Link>
    </li>
  );
}

function Picker({ label, value, items }: { label: string; value: string; items: { key: string; label: string; onSelect: () => void }[] }) {
  return (
    <Menu.Root>
      <Menu.Trigger
        aria-label={`${label}: ${value}`}
        className="inline-flex items-center gap-2 rounded-control border border-border-strong px-3 py-1 text-ink hover:bg-surface-hover"
      >
        <span className="text-ink-muted">{label}:</span>
        <span className="font-semibold">{value}</span>
        <ChevronDown aria-hidden className="size-4" />
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Content align="start" sideOffset={4} className="z-50 min-w-56 rounded-overlay border border-border-strong bg-surface p-1 shadow-menu">
          {items.map((item) => (
            <Menu.Item key={item.key} className={menuItem} onSelect={item.onSelect}>
              {item.label}
            </Menu.Item>
          ))}
        </Menu.Content>
      </Menu.Portal>
    </Menu.Root>
  );
}

function PinDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const client = useQueryClient();
  const toast = useToast();
  const [pin, setPin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);

  async function save(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(undefined);
    try {
      await send("/api/v1/auth/pin", { method: "POST", body: { pin, password } });
      await client.invalidateQueries({ queryKey: ME_KEY });
      toast({ title: "PIN saved", tone: "success" });
      setPin("");
      setPassword("");
      onOpenChange(false);
    } catch (caught) {
      setError(caught instanceof ApiError ? problemMessage(caught.problem) : "Could not save the PIN.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange} title="Workstation PIN" description="Unlock this workstation quickly with a 6-digit PIN.">
      <form method="post" onSubmit={save} noValidate className="flex flex-col gap-4">
        {error && <Callout tone="danger" title={error} />}
        <Field label="New PIN" required hint="6 digits; not your password">
          {(control) => (
            <TextInput {...control} type="password" inputMode="numeric" autoComplete="off" maxLength={6} className="tabular" value={pin} onChange={(e) => setPin(e.target.value)} />
          )}
        </Field>
        <Field label="Your password" required>
          {(control) => (
            <TextInput {...control} type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
          )}
        </Field>
        <Button type="submit" loading={saving}>
          Save PIN
        </Button>
      </form>
    </Dialog>
  );
}
