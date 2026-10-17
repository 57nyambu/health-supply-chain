"use client";

import { useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";

import { PayerEligibility } from "@/components/insurance/payer-eligibility";
import { coveragesOf } from "@/components/insurance/api";
import { Button } from "@/components/ui/button";
import { Field, TextInput } from "@/components/ui/field";
import { Callout, StatusPill } from "@/components/ui/status";
import { api, ApiError, problemMessage } from "@/lib/api/client";
import { type Schemas, unwrap } from "@/lib/api/query";
import { SEX_SHORT } from "@/lib/patients";

type Result = Schemas["SearchResult"];

/**
 * Claims workspace (Phase 3). Stage A: cover check — find a patient and verify each cover
 * with its payer (eligibility snapshot, then the visit consent where the payer needs one).
 * The claims worklist arrives with P3-CLM-01 once visits and billing are on main.
 */
export default function ClaimsPage() {
  const [results, setResults] = useState<Result[]>();
  const [patient, setPatient] = useState<Result>();
  const [error, setError] = useState<string>();
  const [searching, setSearching] = useState(false);

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const q = String(new FormData(event.currentTarget).get("q") ?? "").trim();
    if (!q) {
      setError("Type an ID, phone number, MRN or name.");
      return;
    }
    setSearching(true);
    setError(undefined);
    setPatient(undefined);
    try {
      setResults((await unwrap(api.POST("/api/v1/patients/search/", { body: { q } }))).results);
    } catch (caught) {
      setError(caught instanceof ApiError ? problemMessage(caught.problem) : "The search did not work. Try again.");
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <h1 className="text-xl font-bold">Claims</h1>
      <section aria-labelledby="check-heading" className="flex max-w-3xl flex-col gap-4 border border-border-strong bg-surface p-4">
        <h2 id="check-heading" className="text-lg font-bold">
          Cover check
        </h2>
        <form onSubmit={search} className="flex flex-wrap items-end gap-3" noValidate>
          <Field label="Find the patient" hint="ID, phone number, MRN or at least 3 letters of the name." className="min-w-72 flex-1">
            {(control) => <TextInput {...control} name="q" autoComplete="off" />}
          </Field>
          <Button type="submit" loading={searching} loadingLabel="Searching…">
            Search
          </Button>
        </form>
        {error && (
          <Callout tone="danger" title="Search failed">
            {error}
          </Callout>
        )}
        {results && !patient && (
          <ul className="flex flex-col divide-y divide-border border border-border" aria-label="Patients found">
            {results.length === 0 && <li className="p-3 text-ink-muted">No patient matches.</li>}
            {results.map((r) => (
              <li key={r.id} className="flex items-center justify-between gap-3 p-3">
                <span className="text-ink">
                  <span className="font-semibold">{r.display_name}</span> · {r.mrn} · {SEX_SHORT[r.sex] ?? r.sex}
                </span>
                <Button variant="secondary" density="compact" onClick={() => setPatient(r)}>
                  Check cover
                </Button>
              </li>
            ))}
          </ul>
        )}
        {patient && <Covers patient={patient} onBack={() => setPatient(undefined)} />}
      </section>
    </div>
  );
}

function Covers({ patient, onBack }: { patient: Result; onBack: () => void }) {
  const covers = useQuery({ queryKey: ["insurance", "coverages", patient.id], queryFn: () => coveragesOf(patient.id) });
  const current = (covers.data ?? []).filter((c) => c.current);
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-ink">
          <span className="font-semibold">{patient.display_name}</span> · {patient.mrn}
        </p>
        <Button variant="quiet" onClick={onBack}>
          Choose another patient
        </Button>
      </div>
      {covers.isLoading && <StatusPill>Loading cover…</StatusPill>}
      {covers.isFetched && current.length === 0 && (
        <Callout tone="info" title="No current cover">
          This patient pays cash or self-pays. Record a cover at reception to bill a payer.
        </Callout>
      )}
      {current.map((c) => (
        <PayerEligibility key={c.id} patientId={patient.id} coverageId={c.id} />
      ))}
    </div>
  );
}
