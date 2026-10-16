"use client";

import { CircleAlert } from "lucide-react";
import { type InputHTMLAttributes, type ReactNode, useId } from "react";

import { cn } from "@/lib/cn";

export type ControlProps = {
  id: string;
  "aria-describedby"?: string;
  "aria-invalid"?: boolean;
  "aria-required"?: boolean;
};

type FieldProps = {
  label: string;
  hint?: string;
  error?: string;
  required?: boolean;
  className?: string;
  children: (control: ControlProps) => ReactNode;
};

/** Label above, hint and error below; never placeholder-as-label (DESIGN-SYSTEM §7). */
export function Field({ label, hint, error, required, className, children }: FieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <label htmlFor={id} className="font-semibold text-ink">
        {label}
        {required && <span className="font-normal text-ink-muted"> (required)</span>}
      </label>
      {children({
        id,
        "aria-describedby": describedBy,
        "aria-invalid": error ? true : undefined,
        "aria-required": required || undefined,
      })}
      {hint && (
        <p id={hintId} className="text-sm text-ink-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="flex items-start gap-1 text-sm font-semibold text-danger-ink">
          <CircleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
          {error}
        </p>
      )}
    </div>
  );
}

export const controlClass = (invalid?: boolean, extra?: string) =>
  cn(
    "h-10 rounded-control border bg-surface px-3 text-base text-ink",
    // Full width unless the caller sets a width (cn does not resolve conflicting utilities).
    !/(^|\s)w-/.test(extra ?? "") && "w-full",
    "disabled:border-border-strong disabled:bg-surface-sunken disabled:text-ink-disabled",
    // :read-only also matches <select>; only text fields that are read-only look sunken.
    "[&:is(input,textarea):read-only]:bg-surface-sunken",
    invalid ? "border-2 border-danger" : "border-border-strong",
    extra,
  );

export function TextInput({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={controlClass(Boolean(props["aria-invalid"]), className)} {...props} />;
}
