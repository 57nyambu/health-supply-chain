"use client";

import { useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, TextInput } from "@/components/ui/field";
import { DateInput, type DobValue, IdentifierInput, type IdentifierValue, PhoneInput } from "@/components/ui/inputs";
import { Select } from "@/components/ui/select";
import { Callout } from "@/components/ui/status";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, type Problem, problemMessage } from "@/lib/api/client";
import { type Schemas, unwrap } from "@/lib/api/query";
import { normalisePhone } from "@/lib/format";
import { prefillFrom, SEX_OPTIONS } from "@/lib/patients";

import { Duplicates } from "./duplicates";
import { type NoticeChoice, PrivacyNotice } from "@/components/clinical/privacy-notice";

type Candidate = { id: string; score: number; reasons: string[] };

/** Field errors from a problem+json body, keyed by the first path segment ("identifiers.0.value" → "identifiers"). */
export function fieldErrors(problem: Problem): Record<string, string> {
  const out: Record<string, string> = {};
  for (const e of problem.errors ?? []) {
    const key = (e.field ?? "").split(".")[0] || "form";
    out[key] = out[key] ? `${out[key]} ${e.message}` : e.message;
  }
  return out;
}

/** New registration: names, sex, date of birth (or age), IDs, phone, next of kin, privacy notice. */
export function RegisterForm({
  initial,
  onCancel,
  onRegistered,
  onOpenExisting,
}: {
  initial?: string;
  onCancel: () => void;
  onRegistered: (id: string) => void;
  onOpenExisting: (id: string) => void;
}) {
  const toast = useToast();
  const [prefill] = useState(() => prefillFrom(initial));
  const [sex, setSex] = useState<string>();
  const [dob, setDob] = useState<DobValue>({ date: null, estimated: false });
  const [identifiers, setIdentifiers] = useState<IdentifierValue[]>([{ type: "national_id", value: prefill.identifier }]);
  const [phone, setPhone] = useState<string | null>(() => normalisePhone(prefill.phone));
  const [kinPhone, setKinPhone] = useState<string | null>(null);
  const [notice, setNotice] = useState<NoticeChoice>({ method: "verbal", given_by: "patient", given: false });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [duplicates, setDuplicates] = useState<Candidate[]>();
  const [saving, setSaving] = useState(false);
  const privacy = useQuery({ queryKey: ["privacy-notice"], queryFn: () => unwrap(api.GET("/api/v1/patients/privacy-notice/")) });

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const text = (name: string) => String(data.get(name) ?? "").trim();
    const problems: Record<string, string> = {};
    if (!text("given_name") || !text("family_name")) problems.given_name = "Enter the given and family names.";
    if (!sex) problems.sex = "Choose the sex.";
    if (!dob.estimated && !dob.date) problems.date_of_birth = "Enter the date of birth as DD/MM/YYYY, or tick that it is unknown and enter the age.";
    if (dob.estimated && !dob.years && !dob.months) problems.date_of_birth = "Enter the age in years or months.";
    if (!notice.given) problems.privacy_notice = "Give the privacy notice and tick to confirm.";
    if (text("phone") && !phone) problems.contacts = "Enter a Kenyan phone number, e.g. 0712 345 678.";
    const kin = { name: text("kin_name"), relationship: text("kin_relationship"), phone: kinPhone ?? "" };
    if ((kin.name || kin.relationship || text("kin_phone")) && (!kin.name || !kin.relationship)) {
      problems.next_of_kin = "Enter the next of kin's name and relationship, or leave all three empty.";
    }
    setErrors(problems);
    if (Object.keys(problems).length) return;

    const body: Schemas["PatientCreateRequest"] = {
      given_name: text("given_name"),
      middle_name: text("middle_name"),
      family_name: text("family_name"),
      sex: sex as Schemas["PatientCreateRequest"]["sex"],
      date_of_birth: dob.estimated ? null : dob.date,
      age_years: dob.estimated ? (dob.years ?? 0) : null,
      age_months: dob.estimated ? (dob.months ?? 0) : null,
      identifiers: identifiers.filter((i) => i.value.trim()).map((i) => ({ type: i.type, value: i.value.trim(), issuer: "" })),
      contacts: phone ? [{ kind: "phone", value: phone, is_primary: true }] : [],
      next_of_kin: kin.name ? [kin] : [],
      override_reason: text("override_reason"),
      privacy_notice: {
        version: privacy.data?.version ?? "",
        method: notice.method as Schemas["PrivacyNoticeRequest"]["method"],
        given_by: notice.given_by as Schemas["PrivacyNoticeRequest"]["given_by"],
      },
    };
    setSaving(true);
    try {
      const created = await unwrap(api.POST("/api/v1/patients/", { body }));
      toast({ title: `Patient registered — MRN ${created.mrn}`, tone: "success" });
      onRegistered(created.id);
    } catch (caught) {
      if (caught instanceof ApiError && caught.problem.code === "likely_duplicate") {
        setDuplicates((caught.problem.candidates as Candidate[] | undefined) ?? []);
      } else if (caught instanceof ApiError && caught.status === 400) {
        setErrors(fieldErrors(caught.problem));
      } else {
        setErrors({ form: caught instanceof ApiError ? problemMessage(caught.problem) : "Could not register the patient. Try again." });
      }
    } finally {
      setSaving(false);
    }
  }

  const fieldError = (name: string) => errors[name];
  const summary = Object.entries(errors);

  return (
    <section aria-labelledby="register-heading" className="flex flex-col gap-4 border border-border-strong bg-surface p-4">
      <h2 id="register-heading" className="text-lg font-bold">
        Register a new patient
      </h2>
      <form method="post" onSubmit={submit} noValidate className="flex flex-col gap-6">
        {summary.length > 0 && (
          <Callout tone="danger" title="Check these before registering.">
            <ul className="list-disc pl-5">
              {summary.map(([key, message]) => (
                <li key={key}>{message}</li>
              ))}
            </ul>
          </Callout>
        )}

        <fieldset className="grid gap-3 md:grid-cols-3">
          <legend className="mb-2 font-bold">Name and sex</legend>
          <Field label="Given name" required error={fieldError("given_name")}>
            {(control) => <TextInput {...control} name="given_name" defaultValue={prefill.given_name} autoFocus autoComplete="off" maxLength={80} />}
          </Field>
          <Field label="Middle name">
            {(control) => <TextInput {...control} name="middle_name" defaultValue={prefill.middle_name} autoComplete="off" maxLength={80} />}
          </Field>
          <Field label="Family name" required>
            {(control) => <TextInput {...control} name="family_name" defaultValue={prefill.family_name} autoComplete="off" maxLength={80} />}
          </Field>
          <Field label="Sex" required error={fieldError("sex")}>
            {(control) => <Select {...control} value={sex} onValueChange={setSex} options={SEX_OPTIONS} placeholder="Choose" />}
          </Field>
          <Field label="Date of birth" required hint={dob.estimated ? undefined : "DD/MM/YYYY"} error={fieldError("date_of_birth") ?? fieldError("age_years")} className="md:col-span-2">
            {(control) => <DateInput {...control} value={dob} onValueChange={setDob} />}
          </Field>
        </fieldset>

        <fieldset className="flex flex-col gap-3">
          <legend className="mb-2 font-bold">Identifiers and phone</legend>
          {identifiers.map((identifier, index) => (
            <Field key={index} label={index === 0 ? "Identifier" : `Identifier ${index + 1}`} hint="Leave empty if the patient has none with them." error={index === 0 ? fieldError("identifiers") : undefined}>
              {(control) => (
                <IdentifierInput
                  {...control}
                  value={identifier}
                  onValueChange={(next) => setIdentifiers(identifiers.map((item, i) => (i === index ? next : item)))}
                />
              )}
            </Field>
          ))}
          <div>
            <Button variant="quiet" density="compact" onClick={() => setIdentifiers([...identifiers, { type: "sha_number", value: "" }])}>
              Add another identifier
            </Button>
          </div>
          <Field label="Phone" hint="Kenyan mobile, e.g. 0712 345 678" error={fieldError("contacts")} className="max-w-sm">
            {(control) => <PhoneInput {...control} name="phone" value={prefill.phone} onValueChange={(e164) => setPhone(e164)} />}
          </Field>
        </fieldset>

        <fieldset className="grid gap-3 md:grid-cols-3">
          <legend className="mb-2 font-bold">Next of kin (optional)</legend>
          {fieldError("next_of_kin") && (
            <p className="text-danger-ink md:col-span-3">{fieldError("next_of_kin")}</p>
          )}
          <Field label="Next of kin name">
            {(control) => <TextInput {...control} name="kin_name" autoComplete="off" maxLength={120} />}
          </Field>
          <Field label="Relationship" hint="e.g. mother, spouse, son">
            {(control) => <TextInput {...control} name="kin_relationship" autoComplete="off" maxLength={40} />}
          </Field>
          <Field label="Next of kin phone">
            {(control) => <PhoneInput {...control} name="kin_phone" value="" onValueChange={(e164) => setKinPhone(e164)} />}
          </Field>
        </fieldset>

        <PrivacyNotice notice={privacy.data} value={notice} onChange={setNotice} error={fieldError("privacy_notice")} />

        {duplicates && (
          <Duplicates candidates={duplicates} onOpen={onOpenExisting} />
        )}

        <div className="flex flex-wrap items-end gap-3">
          {duplicates && (
            <Field label="Reason to register anyway" required hint="e.g. a different person with the same name" className="min-w-80 flex-1">
              {(control) => <TextInput {...control} name="override_reason" autoComplete="off" maxLength={255} />}
            </Field>
          )}
          <Button type="submit" loading={saving} className={duplicates ? "mb-6" : undefined}>
            {duplicates ? "Register anyway" : "Register patient"}
          </Button>
          <Button variant="secondary" onClick={onCancel} className={duplicates ? "mb-6" : undefined}>
            Cancel
          </Button>
        </div>
      </form>
    </section>
  );
}
