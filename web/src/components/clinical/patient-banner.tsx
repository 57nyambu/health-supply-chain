import { ShieldAlert, TriangleAlert } from "lucide-react";

import { StatusPill } from "@/components/ui/status";
import { cn } from "@/lib/cn";
import { ageText, formatDate, formatTime } from "@/lib/format";

export type BannerPatient = {
  displayName: string;
  sex: "female" | "male" | "intersex" | string;
  dateOfBirth: string | null;
  dobEstimated?: boolean;
  mrn: string;
  /** The second identifier always shown next to the MRN (masked unless chart access allows). */
  secondIdentifier?: { label: string; value: string };
  allergies: { state: "none_known" | "not_recorded" | "recorded"; items?: string[] };
  alerts?: string[];
  payer?: { name: string; status: "verified" | "pending" | "failed" | "self_pay" };
};

const SEX = { female: "F", male: "M", intersex: "Intersex" } as Record<string, string>;
const PAYER_TONE = { verified: "success", pending: "warning", failed: "danger", self_pay: "neutral" } as const;
const PAYER_TEXT = { verified: "verified", pending: "verification pending", failed: "not verified", self_pay: "self-pay" };

/** Name, sex, age (DOB on hover/focus), two identifiers, allergies state, alerts, payer. */
export function PatientBanner({ patient }: { patient: BannerPatient }) {
  const { allergies } = patient;
  return (
    <section aria-label="Patient" className="sticky top-0 z-20 border-b border-border-subtle bg-surface px-6 py-3 shadow-sticky">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h2 className="text-lg font-bold text-ink">{patient.displayName}</h2>
        <span className="text-ink">{SEX[patient.sex] ?? patient.sex}</span>
        {patient.dateOfBirth && (
          <span tabIndex={0} className="group relative rounded-control text-ink">
            {ageText(patient.dateOfBirth)}
            {patient.dobEstimated && <span className="text-ink-muted"> (estimated)</span>}
            <span className="ml-2 hidden text-ink-muted group-hover:inline group-focus:inline">
              DOB {formatDate(patient.dateOfBirth)}
            </span>
          </span>
        )}
        <span className="tabular text-ink">
          <span className="text-ink-muted">MRN </span>
          {patient.mrn}
        </span>
        {patient.secondIdentifier && (
          <span className="tabular text-ink">
            <span className="text-ink-muted">{patient.secondIdentifier.label} </span>
            {patient.secondIdentifier.value}
          </span>
        )}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {allergies.state === "recorded" && allergies.items?.length ? (
          <span className="inline-flex items-center gap-1 rounded-control border border-danger bg-danger-tint px-2 py-0.5 font-semibold text-danger-ink">
            <ShieldAlert aria-hidden className="size-4" />
            Allergy: {allergies.items.join(", ")}
          </span>
        ) : allergies.state === "none_known" ? (
          <StatusPill tone="success">No known allergies</StatusPill>
        ) : (
          <span className="inline-flex items-center gap-1 rounded-control border border-warning-ink bg-warning-tint px-2 py-0.5 font-semibold text-warning-ink">
            <TriangleAlert aria-hidden className="size-4" />
            Allergies not recorded
          </span>
        )}
        {patient.alerts?.map((alert) => (
          <StatusPill key={alert} tone="warning">
            Alert: {alert}
          </StatusPill>
        ))}
        {patient.payer && (
          <StatusPill tone={PAYER_TONE[patient.payer.status]}>
            Payer: {patient.payer.name} {PAYER_TEXT[patient.payer.status]}
          </StatusPill>
        )}
      </div>
    </section>
  );
}

/** Shown while the user reads a chart through break-glass access (P1-UAC-08). */
export function BreakGlassBanner({ expiresAt, onEnd }: { expiresAt: string; onEnd?: () => void }) {
  return (
    <div role="status" className={cn("flex items-start gap-3 border-l-4 border-l-danger bg-danger-tint px-6 py-3 text-danger-ink")}>
      <ShieldAlert aria-hidden className="mt-0.5 size-5 shrink-0" />
      <p className="flex-1 font-semibold">
        Emergency access until {formatTime(expiresAt)}. Every view is logged and reviewed by the medical superintendent and the data protection officer.
      </p>
      {onEnd && (
        <button type="button" onClick={onEnd} className="shrink-0 rounded-control border border-danger bg-surface px-3 py-1 font-semibold text-danger-ink hover:bg-surface-hover">
          End emergency access
        </button>
      )}
    </div>
  );
}
