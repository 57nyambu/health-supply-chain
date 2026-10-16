"use client";

import { Field } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { NOTICE_GIVEN_TO, NOTICE_METHODS } from "@/lib/patients";

export type NoticeChoice = { method: string; given_by: string; given: boolean };

/** The privacy notice reception gives at registration (Data Protection Act s.29; DESIGN §8.5). */
export function PrivacyNotice({
  notice,
  value,
  onChange,
  error,
}: {
  notice?: { version: string; text: string };
  value: NoticeChoice;
  onChange: (value: NoticeChoice) => void;
  error?: string;
}) {
  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="mb-2 font-bold">Privacy notice</legend>
      <div
        tabIndex={0}
        aria-label="Privacy notice text"
        className="max-h-40 overflow-auto whitespace-pre-line border border-border-subtle bg-surface-sunken p-3 text-sm text-ink"
      >
        {notice ? notice.text : "Loading the notice…"}
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <Field label="How it was given">
          {(control) => <Select {...control} value={value.method} onValueChange={(method) => onChange({ ...value, method })} options={NOTICE_METHODS} />}
        </Field>
        <Field label="Given to">
          {(control) => <Select {...control} value={value.given_by} onValueChange={(given_by) => onChange({ ...value, given_by })} options={NOTICE_GIVEN_TO} />}
        </Field>
      </div>
      <label className="inline-flex items-start gap-2 text-ink">
        <input
          type="checkbox"
          checked={value.given}
          onChange={(event) => onChange({ ...value, given: event.target.checked })}
          aria-invalid={Boolean(error) || undefined}
          aria-describedby={error ? "privacy-notice-error" : undefined}
          className="mt-1 size-4 accent-primary"
        />
        <span>
          I gave this privacy notice{notice ? ` (version ${notice.version})` : ""} and answered the patient&apos;s questions.
        </span>
      </label>
      {error && (
        <p id="privacy-notice-error" className="text-danger-ink">
          {error}
        </p>
      )}
    </fieldset>
  );
}
