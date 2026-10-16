import { Check, Siren } from "lucide-react";

import { cn } from "@/lib/cn";

export const JOURNEY = ["Reception", "Triage", "Consultation", "Services", "Review", "Disposition", "Settlement"] as const;
export type JourneyStep = (typeof JOURNEY)[number];

type JourneyRailProps = {
  current: JourneyStep;
  emergency?: boolean;
  /** Clicking a completed step opens its record. */
  onSelect?: (step: JourneyStep) => void;
};

/** The signature element: where this visit is (DESIGN-SYSTEM §1, §7). */
export function JourneyRail({ current, emergency = false, onSelect }: JourneyRailProps) {
  const currentIndex = JOURNEY.indexOf(current);
  return (
    <nav aria-label="Visit journey" className="border-b border-border-subtle bg-surface px-6 py-2">
      <ol className="flex flex-wrap items-center gap-1">
        {emergency && (
          <li className="mr-2 inline-flex items-center gap-1 rounded-control bg-triage-red px-2 py-1 text-sm font-semibold text-triage-red-text">
            <Siren aria-hidden className="size-4" />
            Emergency
          </li>
        )}
        {JOURNEY.map((step, index) => {
          const state = index < currentIndex ? "done" : index === currentIndex ? "current" : "todo";
          const body = (
            <>
              {state === "done" && <Check aria-hidden className="size-4" />}
              {step}
            </>
          );
          const cls = cn(
            "inline-flex items-center gap-1 rounded-control border px-3 py-1 text-sm font-semibold",
            state === "done" && "border-primary-tint bg-primary-tint text-primary",
            state === "current" && "border-primary bg-primary text-on-primary",
            state === "todo" && "border-border-strong bg-surface text-ink-muted",
          );
          return (
            <li key={step} className="inline-flex items-center gap-1" aria-current={state === "current" ? "step" : undefined}>
              {index > 0 && <span aria-hidden className="h-px w-3 bg-border-strong" />}
              {state === "done" && onSelect ? (
                <button
                  type="button"
                  aria-label={`${step} (completed)`}
                  className={cn(cls, "hover:underline")}
                  onClick={() => onSelect(step)}
                >
                  {body}
                </button>
              ) : (
                <span className={cls}>
                  {body}
                  {state === "done" && <span className="sr-only">(completed)</span>}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
