/** Administration sections and the permission that shows each (the API enforces them). */
export const ADMIN_SECTIONS = [
  { href: "/admin/users", label: "Users and roles", permission: "admin.user.read" },
  { href: "/admin/approvals", label: "Approvals", permission: "access.approval.read" },
  { href: "/admin/licences", label: "Licences", permission: "access.licence.read" },
  { href: "/admin/facility", label: "Facility setup", permission: "facilities.facility.read" },
  { href: "/admin/break-glass", label: "Break-glass reviews", permission: "access.breakglass.review" },
  { href: "/admin/audit", label: "Audit log", permission: "audit.log.read" },
] as const;

export function sectionsFor(permissions: readonly string[]) {
  return ADMIN_SECTIONS.filter((s) => permissions.includes(s.permission));
}
