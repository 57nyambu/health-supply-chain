"use client";

import { LoaderCircle } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

import { cn } from "@/lib/cn";

import { type ControlProps, controlClass } from "./field";
import type { Option } from "./select";

type ComboboxProps = Partial<ControlProps> & {
  /** Called (debounced) with the typed text; resolves to the options to show. */
  search: (text: string) => Promise<Option[]>;
  onSelect: (option: Option) => void;
  minLength?: number;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  "aria-label"?: string;
  debounceMs?: number;
};

/** Typeahead combobox (WAI-ARIA combobox pattern): ↑/↓ moves, Enter selects, Esc closes. */
export function Combobox({
  search,
  onSelect,
  minLength = 2,
  placeholder,
  disabled,
  className,
  debounceMs = 200,
  id,
  ...aria
}: ComboboxProps) {
  const listId = useId();
  const [text, setText] = useState("");
  const [options, setOptions] = useState<Option[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [loading, setLoading] = useState(false);
  const latest = useRef(0);
  // The text shown after a choice is the option's label, not a new search.
  const chosen = useRef<string | null>(null);

  useEffect(() => {
    if (text.trim().length < minLength || text === chosen.current) return;
    const request = ++latest.current;
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const found = await search(text.trim());
        if (request === latest.current) {
          setOptions(found);
          setActive(found.length ? 0 : -1);
          setOpen(true);
        }
      } finally {
        if (request === latest.current) setLoading(false);
      }
    }, debounceMs);
    return () => clearTimeout(timer);
  }, [text, minLength, search, debounceMs]);

  const choose = (option: Option) => {
    onSelect(option);
    const label = option.code ? `${option.code} ${option.label}` : option.label;
    chosen.current = label;
    setText(label);
    setOpen(false);
  };

  return (
    <div className={cn("relative", className)}>
      <input
        id={id}
        {...aria}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={open}
        aria-controls={listId}
        aria-activedescendant={open && active >= 0 ? `${listId}-${active}` : undefined}
        autoComplete="off"
        disabled={disabled}
        placeholder={placeholder}
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          if (event.target.value.trim().length < minLength) {
            latest.current += 1; // drop any search still in flight
            setOptions([]);
            setOpen(false);
          }
        }}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setOpen(true);
            setActive((i) => Math.min(i + 1, options.length - 1));
          } else if (event.key === "ArrowUp") {
            event.preventDefault();
            setActive((i) => Math.max(i - 1, 0));
          } else if (event.key === "Enter" && open && active >= 0 && options[active]) {
            event.preventDefault();
            choose(options[active]);
          } else if (event.key === "Escape") {
            setOpen(false);
          }
        }}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        className={controlClass(Boolean(aria["aria-invalid"]), "pr-10")}
      />
      {loading && (
        <LoaderCircle aria-label="Searching" className="absolute top-3 right-3 size-4 animate-spin text-ink-muted" />
      )}
      <ul
        id={listId}
        role="listbox"
        hidden={!open}
        className="absolute z-40 mt-1 max-h-80 w-full overflow-auto rounded-overlay border border-border-strong bg-surface p-1 shadow-menu"
      >
        {options.length === 0 ? (
          <li className="px-3 py-2 text-ink-muted" role="presentation">
            No matches
          </li>
        ) : (
          options.map((option, index) => (
            <li
              key={option.value}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={index === active}
              onMouseDown={(event) => {
                event.preventDefault();
                choose(option);
              }}
              className={cn("cursor-default rounded-control px-3 py-2 text-ink", index === active && "bg-selected")}
            >
              {option.code && <span className="tabular font-semibold">{option.code} </span>}
              {option.label}
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
