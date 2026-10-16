import { IDENTIFIER_TYPES } from "@/components/ui/inputs";

/** Labels and helpers shared by reception and the patient record (DESIGN §5, §6.1). */

export const SEX_OPTIONS = [
  { value: "female", label: "Female" },
  { value: "male", label: "Male" },
  { value: "intersex", label: "Intersex" },
  { value: "unknown", label: "Unknown" },
];

export const SEX_SHORT: Record<string, string> = { female: "F", male: "M", intersex: "Intersex", unknown: "Unknown" };

const ID_LABELS: Record<string, string> = {
  ...Object.fromEntries(IDENTIFIER_TYPES.map((t) => [t.value, t.label])),
  cr_id: "CR ID",
  temporary: "Temporary ID",
};

export function identifierLabel(type: string): string {
  return ID_LABELS[type] ?? type;
}

/** Identifier types the HIE Client Registry can be searched by (GAP-CR-001). */
export const REGISTRY_TYPES = IDENTIFIER_TYPES.filter((t) =>
  ["national_id", "maisha_namba", "alien_id", "refugee_id"].includes(t.value),
).map((t) => ({ value: t.value, label: t.label }));

export const NOTICE_METHODS = [
  { value: "verbal", label: "Read out or explained" },
  { value: "printed", label: "Printed notice given" },
  { value: "electronic", label: "Shown on screen or sent electronically" },
];

export const NOTICE_GIVEN_TO = [
  { value: "patient", label: "The patient" },
  { value: "guardian", label: "Parent or guardian" },
  { value: "representative", label: "Next of kin or representative" },
];

/** Last four characters only, for banners and lists (the full value stays in the record). */
export function maskIdentifier(value: string): string {
  return value.length <= 4 ? value : `••••${value.slice(-4)}`;
}

/** What the search box holds: an identifier or MRN (digits), a phone number, or a name. */
export function guessQuery(text: string): { kind: "phone" | "number" | "name"; value: string } {
  const value = text.trim();
  if (/^(\+?254|0)[17]\d{8}$/.test(value.replace(/[\s-]/g, ""))) return { kind: "phone", value };
  // Names never hold digits; anything with one is an identifier or MRN (SHA-…, CR-…, 99999-26-…).
  if (/\d/.test(value)) return { kind: "number", value: value.toUpperCase() };
  return { kind: "name", value };
}

/** Prefill for the registration form from what reception searched for (never stored). */
export function prefillFrom(text: string | undefined): {
  given_name: string;
  middle_name: string;
  family_name: string;
  phone: string;
  identifier: string;
} {
  const empty = { given_name: "", middle_name: "", family_name: "", phone: "", identifier: "" };
  if (!text) return empty;
  const guess = guessQuery(text);
  if (guess.kind === "phone") return { ...empty, phone: guess.value };
  if (guess.kind === "number") return { ...empty, identifier: guess.value };
  const parts = guess.value.split(/\s+/).filter(Boolean).map((p) => p[0]!.toUpperCase() + p.slice(1));
  if (parts.length === 1) return { ...empty, given_name: parts[0]! };
  return { ...empty, given_name: parts[0]!, middle_name: parts.slice(1, -1).join(" "), family_name: parts[parts.length - 1]! };
}

export const MATCH_REASONS: Record<string, string> = {
  identifier: "ID",
  phone: "phone",
  name: "name",
  date_of_birth: "date of birth",
  birth_year: "birth year",
  sex: "sex",
};
