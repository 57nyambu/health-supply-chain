"use client";

import { useQueries } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/status";
import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/query";
import { MATCH_REASONS, SEX_SHORT } from "@/lib/patients";

type Candidate = { id: string; score: number; reasons: string[] };

/** The likely duplicates the API found; opening one is usually the right move (DESIGN §6.1). */
export function Duplicates({ candidates, onOpen }: { candidates: Candidate[]; onOpen: (id: string) => void }) {
  const records = useQueries({
    queries: candidates.slice(0, 5).map((c) => ({
      queryKey: ["patient", c.id, "registration"],
      queryFn: () =>
        unwrap(api.GET("/api/v1/patients/{id}/", { params: { path: { id: c.id }, query: { purpose: "registration" } } })),
    })),
  });
  return (
    <Callout tone="warning" title="This looks like a patient who is already registered.">
      <p className="mt-1">Open the existing record if it is the same person. Register anyway only with a reason.</p>
      <ul className="mt-3 flex flex-col gap-2">
        {candidates.slice(0, 5).map((candidate, index) => {
          const record = records[index]?.data;
          return (
            <li key={candidate.id} className="flex flex-wrap items-center gap-3 border border-border-strong bg-surface px-3 py-2 text-ink">
              <span className="font-semibold">{record ? record.display_name : "Loading…"}</span>
              {record && (
                <span className="text-ink-muted">
                  {SEX_SHORT[record.sex] ?? record.sex}
                  {record.age ? ` · ${record.age}` : ""} · MRN <span className="tabular">{record.mrn}</span>
                </span>
              )}
              <span className="text-sm text-ink-muted">
                Same {candidate.reasons.map((r) => MATCH_REASONS[r] ?? r).join(", ")}
              </span>
              <Button className="ml-auto" density="compact" variant="secondary" onClick={() => onOpen(candidate.id)}>
                Open this record
              </Button>
            </li>
          );
        })}
      </ul>
    </Callout>
  );
}
