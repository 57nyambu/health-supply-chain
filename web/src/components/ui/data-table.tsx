"use client";

import { ArrowDown, ArrowUp } from "lucide-react";
import { type KeyboardEvent, type ReactNode, useMemo, useRef, useState } from "react";

import { cn } from "@/lib/cn";

export type Column<Row> = {
  key: string;
  header: string;
  cell: (row: Row) => ReactNode;
  /** Right-aligned tabular figures (amounts, counts, vitals). */
  numeric?: boolean;
  /** Value used for sorting; columns without it are not sortable. */
  sortValue?: (row: Row) => string | number;
};

type DataTableProps<Row> = {
  caption: string;
  columns: Column<Row>[];
  rows: Row[];
  rowKey: (row: Row) => string;
  onOpen?: (row: Row) => void;
  selectedKey?: string;
  /** Empty state that invites the next action (DESIGN-SYSTEM §9). */
  empty: ReactNode;
  density?: "comfortable" | "compact";
};

/** Sticky header, row hover, selection rail, ↑/↓ + Enter keyboard navigation, column sort. */
export function DataTable<Row>({ caption, columns, rows, rowKey, onOpen, selectedKey, empty, density = "comfortable" }: DataTableProps<Row>) {
  const [sort, setSort] = useState<{ key: string; direction: "asc" | "desc" } | null>(null);
  const body = useRef<HTMLTableSectionElement>(null);

  const sorted = useMemo(() => {
    const column = columns.find((c) => c.key === sort?.key);
    if (!sort || !column?.sortValue) return rows;
    const value = column.sortValue;
    return [...rows].sort((a, b) => {
      const [x, y] = [value(a), value(b)];
      const order = x < y ? -1 : x > y ? 1 : 0;
      return sort.direction === "asc" ? order : -order;
    });
  }, [rows, columns, sort]);

  const onKeyDown = (event: KeyboardEvent<HTMLTableRowElement>, row: Row) => {
    const rowsEls = Array.from(body.current?.querySelectorAll<HTMLTableRowElement>("tr[tabindex]") ?? []);
    const index = rowsEls.indexOf(event.currentTarget);
    if (event.key === "ArrowDown") {
      event.preventDefault();
      rowsEls[Math.min(index + 1, rowsEls.length - 1)]?.focus();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      rowsEls[Math.max(index - 1, 0)]?.focus();
    } else if (event.key === "Enter" && onOpen) {
      event.preventDefault();
      onOpen(row);
    }
  };

  const pad = density === "compact" ? "px-3 py-1.5" : "px-4 py-2.5";
  return (
    <div className="overflow-auto border border-border-strong bg-surface">
      <table className="w-full border-collapse text-left">
        <caption className="sr-only">{caption}</caption>
        <thead className="sticky top-0 bg-surface-sunken shadow-sticky">
          <tr>
            {columns.map((column) => {
              const active = sort?.key === column.key;
              return (
                <th
                  key={column.key}
                  scope="col"
                  aria-sort={active ? (sort.direction === "asc" ? "ascending" : "descending") : undefined}
                  className={cn("font-semibold text-ink", pad, column.numeric && "text-right")}
                >
                  {column.sortValue ? (
                    <button
                      type="button"
                      className="inline-flex items-center gap-1 rounded-control font-semibold"
                      onClick={() =>
                        setSort(
                          active && sort.direction === "asc"
                            ? { key: column.key, direction: "desc" }
                            : { key: column.key, direction: "asc" },
                        )
                      }
                    >
                      {column.header}
                      {active &&
                        (sort.direction === "asc" ? (
                          <ArrowUp aria-hidden className="size-4" />
                        ) : (
                          <ArrowDown aria-hidden className="size-4" />
                        ))}
                    </button>
                  ) : (
                    column.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody ref={body}>
          {sorted.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-ink-muted">
                {empty}
              </td>
            </tr>
          ) : (
            sorted.map((row) => {
              const key = rowKey(row);
              const selected = key === selectedKey;
              return (
                <tr
                  key={key}
                  tabIndex={0}
                  aria-selected={onOpen ? selected : undefined}
                  onKeyDown={(event) => onKeyDown(event, row)}
                  onDoubleClick={onOpen ? () => onOpen(row) : undefined}
                  className={cn(
                    "border-t border-border-subtle hover:bg-surface-hover",
                    selected && "bg-selected shadow-[inset_4px_0_0_var(--color-primary)]",
                  )}
                >
                  {columns.map((column) => (
                    <td key={column.key} className={cn("text-ink", pad, column.numeric && "tabular text-right")}>
                      {column.cell(row)}
                    </td>
                  ))}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
