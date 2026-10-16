"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef } from "react";

import { ApiError, send } from "@/lib/api/client";

import { AUTH_ROUTES, type AuthStep, type Me, nextStep } from "./me";
import { workspacesFor } from "./workspaces";

export const ME_KEY = ["me"] as const;

export function useMe() {
  return useQuery({ queryKey: ME_KEY, queryFn: () => send<Me>("/api/v1/me") });
}

/** The page for an API problem that needs a different screen, or undefined. */
export function authRoute(error: unknown): string | undefined {
  return error instanceof ApiError && error.problem.code ? AUTH_ROUTES[error.problem.code] : undefined;
}

const STEP_ROUTES: Record<Exclude<AuthStep, "workspace">, string> = {
  login: "/login",
  mfa: "/mfa",
  "mfa-setup": "/mfa/setup",
  password: "/account/password",
  locked: "/locked",
};

/** Where to send a user after sign-in, MFA or unlock. */
export function destination(me: Me, wanted?: string | null): string {
  const step = nextStep(me);
  if (step !== "workspace") return STEP_ROUTES[step];
  // Only same-site paths; never echo arbitrary URLs.
  if (wanted && wanted.startsWith("/") && !wanted.startsWith("//")) return wanted;
  const first = workspacesFor(me.permissions)[0];
  return first ? `/${first.key}` : "/no-access";
}

/** Store the fresh /me payload returned by sign-in, MFA and unlock calls. */
export function useSignedIn() {
  const client = useQueryClient();
  const router = useRouter();
  return useCallback(
    (me: Me, wanted?: string | null) => {
      client.setQueryData(ME_KEY, me);
      router.replace(destination(me, wanted));
    },
    [client, router],
  );
}

/** Lock the workstation after the facility's idle time (the server also enforces it). */
export function useIdleLock(minutes: number | undefined, onLock: () => void) {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (!minutes) return;
    const reset = () => {
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(onLock, minutes * 60_000);
    };
    const events = ["keydown", "pointerdown", "pointermove", "wheel"] as const;
    events.forEach((e) => window.addEventListener(e, reset, { passive: true }));
    reset();
    return () => {
      events.forEach((e) => window.removeEventListener(e, reset));
      if (timer.current) clearTimeout(timer.current);
    };
  }, [minutes, onLock]);
}
