"use client";

import { Siren, UserPlus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { Field, TextInput } from "@/components/ui/field";
import { StatusPill } from "@/components/ui/status";
import { api, ApiError, problemMessage } from "@/lib/api/client";
import { type Schemas, unwrap } from "@/lib/api/query";
import { useMe } from "@/lib/auth/session";
import { identifierLabel, MATCH_REASONS, maskIdentifier, SEX_SHORT } from "@/lib/patients";

import { RegistrySearch } from "./registry-search";
import { RegisterForm } from "./register-form";
import { UnidentifiedDialog } from "./unidentified-dialog";

type Result = Schemas["SearchResult"];

/** Reception: search before create, over local records and the Client Registry (DESIGN-SYSTEM §6.2). */
export default function ReceptionPage() {
  const router = useRouter();
  const { data: me } = useMe();
  const can = (code: string) => me?.permissions.includes(code) ?? false;
  const [searched, setSearched] = useState<string>();
  const [results, setResults] = useState<Result[]>();
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string>();
  const [registering, setRegistering] = useState(false);
  const [emergency, setEmergency] = useState(false);
  const table = useRef<HTMLDivElement>(null);
  const registerButton = useRef<HTMLButtonElement>(null);

  // After a search, the keyboard goes to the first match (↑/↓, Enter opens) or to "Register".
  useEffect(() => {
    if (results === undefined) return;
    const first = table.current?.querySelector<HTMLElement>("tbody tr[tabindex]");
    (first ?? registerButton.current)?.focus();
  }, [results]);

  const open = (id: string) => router.push(`/patients/${id}`);

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const q = String(new FormData(event.currentTarget).get("q") ?? "").trim();
    if (!q) {
      setError("Type an ID, phone number, MRN or name.");
      return;
    }
    setSearching(true);
    setError(undefined);
    setRegistering(false);
    try {
      const found = await unwrap(api.POST("/api/v1/patients/search/", { body: { q } }));
      setSearched(q);
      setResults(found.results);
    } catch (caught) {
      setError(caught instanceof ApiError ? problemMessage(caught.problem) : "The search did not work. Try again.");
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-bold">Reception</h1>
        {can("patients.patient.register_unidentified") && (
          <Button variant="danger" className="ml-auto" onClick={() => setEmergency(true)}>
            <Siren aria-hidden className="size-4" />
            Unidentified emergency patient
          </Button>
        )}
      </div>

      <section aria-labelledby="find-heading" className="flex flex-col gap-4 border border-border-strong bg-surface p-4">
        <h2 id="find-heading" className="text-lg font-bold">
          Find the patient first
        </h2>
        <form method="post" role="search" aria-label="Patients at this facility" onSubmit={search} noValidate className="grid gap-3 md:grid-cols-[1fr_auto] md:items-end">
          <Field label="ID, phone, MRN or name" hint="Press / to come back here. Names need at least 3 letters." error={error}>
            {(control) => <TextInput {...control} name="q" data-patient-search autoFocus autoComplete="off" spellCheck={false} />}
          </Field>
          <Button type="submit" loading={searching} loadingLabel="Searching…" className="md:mb-6">
            Search
          </Button>
        </form>

        {results !== undefined && (
          <div ref={table} className="flex flex-col gap-3">
            <p role="status" className="text-ink-muted">
              {results.length === 0
                ? "No patient here matches. Check the Client Registry, or register a new patient."
                : `${results.length} ${results.length === 1 ? "patient matches" : "patients match"}. Use ↑ and ↓, then Enter to open.`}
            </p>
            {results.length > 0 && (
              <DataTable
                caption="Patients matching the search"
                rows={results}
                rowKey={(r) => r.id}
                onOpen={(r) => open(r.id)}
                empty=""
                columns={[
                  {
                    key: "name",
                    header: "Name",
                    cell: (r) => (
                      <Link href={`/patients/${r.id}`} tabIndex={-1} className="font-semibold text-primary hover:underline">
                        {r.display_name}
                      </Link>
                    ),
                  },
                  { key: "sex", header: "Sex", cell: (r) => SEX_SHORT[r.sex] ?? r.sex },
                  { key: "age", header: "Age", cell: (r) => (r.age ? `${r.age}${r.dob_estimated ? " (est.)" : ""}` : "—") },
                  {
                    key: "ids",
                    header: "Identifiers",
                    cell: (r) =>
                      r.identifiers.length
                        ? r.identifiers.map((i) => `${identifierLabel(i.type)} ${i.value}`).join(" · ")
                        : "—",
                  },
                  { key: "mrn", header: "MRN", cell: (r) => <span className="tabular">{maskIdentifier(r.mrn)}</span> },
                  {
                    key: "match",
                    header: "Matched on",
                    cell: (r) =>
                      r.is_unidentified ? (
                        <StatusPill tone="warning">Unidentified</StatusPill>
                      ) : (
                        r.reasons.map((reason) => MATCH_REASONS[reason] ?? reason).join(", ")
                      ),
                  },
                ]}
              />
            )}
          </div>
        )}

        {can("patients.patient.create") && (
          <div className="flex flex-wrap items-center gap-3">
            <Button ref={registerButton} variant="secondary" disabled={searched === undefined || registering || searching} onClick={() => setRegistering(true)}>
              <UserPlus aria-hidden className="size-4" />
              Register new patient
            </Button>
            {searched === undefined && <span className="text-sm text-ink-muted">Search first, so the same person is not registered twice.</span>}
          </div>
        )}
      </section>

      {registering && (
        <RegisterForm
          initial={searched}
          onCancel={() => setRegistering(false)}
          onRegistered={(id) => open(id)}
          onOpenExisting={(id) => open(id)}
        />
      )}

      {can("patients.registry.search") && !registering && <RegistrySearch onOpen={open} onLocalMatches={setResults} />}

      <UnidentifiedDialog open={emergency} onOpenChange={setEmergency} onRegistered={(id) => open(id)} />
    </div>
  );
}
