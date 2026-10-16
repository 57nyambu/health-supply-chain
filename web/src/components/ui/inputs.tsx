"use client";

import { type InputHTMLAttributes, useState } from "react";

import { cn } from "@/lib/cn";
import { formatDate, formatKES, maskPhone, normalisePhone, parseDate, parseKES } from "@/lib/format";

import { type ControlProps, controlClass } from "./field";

type Base = ControlProps & { disabled?: boolean; className?: string };

/** KES amount as the API's decimal string; right-aligned tabular figures, 2 dp on blur. */
export function MoneyInput({
  value,
  onValueChange,
  ...props
}: Base & { value: string; onValueChange: (value: string | null) => void } & Omit<
    InputHTMLAttributes<HTMLInputElement>,
    "value" | "onChange"
  >) {
  const [text, setText] = useState(value ? formatKES(value, { currency: false }) : "");
  return (
    <div className="relative">
      <span aria-hidden className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-ink-muted">
        KES
      </span>
      <input
        {...props}
        inputMode="decimal"
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          onValueChange(parseKES(event.target.value));
        }}
        onBlur={() => {
          const parsed = parseKES(text);
          if (parsed) setText(formatKES(parsed, { currency: false }));
        }}
        className={controlClass(Boolean(props["aria-invalid"]), cn("tabular pl-12 text-right", props.className))}
      />
    </div>
  );
}

/** Kenyan phone, normalised to E.164 (+254…); shows the masked number when not editing. */
export function PhoneInput({
  value,
  onValueChange,
  masked = false,
  ...props
}: Base & { value: string; onValueChange: (e164: string | null, raw: string) => void; masked?: boolean } & Omit<
    InputHTMLAttributes<HTMLInputElement>,
    "value" | "onChange"
  >) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(value);
  const shown = masked && !editing && normalisePhone(text) ? maskPhone(normalisePhone(text)!) : text;
  return (
    <input
      {...props}
      type="tel"
      inputMode="tel"
      autoComplete="off"
      value={shown}
      onFocus={() => setEditing(true)}
      onBlur={() => {
        setEditing(false);
        const e164 = normalisePhone(text);
        if (e164) setText(e164);
      }}
      onChange={(event) => {
        setText(event.target.value);
        onValueChange(normalisePhone(event.target.value), event.target.value);
      }}
      className={controlClass(Boolean(props["aria-invalid"]), cn("tabular", props.className))}
    />
  );
}

export const IDENTIFIER_TYPES = [
  { value: "national_id", label: "National ID", hint: "6–9 digits" },
  { value: "maisha_namba", label: "Maisha Namba", hint: "9–12 digits" },
  { value: "sha_number", label: "SHA number", hint: "letters, digits and dashes" },
  { value: "cr_id", label: "Client Registry ID", hint: "starts with CR" },
  { value: "alien_id", label: "Alien ID", hint: "6–10 digits" },
  { value: "refugee_id", label: "Refugee ID", hint: "letters, digits and dashes" },
  { value: "passport", label: "Passport", hint: "6–12 letters or digits" },
  { value: "birth_certificate", label: "Birth certificate", hint: "6–12 digits" },
  { value: "birth_notification", label: "Birth notification", hint: "letters, digits and dashes" },
] as const;

export type IdentifierValue = { type: string; value: string };

/** Identifier type + number; the API validates the format and never echoes it in errors. */
export function IdentifierInput({
  value,
  onValueChange,
  id,
  disabled,
  ...aria
}: Base & { value: IdentifierValue; onValueChange: (value: IdentifierValue) => void }) {
  const type = IDENTIFIER_TYPES.find((t) => t.value === value.type);
  return (
    <div className="flex gap-2">
      <select
        aria-label="Identifier type"
        disabled={disabled}
        value={value.type}
        onChange={(event) => onValueChange({ ...value, type: event.target.value })}
        className={controlClass(false, "w-48 shrink-0")}
      >
        {IDENTIFIER_TYPES.map((t) => (
          <option key={t.value} value={t.value}>
            {t.label}
          </option>
        ))}
      </select>
      <input
        id={id}
        {...aria}
        disabled={disabled}
        autoComplete="off"
        spellCheck={false}
        value={value.value}
        title={type?.hint}
        onChange={(event) => onValueChange({ ...value, value: event.target.value.toUpperCase() })}
        className={controlClass(Boolean(aria["aria-invalid"]), "tabular")}
      />
    </div>
  );
}

export type DobValue = { date: string | null; estimated: boolean; years?: number; months?: number };

/** DD/MM/YYYY typed entry, or an estimated date of birth from age in years and months. */
export function DateInput({
  value,
  onValueChange,
  allowEstimate = true,
  id,
  disabled,
  ...aria
}: Base & { value: DobValue; onValueChange: (value: DobValue) => void; allowEstimate?: boolean }) {
  const [text, setText] = useState(value.date ? formatDate(value.date) : "");
  return (
    <div className="flex flex-col gap-2">
      {!value.estimated ? (
        <input
          id={id}
          {...aria}
          disabled={disabled}
          inputMode="numeric"
          placeholder="DD/MM/YYYY"
          value={text}
          onChange={(event) => {
            setText(event.target.value);
            onValueChange({ date: parseDate(event.target.value), estimated: false });
          }}
          className={controlClass(Boolean(aria["aria-invalid"]), "tabular w-40")}
        />
      ) : (
        <div className="flex items-center gap-2" role="group" aria-labelledby={id ? `${id}-age` : undefined}>
          <span id={id ? `${id}-age` : undefined} className="sr-only">
            Age
          </span>
          <input
            id={id}
            {...aria}
            disabled={disabled}
            aria-label="Age in years"
            inputMode="numeric"
            value={value.years ?? ""}
            onChange={(event) => onValueChange({ ...value, date: null, years: Number(event.target.value) || 0 })}
            className={controlClass(Boolean(aria["aria-invalid"]), "tabular w-20 text-right")}
          />
          <span className="text-ink-muted">years</span>
          <input
            aria-label="Age in months"
            disabled={disabled}
            inputMode="numeric"
            value={value.months ?? ""}
            onChange={(event) => onValueChange({ ...value, date: null, months: Number(event.target.value) || 0 })}
            className={controlClass(false, "tabular w-20 text-right")}
          />
          <span className="text-ink-muted">months</span>
        </div>
      )}
      {allowEstimate && (
        <label className="inline-flex items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            disabled={disabled}
            checked={value.estimated}
            onChange={(event) => onValueChange({ date: null, estimated: event.target.checked })}
            className="size-4 accent-primary"
          />
          Date of birth unknown — enter the age instead
        </label>
      )}
    </div>
  );
}

export type DoseValue = { quantity: string; unit: string; frequency: string; durationDays: string };

const DOSE_UNITS = ["mg", "g", "microgram", "mL", "tablet", "capsule", "units", "puff", "drop"];
const FREQUENCIES = ["once daily", "twice daily", "three times daily", "four times daily", "every 8 hours", "at night", "when needed"];

/** Quantity + unit + frequency + duration. Error-prone abbreviations (U, QD) are not offered. */
export function DoseInput({
  value,
  onValueChange,
  id,
  disabled,
  ...aria
}: Base & { value: DoseValue; onValueChange: (value: DoseValue) => void }) {
  const set = (patch: Partial<DoseValue>) => onValueChange({ ...value, ...patch });
  return (
    <div className="flex flex-wrap items-center gap-2">
      <input
        id={id}
        {...aria}
        disabled={disabled}
        aria-label="Dose quantity"
        inputMode="decimal"
        value={value.quantity}
        onChange={(event) => set({ quantity: event.target.value })}
        className={controlClass(Boolean(aria["aria-invalid"]), "tabular w-24 text-right")}
      />
      <select aria-label="Dose unit" disabled={disabled} value={value.unit} onChange={(event) => set({ unit: event.target.value })} className={controlClass(false, "w-32")}>
        {DOSE_UNITS.map((u) => (
          <option key={u}>{u}</option>
        ))}
      </select>
      <select aria-label="Frequency" disabled={disabled} value={value.frequency} onChange={(event) => set({ frequency: event.target.value })} className={controlClass(false, "w-48")}>
        {FREQUENCIES.map((f) => (
          <option key={f}>{f}</option>
        ))}
      </select>
      <span className="text-ink-muted">for</span>
      <input
        aria-label="Duration in days"
        disabled={disabled}
        inputMode="numeric"
        value={value.durationDays}
        onChange={(event) => set({ durationDays: event.target.value })}
        className={controlClass(false, "tabular w-20 text-right")}
      />
      <span className="text-ink-muted">days</span>
    </div>
  );
}
