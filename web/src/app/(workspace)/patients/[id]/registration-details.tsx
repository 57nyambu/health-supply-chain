"use client";

import { useQuery } from "@tanstack/react-query";
import { type FormEvent, type ReactNode, useState } from "react";

import { type NoticeChoice, PrivacyNotice } from "@/components/clinical/privacy-notice";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, TextInput } from "@/components/ui/field";
import { DateInput, type DobValue, IdentifierInput, type IdentifierValue, PhoneInput } from "@/components/ui/inputs";
import { Select } from "@/components/ui/select";
import { Callout, StatusPill } from "@/components/ui/status";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, problemMessage } from "@/lib/api/client";
import { type Schemas, unwrap } from "@/lib/api/query";
import { formatDate, formatDateTime } from "@/lib/format";
import { identifierLabel, NOTICE_GIVEN_TO, NOTICE_METHODS, SEX_OPTIONS } from "@/lib/patients";

type Patient = Schemas["Patient"];
type Panel = "details" | "phone" | "identifier" | "kin" | "notice" | null;

const failure = (caught: unknown, fallback: string) =>
  caught instanceof ApiError
    ? caught.status === 409
      ? "Someone else changed this record just now. Close this, check the record and try again."
      : problemMessage(caught.problem)
    : fallback;

/** Who the patient is and how to reach them; each change is its own audited, append-only entry. */
export function RegistrationDetails({ patient, editable, onChanged }: { patient: Patient; editable: boolean; onChanged: () => Promise<unknown> }) {
  const toast = useToast();
  const [panel, setPanel] = useState<Panel>(null);
  const notice = patient.consents.find((c) => c.kind === "privacy_notice");
  const sms = patient.consents.find((c) => c.kind === "sms_reminders");

  /** Run a save; close the dialog and refresh only when it worked. Errors stay in the dialog. */
  const save = (run: () => Promise<unknown>, done: string) => async () => {
    await run();
    setPanel(null);
    toast({ title: done, tone: "success" });
    await onChanged();
  };

  return (
    <section aria-labelledby="registration-heading" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <h2 id="registration-heading" className="mr-auto text-lg font-bold">
          Registration details
        </h2>
        {editable && (
          <>
            <Button density="compact" variant="secondary" onClick={() => setPanel("details")}>
              Edit details
            </Button>
            <Button density="compact" variant="secondary" onClick={() => setPanel("phone")}>
              Add phone
            </Button>
            <Button density="compact" variant="secondary" onClick={() => setPanel("identifier")}>
              Add identifier
            </Button>
            <Button density="compact" variant="secondary" onClick={() => setPanel("kin")}>
              Add next of kin
            </Button>
          </>
        )}
      </div>

      <dl className="grid grid-cols-[10rem_1fr] gap-x-4 gap-y-2 border border-border-strong bg-surface p-4">
        <Row label="Name">{patient.display_name}</Row>
        <Row label="Sex">{SEX_OPTIONS.find((s) => s.value === patient.sex)?.label ?? patient.sex}</Row>
        <Row label="Date of birth">
          {patient.date_of_birth ? `${formatDate(patient.date_of_birth)}${patient.dob_estimated ? " (estimated)" : ""}` : "Not recorded"}
        </Row>
        <Row label="MRN">
          <span className="tabular">{patient.mrn}</span>
        </Row>
        {patient.is_unidentified && <Row label="Description">{patient.description}</Row>}
      </dl>

      <List title="Identifiers" empty="No identifiers yet.">
        {patient.identifiers.map((i) => (
          <li key={i.id} className="flex flex-wrap items-center gap-3 px-4 py-2">
            <span className="w-40 text-ink-muted">{identifierLabel(i.type)}</span>
            <span className="tabular font-semibold">{i.value}</span>
            {i.verified_at ? (
              <StatusPill tone="success">Verified with the Client Registry</StatusPill>
            ) : i.source === "system" ? (
              <StatusPill tone="warning">Temporary</StatusPill>
            ) : null}
          </li>
        ))}
      </List>

      <List title="Phone and e-mail" empty="No phone or e-mail yet.">
        {patient.contacts.map((c) => (
          <li key={c.id} className="flex flex-wrap items-center gap-3 px-4 py-2">
            <span className="w-40 text-ink-muted">{c.kind === "phone" ? "Phone" : "E-mail"}</span>
            <span className="tabular font-semibold">{c.value}</span>
            {c.is_primary && <StatusPill tone="neutral">Main</StatusPill>}
          </li>
        ))}
      </List>

      <List title="Next of kin" empty="No next of kin yet.">
        {patient.next_of_kin.map((k) => (
          <li key={k.id} className="flex flex-wrap items-center gap-3 px-4 py-2">
            <span className="font-semibold">{k.name}</span>
            <span className="text-ink-muted">{k.relationship}</span>
            {k.phone && <span className="tabular">{k.phone}</span>}
          </li>
        ))}
      </List>

      <div className="flex flex-col gap-2 border border-border-strong bg-surface p-4">
        <h3 className="font-bold">Privacy</h3>
        {notice?.decision === "given" ? (
          <p>
            <StatusPill tone="success">Privacy notice given</StatusPill>{" "}
            <span className="text-sm text-ink-muted">
              version {notice.version}, {formatDateTime(notice.recorded_at)}
            </span>
          </p>
        ) : (
          <div className="flex flex-wrap items-center gap-3">
            <StatusPill tone="warning">Privacy notice not recorded</StatusPill>
            {editable && (
              <Button density="compact" variant="secondary" onClick={() => setPanel("notice")}>
                Record the privacy notice
              </Button>
            )}
          </div>
        )}
        <p className="text-sm text-ink-muted">SMS reminders: {sms ? (sms.decision === "given" ? "agreed" : "declined") : "not asked"}</p>
      </div>

      {/* Mounted only while open, so every opening starts from a clean form. */}
      {panel === "details" && <EditDetails patient={patient} onClose={() => setPanel(null)} save={save} />}
      {panel === "phone" && <AddPhone patientId={patient.id} onClose={() => setPanel(null)} save={save} />}
      {panel === "identifier" && <AddIdentifier patientId={patient.id} onClose={() => setPanel(null)} save={save} />}
      {panel === "kin" && <AddKin patientId={patient.id} onClose={() => setPanel(null)} save={save} />}
      {panel === "notice" && <RecordNotice patientId={patient.id} onClose={() => setPanel(null)} save={save} />}
    </section>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt className="text-ink-muted">{label}</dt>
      <dd className="font-semibold">{children}</dd>
    </>
  );
}

function List({ title, empty, children }: { title: string; empty: string; children: ReactNode[] }) {
  return (
    <div className="flex flex-col gap-2">
      <h3 className="font-bold">{title}</h3>
      <ul className="flex flex-col divide-y divide-border-subtle border border-border-strong bg-surface">
        {children.length ? children : <li className="px-4 py-3 text-ink-muted">{empty}</li>}
      </ul>
    </div>
  );
}

type Save = (run: () => Promise<unknown>, done: string) => () => Promise<void>;

/** Dialog with a form: submit runs `onSubmit`; a thrown error is shown, the dialog stays open. */
function FormDialog({
  onClose,
  title,
  action,
  onSubmit,
  children,
}: {
  onClose: () => void;
  title: string;
  action: string;
  onSubmit: (data: FormData) => Promise<void> | string | undefined;
  children: ReactNode;
}) {
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(undefined);
    setSaving(true);
    try {
      const result = onSubmit(new FormData(event.currentTarget));
      if (typeof result === "string") setError(result);
      else await result;
    } catch (caught) {
      setError(failure(caught, "That did not work. Try again."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()} title={title}>
      <form method="post" onSubmit={submit} noValidate className="flex flex-col gap-4">
        {error && <Callout tone="danger" title={error} />}
        {children}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            {action}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

function EditDetails({ patient, onClose, save }: { patient: Patient; onClose: () => void; save: Save }) {
  const [sex, setSex] = useState(patient.sex);
  const [dob, setDob] = useState<DobValue>({ date: patient.date_of_birth, estimated: false });
  return (
    <FormDialog
      onClose={onClose}
      title="Edit details"
      action="Save details"
      onSubmit={(data) => {
        const text = (name: string) => String(data.get(name) ?? "").trim();
        if (!text("given_name") || !text("family_name")) return "Enter the given and family names.";
        if (!dob.date && patient.date_of_birth) return "Enter the date of birth as DD/MM/YYYY.";
        // Only a changed date is sent: an untouched estimated date stays estimated.
        const dobChanged = Boolean(dob.date) && dob.date !== patient.date_of_birth;
        return save(
          () =>
            unwrap(
              api.PATCH("/api/v1/patients/{id}/", {
                params: { path: { id: patient.id } },
                body: {
                  version: patient.version,
                  given_name: text("given_name"),
                  middle_name: text("middle_name"),
                  family_name: text("family_name"),
                  sex: sex as Schemas["PatchedPatientUpdateRequest"]["sex"],
                  ...(dobChanged ? { date_of_birth: dob.date, dob_estimated: false } : {}),
                },
              }),
            ),
          "Details saved",
        )();
      }}
    >
      <div className="grid gap-3 md:grid-cols-3">
        <Field label="Given name" required>
          {(control) => <TextInput {...control} name="given_name" defaultValue={patient.given_name} autoFocus autoComplete="off" />}
        </Field>
        <Field label="Middle name">
          {(control) => <TextInput {...control} name="middle_name" defaultValue={patient.middle_name} autoComplete="off" />}
        </Field>
        <Field label="Family name" required>
          {(control) => <TextInput {...control} name="family_name" defaultValue={patient.family_name} autoComplete="off" />}
        </Field>
      </div>
      <Field label="Sex" required>
        {(control) => <Select {...control} value={sex} onValueChange={(value) => setSex(value as Patient["sex"])} options={SEX_OPTIONS} />}
      </Field>
      <Field label="Date of birth" hint="DD/MM/YYYY">
        {(control) => <DateInput {...control} value={dob} onValueChange={setDob} allowEstimate={false} />}
      </Field>
    </FormDialog>
  );
}

function AddPhone({ patientId, onClose, save }: { patientId: string; onClose: () => void; save: Save }) {
  const [phone, setPhone] = useState<string | null>(null);
  const [primary, setPrimary] = useState(true);
  return (
    <FormDialog
      onClose={onClose}
      title="Add phone"
      action="Add phone"
      onSubmit={() => {
        if (!phone) return "Enter a Kenyan phone number, e.g. 0712 345 678.";
        return save(
          () => unwrap(api.POST("/api/v1/patients/{id}/contacts/", { params: { path: { id: patientId } }, body: { kind: "phone", value: phone, is_primary: primary } })),
          "Phone added",
        )();
      }}
    >
      <Field label="Phone" required hint="Kenyan mobile, e.g. 0712 345 678">
        {(control) => <PhoneInput {...control} value="" autoFocus onValueChange={(e164) => setPhone(e164)} />}
      </Field>
      <label className="inline-flex items-center gap-2 text-ink">
        <input type="checkbox" checked={primary} onChange={(event) => setPrimary(event.target.checked)} className="size-4 accent-primary" />
        Make this the main number (SMS and calls go here)
      </label>
    </FormDialog>
  );
}

function AddIdentifier({ patientId, onClose, save }: { patientId: string; onClose: () => void; save: Save }) {
  const [identifier, setIdentifier] = useState<IdentifierValue>({ type: "national_id", value: "" });
  return (
    <FormDialog
      onClose={onClose}
      title="Add identifier"
      action="Add identifier"
      onSubmit={() => {
        if (!identifier.value.trim()) return "Enter the number from the document.";
        return save(
          () =>
            unwrap(
              api.POST("/api/v1/patients/{id}/identifiers/", {
                params: { path: { id: patientId } },
                body: { type: identifier.type, value: identifier.value.trim(), issuer: "" },
              }),
            ),
          "Identifier added",
        )();
      }}
    >
      <Field label="Identifier" required>
        {(control) => <IdentifierInput {...control} value={identifier} onValueChange={setIdentifier} />}
      </Field>
    </FormDialog>
  );
}

function AddKin({ patientId, onClose, save }: { patientId: string; onClose: () => void; save: Save }) {
  const [phone, setPhone] = useState<string | null>(null);
  return (
    <FormDialog
      onClose={onClose}
      title="Add next of kin"
      action="Add next of kin"
      onSubmit={(data) => {
        const name = String(data.get("kin_name") ?? "").trim();
        const relationship = String(data.get("relationship") ?? "").trim();
        if (!name || !relationship) return "Enter the name and the relationship.";
        if (String(data.get("kin_phone") ?? "").trim() && !phone) return "Enter a Kenyan phone number, e.g. 0712 345 678.";
        return save(
          () =>
            unwrap(
              api.POST("/api/v1/patients/{id}/next-of-kin/", { params: { path: { id: patientId } }, body: { name, relationship, phone: phone ?? "" } }),
            ),
          "Next of kin added",
        )();
      }}
    >
      <Field label="Name" required>
        {(control) => <TextInput {...control} name="kin_name" autoFocus autoComplete="off" maxLength={120} />}
      </Field>
      <Field label="Relationship" required hint="e.g. mother, spouse, son">
        {(control) => <TextInput {...control} name="relationship" autoComplete="off" maxLength={40} />}
      </Field>
      <Field label="Phone">
        {(control) => <PhoneInput {...control} name="kin_phone" value="" onValueChange={(e164) => setPhone(e164)} />}
      </Field>
    </FormDialog>
  );
}

function RecordNotice({ patientId, onClose, save }: { patientId: string; onClose: () => void; save: Save }) {
  const [notice, setNotice] = useState<NoticeChoice>({ method: NOTICE_METHODS[0]!.value, given_by: NOTICE_GIVEN_TO[0]!.value, given: false });
  const text = useQuery({ queryKey: ["privacy-notice"], queryFn: () => unwrap(api.GET("/api/v1/patients/privacy-notice/")) });
  return (
    <FormDialog
      onClose={onClose}
      title="Record the privacy notice"
      action="Record the notice"
      onSubmit={() => {
        if (!notice.given) return "Give the privacy notice and tick to confirm.";
        return save(
          () =>
            unwrap(
              api.POST("/api/v1/patients/{id}/consents/", {
                params: { path: { id: patientId } },
                body: {
                  kind: "privacy_notice",
                  decision: "given",
                  version: text.data?.version ?? "",
                  method: notice.method as Schemas["ConsentInputRequest"]["method"],
                  given_by: notice.given_by as Schemas["ConsentInputRequest"]["given_by"],
                },
              }),
            ),
          "Privacy notice recorded",
        )();
      }}
    >
      <PrivacyNotice notice={text.data} value={notice} onChange={setNotice} />
    </FormDialog>
  );
}
