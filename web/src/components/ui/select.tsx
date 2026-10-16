"use client";

import * as RadixSelect from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";

import { cn } from "@/lib/cn";

import type { ControlProps } from "./field";

export type Option = { value: string; label: string; code?: string };

type SelectProps = Partial<ControlProps> & {
  value: string | undefined;
  onValueChange: (value: string) => void;
  options: Option[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  "aria-label"?: string;
};

/** Keyboard-selectable list; coded items show code + title (DESIGN-SYSTEM §7). */
export function Select({ value, onValueChange, options, placeholder = "Choose…", disabled, className, ...aria }: SelectProps) {
  return (
    <RadixSelect.Root value={value} onValueChange={onValueChange} disabled={disabled}>
      <RadixSelect.Trigger
        {...aria}
        className={cn(
          "inline-flex h-10 w-full items-center justify-between gap-2 rounded-control border bg-surface px-3 text-left text-ink",
          aria["aria-invalid"] ? "border-2 border-danger" : "border-border-strong",
          "data-[disabled]:bg-surface-sunken data-[disabled]:text-ink-disabled",
          className,
        )}
      >
        <RadixSelect.Value placeholder={<span className="text-ink-muted">{placeholder}</span>} />
        <RadixSelect.Icon>
          <ChevronDown aria-hidden className="size-4" />
        </RadixSelect.Icon>
      </RadixSelect.Trigger>
      <RadixSelect.Portal>
        <RadixSelect.Content
          position="popper"
          sideOffset={4}
          className="z-50 max-h-80 min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-overlay border border-border-strong bg-surface shadow-menu"
        >
          <RadixSelect.Viewport className="p-1">
            {options.map((option) => (
              <RadixSelect.Item
                key={option.value}
                value={option.value}
                className="relative flex cursor-default select-none items-center gap-2 rounded-control py-2 pr-8 pl-3 text-ink outline-none data-[highlighted]:bg-selected"
              >
                <RadixSelect.ItemText>
                  {option.code ? (
                    <>
                      <span className="tabular font-semibold">{option.code}</span> {option.label}
                    </>
                  ) : (
                    option.label
                  )}
                </RadixSelect.ItemText>
                <RadixSelect.ItemIndicator className="absolute right-2">
                  <Check aria-hidden className="size-4" />
                </RadixSelect.ItemIndicator>
              </RadixSelect.Item>
            ))}
          </RadixSelect.Viewport>
        </RadixSelect.Content>
      </RadixSelect.Portal>
    </RadixSelect.Root>
  );
}
