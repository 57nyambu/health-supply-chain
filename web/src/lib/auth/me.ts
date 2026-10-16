/** GET /api/v1/me — the signed-in user, facility, roles and effective permissions.
 * The UI only hides what the user cannot do; the API enforces access (web/CLAUDE.md). */
export type Me = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  must_change_password: boolean;
  facility: { id: number; name: string; mfl_code: string } | null;
  facilities: { id: number; name: string }[];
  roles: string[];
  permissions: string[];
  session: { idle_minutes: number; absolute_hours: number; lock_minutes: number };
  mfa: { enrolled: boolean; required: boolean; verified: boolean };
  workstation: { locked: boolean; pin_set: boolean };
};

export type AuthStep = "login" | "mfa" | "mfa-setup" | "password" | "locked" | "workspace";

/** Where a signed-in user has to go next. */
export function nextStep(me: Me): AuthStep {
  if (me.workstation.locked) return "locked";
  if (me.mfa.required && !me.mfa.enrolled) return "mfa-setup";
  if (me.mfa.enrolled && !me.mfa.verified) return "mfa";
  if (me.must_change_password) return "password";
  return "workspace";
}

export function displayName(me: Pick<Me, "first_name" | "last_name" | "email">): string {
  return [me.first_name, me.last_name].filter(Boolean).join(" ") || me.email;
}

/** Problem codes that move the user to another screen (from the API's problem+json). */
export const AUTH_ROUTES: Record<string, string> = {
  not_authenticated: "/login",
  session_expired: "/session-expired",
  workstation_locked: "/locked",
  mfa_enrolment_required: "/mfa/setup",
  mfa_required: "/mfa",
  password_change_required: "/account/password",
};
