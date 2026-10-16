"use client";

import { useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, TextInput } from "@/components/ui/field";
import { PhoneInput } from "@/components/ui/inputs";
import { Select } from "@/components/ui/select";
import { Callout, StatusPill } from "@/components/ui/status";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, problemMessage } from "@/lib/api/client";
import { type Schemas, unwrap } from "@/lib/api/query";
import { useMe } from "@/lib/auth/session";
import { formatDate } from "@/lib/format";
import { identifierLabel, REGISTRY_TYPES, SEX_SHORT } from "@/lib/patients";

import { Duplicates } from "./duplicates";
import { type NoticeChoice, PrivacyNotice } from "@/components/clinical/privacy-notice";

type Found = Schemas["RegistrySearch"];
type Candidate = { id: string; score: number; reasons: string[] };

/** National lookup through the HIE Client Registry adapter (fake until GAP-CR-001 closes). */
export function RegistrySearch({
  onOpen,
  onLocalMatches,
}: {
  onOpen: (id: string) => void;
  onLocalMatches: (results: Schemas["SearchResult"][]) => void;
}) {
  const [type, setType] = useState("national_id");
  const [lookup, setLookup] = useState<{ type: string; number: string; found: Found }>();
  const [error, setError] = useState<string>();
  const [searching, setSearching] = useState(false);

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const number = String(new FormData(event.currentTarget).get("number") ?? "").trim().toUpperCase();
    if (!number) {
      setError("Enter the number from the patient's document.");
      return;
    }
    setSearching(true);
    setError(undefined);
    try {
      const found = await unwrap(
        api.POST("/api/v1/patients/registry-search/", { body: { type: type as Schemas["RegistryQueryRequest"]["type"], number } }),
      );
      setLookup({ type, number, found });
      if (found.local.length) onLocalMatches(found.local);
    } catch (caught) {
      setError(caught instanceof ApiError ? problemMessage(caught.problem) : "The lookup did not work. Try again.");
    } finally {
      setSearching(false);
    }
  }

  const registry = lookup?.found.registry;
  return (
    <section aria-labelledby="registry-heading" className="flex flex-col gap-4 border border-border-strong bg-surface p-4">
      <h2 id="registry-heading" className="text-lg font-bold">
        Client Registry (national)
      </h2>
      <form method="post" onSubmit={search} noValidate className="grid gap-3 md:grid-cols-[14rem_1fr_auto] md:items-end">
        <Field label="Document">
          {(control) => <Select {...control} value={type} onValueChange={setType} options={REGISTRY_TYPES} />}
        </Field>
        <Field label="Number" error={error}>
          {(control) => <TextInput {...control} name="number" autoComplete="off" spellCheck={false} className="tabular uppercase" />}
        </Field>
        <Button type="submit" variant="secondary" loading={searching} loadingLabel="Searching…" className={error ? "md:mb-6" : undefined}>
          Search the registry
        </Button>
      </form>

      {registry?.status === "unavailable" && (
        <Callout tone="warning" title="The Client Registry did not answer.">
          Register the patient here now; the CR ID can be added when the registry is back. Care is never held up by the registry.
        </Callout>
      )}
      {registry?.status === "not_found" && (
        <Callout tone="info" title="No record in the Client Registry for this number.">
          Check the number with the patient, or register them here.
        </Callout>
      )}
      {registry?.status === "found" && registry.person && lookup && (
        <div className="flex flex-col gap-3 border border-border-subtle bg-surface-sunken p-4">
          <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <span className="text-lg font-bold">
              {[registry.person.given_name, registry.person.middle_name, registry.person.family_name].filter(Boolean).join(" ")}
            </span>
            <span>{SEX_SHORT[registry.person.sex] ?? registry.person.sex}</span>
            {registry.person.date_of_birth && <span>born {formatDate(registry.person.date_of_birth)}</span>}
            <span className="tabular">{registry.person.cr_id}</span>
            <StatusPill tone="success">In the Client Registry</StatusPill>
          </div>
          <p className="text-sm text-ink-muted">
            {registry.person.identifiers.map((i) => `${identifierLabel(i.type)} ${i.value}`).join(" · ")}
            {registry.person.phone ? ` · phone ${registry.person.phone}` : ""}
          </p>
          {registry.registered_patient ? (
            <div className="flex flex-wrap items-center gap-3">
              <span>Already registered at this facility.</span>
              <Button onClick={() => onOpen(registry.registered_patient!)}>Open the record</Button>
            </div>
          ) : (
            <RegistryImport type={lookup.type} number={lookup.number} onImported={onOpen} />
          )}
        </div>
      )}
    </section>
  );
}

function RegistryImport({ type, number, onImported }: { type: string; number: string; onImported: (id: string) => void }) {
  const toast = useToast();
  const { data: me } = useMe();
  const [notice, setNotice] = useState<NoticeChoice>({ method: "verbal", given_by: "patient", given: false });
  const [phone, setPhone] = useState<string | null>(null);
  const [error, setError] = useState<string>();
  const [duplicates, setDuplicates] = useState<Candidate[]>();
  const [saving, setSaving] = useState(false);
  const privacy = useQuery({ queryKey: ["privacy-notice"], queryFn: () => unwrap(api.GET("/api/v1/patients/privacy-notice/")) });
  if (!me?.permissions.includes("patients.registry.import")) return null;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    if (!notice.given) {
      setError("Give the privacy notice and tick to confirm.");
      return;
    }
    if (String(data.get("phone") ?? "").trim() && !phone) {
      setError("Enter a Kenyan phone number, e.g. 0712 345 678.");
      return;
    }
    setSaving(true);
    setError(undefined);
    try {
      const created = await unwrap(
        api.POST("/api/v1/patients/registry-import/", {
          body: {
            type: type as Schemas["RegistryImportRequest"]["type"],
            number,
            contacts: phone ? [{ kind: "phone", value: phone, is_primary: true }] : [],
            override_reason: String(data.get("override_reason") ?? "").trim(),
            privacy_notice: {
              version: privacy.data?.version ?? "",
              method: notice.method as Schemas["PrivacyNoticeRequest"]["method"],
              given_by: notice.given_by as Schemas["PrivacyNoticeRequest"]["given_by"],
            },
          },
        }),
      );
      toast({ title: `Patient registered from the Client Registry — MRN ${created.mrn}`, tone: "success" });
      onImported(created.id);
    } catch (caught) {
      if (caught instanceof ApiError && caught.problem.code === "likely_duplicate") {
        setDuplicates((caught.problem.candidates as Candidate[] | undefined) ?? []);
      } else {
        setError(caught instanceof ApiError ? problemMessage(caught.problem) : "Could not register the patient. Try again.");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <form method="post" onSubmit={submit} noValidate className="flex flex-col gap-4 border-t border-border-subtle pt-4">
      {error && <Callout tone="danger" title={error} />}
      <Field label="Phone" hint="Leave empty to use the registry's number." className="max-w-sm">
        {(control) => <PhoneInput {...control} name="phone" value="" onValueChange={(e164) => setPhone(e164)} />}
      </Field>
      <PrivacyNotice notice={privacy.data} value={notice} onChange={setNotice} />
      {duplicates && <Duplicates candidates={duplicates} onOpen={onImported} />}
      <div className="flex flex-wrap items-end gap-3">
        {duplicates && (
          <Field label="Reason to register anyway" required className="min-w-80 flex-1">
            {(control) => <TextInput {...control} name="override_reason" autoComplete="off" maxLength={255} />}
          </Field>
        )}
        <Button type="submit" loading={saving} className={duplicates ? "mb-6" : undefined}>
          {duplicates ? "Register anyway" : "Register from the Client Registry"}
        </Button>
      </div>
    </form>
  );
}
