import {
  CircleAlert,
  CircleCheck,
  Circle,
  Diamond,
  Info,
  Octagon,
  Square,
  Triangle,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export type Tone = "neutral" | "info" | "success" | "warning" | "danger";

const TONE: Record<Tone, { box: string; icon: LucideIcon }> = {
  neutral: { box: "border-border-strong bg-surface-sunken text-ink", icon: Info },
  info: { box: "border-primary bg-primary-tint text-primary", icon: Info },
  success: { box: "border-success bg-success-tint text-success-ink", icon: CircleCheck },
  warning: { box: "border-warning-ink bg-warning-tint text-warning-ink", icon: TriangleAlert },
  danger: { box: "border-danger bg-danger-tint text-danger-ink", icon: CircleAlert },
};

/** Full-round chip with text and icon — never colour alone. */
export function StatusPill({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  const { box, icon: Icon } = TONE[tone];
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-sm font-semibold", box)}>
      <Icon aria-hidden className="size-3.5" />
      {children}
    </span>
  );
}

/** Tinted box, 4 px rail, icon, title and body. Danger callouts are announced. */
export function Callout({ tone = "info", title, children }: { tone?: Exclude<Tone, "neutral">; title: string; children?: ReactNode }) {
  const { box, icon: Icon } = TONE[tone];
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={cn("flex gap-3 border-l-4 p-4", box, "border-y-0 border-r-0")}
    >
      <Icon aria-hidden className="mt-0.5 size-5 shrink-0" />
      <div className="text-ink">
        <p className="font-semibold">{title}</p>
        {children && <div className="mt-1 text-ink">{children}</div>}
      </div>
    </div>
  );
}

export type TriageLevel = "red" | "orange" | "yellow" | "green" | "blue";

const TRIAGE: Record<TriageLevel, { adult: string; child?: string; icon: LucideIcon; cls: string; rail: string }> = {
  red: { adult: "Red (emergency)", child: "Emergency", icon: Octagon, cls: "bg-triage-red text-triage-red-text", rail: "var(--color-triage-red)" },
  orange: { adult: "Orange (very urgent)", icon: Triangle, cls: "bg-triage-orange text-triage-orange-text", rail: "var(--color-triage-orange)" },
  yellow: { adult: "Yellow (urgent)", child: "Priority", icon: Diamond, cls: "bg-triage-yellow text-triage-yellow-text", rail: "var(--color-triage-yellow)" },
  green: { adult: "Green (routine)", child: "Non-urgent", icon: Circle, cls: "bg-triage-green text-triage-green-text", rail: "var(--color-triage-green)" },
  blue: { adult: "Blue (dead on arrival)", icon: Square, cls: "bg-triage-blue text-triage-blue-text", rail: "var(--color-triage-blue)" },
};

/** Colour + word + shape (DESIGN-SYSTEM §2.2). `scale="paediatric"` uses ETAT+ labels. */
export function TriageTag({ level, scale = "adult" }: { level: TriageLevel; scale?: "adult" | "paediatric" }) {
  const t = TRIAGE[level];
  const Icon = t.icon;
  const label = scale === "paediatric" ? (t.child ?? t.adult) : t.adult;
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-control px-2 py-0.5 text-sm font-semibold", t.cls)}>
      <Icon aria-hidden className="size-3.5 fill-current" />
      {label}
    </span>
  );
}

/** The 4 px left rail colour for a queue row. */
export const triageRail = (level: TriageLevel) => ({ boxShadow: `inset 4px 0 0 ${TRIAGE[level].rail}` });
