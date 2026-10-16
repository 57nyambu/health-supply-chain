"use client";

import { useState } from "react";

import { JourneyRail } from "@/components/clinical/journey-rail";
import { BreakGlassBanner, PatientBanner } from "@/components/clinical/patient-banner";
import { Button } from "@/components/ui/button";
import { Combobox } from "@/components/ui/combobox";
import { DataTable } from "@/components/ui/data-table";
import { Dialog } from "@/components/ui/dialog";
import { Field, TextInput } from "@/components/ui/field";
import { DateInput, type DobValue, DoseInput, IdentifierInput, MoneyInput, PhoneInput } from "@/components/ui/inputs";
import { Select } from "@/components/ui/select";
import { Callout, StatusPill, TriageTag, triageRail } from "@/components/ui/status";
import { Tabs } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toast";
import { formatKES } from "@/lib/format";

// Synthetic examples only — this page never loads real data.
const ICD = [
  { value: "DA42.Z", code: "DA42.Z", label: "Gastritis, unspecified" },
  { value: "CA40.0", code: "CA40.0", label: "Bacterial pneumonia" },
  { value: "1F40.Z", code: "1F40.Z", label: "Malaria, unspecified" },
];
const QUEUE = [
  { id: "1", ticket: "C2-014", wait: 12, triage: "yellow" as const, amount: "1500" },
  { id: "2", ticket: "C2-015", wait: 4, triage: "green" as const, amount: "800" },
  { id: "3", ticket: "ER-007", wait: 1, triage: "red" as const, amount: "0" },
];
const TOKENS = [
  "canvas", "surface", "surface-sunken", "surface-hover", "selected", "ink", "ink-muted", "border-strong",
  "border-subtle", "primary", "primary-hover", "primary-tint", "danger", "danger-tint", "success", "success-tint",
  "warning", "warning-tint", "focus-outer",
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section aria-label={title} className="border-t border-border-subtle py-8">
      <h2 className="mb-4 text-lg font-bold">{title}</h2>
      {children}
    </section>
  );
}

export function Catalogue() {
  const toast = useToast();
  const [dialog, setDialog] = useState(false);
  const [money, setMoney] = useState<string | null>("1500.00");
  const [identifier, setIdentifier] = useState({ type: "national_id", value: "" });
  const [dob, setDob] = useState<DobValue>({ date: null, estimated: false });
  const [dose, setDose] = useState({ quantity: "500", unit: "mg", frequency: "three times daily", durationDays: "5" });
  const [payer, setPayer] = useState<string | undefined>("sha");
  const [selected, setSelected] = useState<string>();

  return (
    <main className="mx-auto max-w-6xl px-6 pb-16">
      <header className="py-8">
        <h1 className="text-xl font-bold">Design system</h1>
        <p className="mt-1 max-w-[75ch] text-ink-muted">
          Flat 2.0, high-contrast light (docs/agent/DESIGN-SYSTEM.md). Every example uses synthetic data.
        </p>
      </header>

      <Section title="Colour tokens">
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
          {TOKENS.map((token) => (
            <li key={token} className="flex items-center gap-2">
              <span aria-hidden className="size-8 rounded-control border border-border-strong" style={{ background: `var(--color-${token})` }} />
              <code className="text-sm">{token}</code>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Type">
        <p className="text-3xl font-bold">31 · 39 headline numbers</p>
        <p className="text-xl font-bold">Page title 25</p>
        <p className="text-lg font-bold">Section heading 20</p>
        <p>Body 16 — Il1 O0 rnm: confusable glyphs stay distinct.</p>
        <p className="text-sm text-ink-muted">Secondary 14 — the smallest size used.</p>
        <p className="tabular">Tabular figures: 1,111.11 / 8,888.88</p>
      </Section>

      <Section title="Buttons">
        <div className="flex flex-wrap gap-3">
          <Button>Open visit</Button>
          <Button variant="secondary">Record vitals</Button>
          <Button variant="quiet">Show history</Button>
          <Button variant="danger">Cancel order</Button>
          <Button variant="success">Release result</Button>
          <Button loading>Receive payment</Button>
          <Button disabled>Dispense</Button>
          <Button density="compact" variant="secondary">
            Compact
          </Button>
        </div>
      </Section>

      <Section title="Fields and inputs">
        <div className="grid gap-6 md:grid-cols-2">
          <Field label="Given name" required hint="As written on the identity document">
            {(control) => <TextInput {...control} />}
          </Field>
          <Field label="Family name" required error="Enter the family name.">
            {(control) => <TextInput {...control} />}
          </Field>
          <Field label="Amount" hint={money ? formatKES(money) : "Enter an amount"}>
            {(control) => <MoneyInput {...control} value="1500.00" onValueChange={setMoney} />}
          </Field>
          <Field label="Phone" hint="Kenyan numbers are stored as +254…">
            {(control) => <PhoneInput {...control} masked value="+254700000123" onValueChange={() => undefined} />}
          </Field>
          <Field label="Identifier">
            {(control) => <IdentifierInput {...control} value={identifier} onValueChange={setIdentifier} />}
          </Field>
          <Field label="Date of birth">
            {(control) => <DateInput {...control} value={dob} onValueChange={setDob} />}
          </Field>
          <Field label="Dose" className="md:col-span-2">
            {(control) => <DoseInput {...control} value={dose} onValueChange={setDose} />}
          </Field>
          <Field label="Payer">
            {(control) => (
              <Select
                {...control}
                value={payer}
                onValueChange={setPayer}
                options={[
                  { value: "cash", label: "Cash" },
                  { value: "sha", label: "SHA (SHIF)" },
                  { value: "smart", label: "Private insurer (SMART)" },
                ]}
              />
            )}
          </Field>
          <Field label="Diagnosis" hint="Type at least two characters">
            {(control) => (
              <Combobox
                {...control}
                search={async (text) => ICD.filter((o) => `${o.code} ${o.label}`.toLowerCase().includes(text.toLowerCase()))}
                onSelect={() => undefined}
              />
            )}
          </Field>
        </div>
      </Section>

      <Section title="Status, triage and callouts">
        <div className="flex flex-wrap gap-3">
          <StatusPill>Draft</StatusPill>
          <StatusPill tone="info">Placed</StatusPill>
          <StatusPill tone="success">Paid</StatusPill>
          <StatusPill tone="warning">Awaiting payment</StatusPill>
          <StatusPill tone="danger">Rejected</StatusPill>
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          {(["red", "orange", "yellow", "green", "blue"] as const).map((level) => (
            <TriageTag key={level} level={level} />
          ))}
          <TriageTag level="yellow" scale="paediatric" />
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <Callout tone="info" title="Eligibility pending">The Client Registry is slow; care continues.</Callout>
          <Callout tone="success" title="Payment received">Receipt R-000123 sent.</Callout>
          <Callout tone="warning" title="Allergies not recorded">Ask the patient before prescribing.</Callout>
          <Callout tone="danger" title="Critical value">Potassium 7.1 mmol/L — call the clinician now.</Callout>
        </div>
      </Section>

      <Section title="Data table">
        <DataTable
          caption="Patients waiting"
          columns={[
            { key: "ticket", header: "Ticket", cell: (r) => <span className="tabular font-semibold">{r.ticket}</span>, sortValue: (r) => r.ticket },
            { key: "triage", header: "Triage", cell: (r) => <TriageTag level={r.triage} /> },
            { key: "wait", header: "Wait (min)", cell: (r) => r.wait, numeric: true, sortValue: (r) => r.wait },
            { key: "amount", header: "Due (KES)", cell: (r) => formatKES(r.amount, { currency: false }), numeric: true },
          ]}
          rows={QUEUE}
          rowKey={(r) => r.id}
          selectedKey={selected}
          onOpen={(r) => setSelected(r.id)}
          empty="No patients waiting. New arrivals appear here when reception opens a visit."
        />
        <ul className="mt-4 w-80 border border-border-strong bg-surface">
          {QUEUE.map((r) => (
            <li key={r.id} style={triageRail(r.triage)} className="border-b border-border-subtle py-2 pr-3 pl-5 last:border-b-0">
              {r.ticket}
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Tabs">
        <Tabs
          label="Record sections"
          tabs={[
            { value: "summary", label: "Summary", content: <p>Allergies, alerts, active problems and medicines.</p> },
            { value: "documents", label: "Documents", content: <p>1 item hidden — sensitive category.</p> },
          ]}
        />
      </Section>

      <Section title="Toast and dialog">
        <div className="flex gap-3">
          <Button variant="secondary" onClick={() => toast({ title: "Result released", tone: "success" })}>
            Release result
          </Button>
          <Button variant="secondary" onClick={() => toast({ title: "Critical potassium", body: "Call the ward now.", tone: "danger", critical: true })}>
            Show critical toast
          </Button>
          <Button variant="secondary" onClick={() => setDialog(true)}>
            Open dialog
          </Button>
        </div>
        <Dialog
          open={dialog}
          onOpenChange={setDialog}
          title="Record vitals"
          description="Values are checked against plausible ranges."
          footer={
            <>
              <Button variant="secondary" onClick={() => setDialog(false)}>
                Cancel
              </Button>
              <Button onClick={() => setDialog(false)}>Save vitals</Button>
            </>
          }
        >
          <Field label="Temperature (°C)">{(control) => <TextInput {...control} inputMode="decimal" />}</Field>
        </Dialog>
      </Section>

      <Section title="Patient banner and journey rail">
        <div className="border border-border-strong">
          <PatientBanner
            patient={{
              displayName: "Synthetic Patient",
              sex: "female",
              dateOfBirth: "1990-04-12",
              mrn: "90001-26-000412",
              secondIdentifier: { label: "CR", value: "CR-SYN-…01" },
              allergies: { state: "recorded", items: ["Penicillin"] },
              alerts: ["Pregnant"],
              payer: { name: "SHA (SHIF)", status: "verified" },
            }}
          />
          <BreakGlassBanner expiresAt="2026-10-16T11:35:00Z" />
          <JourneyRail current="Consultation" onSelect={() => undefined} />
        </div>
        <div className="mt-4 border border-border-strong">
          <JourneyRail current="Triage" emergency />
        </div>
      </Section>
    </main>
  );
}
