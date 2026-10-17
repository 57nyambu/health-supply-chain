import type { AdminSection } from "./sections";

/** Administration sections added by the Phase 2 lane (ADR-024) — edited only by that lane. */
export const PHASE_2_SECTIONS: AdminSection[] = [
  { href: "/admin/services", label: "Services and prices", permission: "billing.pricelist.manage" },
  { href: "/admin/gates", label: "Payment gates", permission: "visits.gate.manage" },
  { href: "/admin/boards", label: "Queue boards", permission: "visits.board.manage" },
];
