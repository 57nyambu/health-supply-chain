import { PHASE_2_SECTIONS } from "./sections-phase2";
import { PHASE_3_SECTIONS } from "./sections-phase3";

export type AdminSection = { href: string; label: string; permission: string };

/** Administration sections and the permission that shows each (the API enforces them). */
const PHASE_1_SECTIONS: AdminSection[] = [
  { href: "/admin/users", label: "Users and roles", permission: "admin.user.read" },
  { href: "/admin/approvals", label: "Approvals", permission: "access.approval.read" },
  { href: "/admin/licences", label: "Licences", permission: "access.licence.read" },
  { href: "/admin/facility", label: "Facility setup", permission: "facilities.facility.read" },
  { href: "/admin/break-glass", label: "Break-glass reviews", permission: "access.breakglass.review" },
  { href: "/admin/audit", label: "Audit log", permission: "audit.log.read" },
];

/** Phase 2 and Phase 3 lanes add their sections in their own files (ADR-024). */
export const ADMIN_SECTIONS: AdminSection[] = [...PHASE_1_SECTIONS, ...PHASE_2_SECTIONS, ...PHASE_3_SECTIONS];

export function sectionsFor(permissions: readonly string[]) {
  return ADMIN_SECTIONS.filter((s) => permissions.includes(s.permission));
}
