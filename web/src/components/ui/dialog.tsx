"use client";

import * as RadixDialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type DialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  /** When true, Esc and the close button ask before discarding unsaved clinical data. */
  dirty?: boolean;
  confirmDiscard?: () => boolean;
  size?: "md" | "lg";
};

/** Level-3 overlay, focus trapped; Esc closes unless it would lose unsaved work. */
export function Dialog({ open, onOpenChange, title, description, children, footer, dirty = false, confirmDiscard, size = "md" }: DialogProps) {
  const ask = confirmDiscard ?? (() => window.confirm("Discard the changes you have not saved?"));
  const request = (next: boolean) => {
    if (!next && dirty && !ask()) return;
    onOpenChange(next);
  };
  return (
    <RadixDialog.Root open={open} onOpenChange={request}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 z-40 bg-scrim" />
        <RadixDialog.Content
          className={cn(
            "fixed top-1/2 left-1/2 z-50 flex max-h-[90vh] -translate-x-1/2 -translate-y-1/2 flex-col rounded-overlay border border-border-strong bg-surface shadow-dialog",
            size === "lg" ? "w-[min(56rem,calc(100vw-2rem))]" : "w-[min(36rem,calc(100vw-2rem))]",
          )}
        >
          <div className="flex items-start justify-between gap-4 border-b border-border-subtle p-5">
            <div>
              <RadixDialog.Title className="text-lg font-bold text-ink">{title}</RadixDialog.Title>
              {description ? (
                <RadixDialog.Description className="mt-1 text-ink-muted">{description}</RadixDialog.Description>
              ) : (
                <RadixDialog.Description className="sr-only">{title}</RadixDialog.Description>
              )}
            </div>
            <RadixDialog.Close aria-label="Close" className="rounded-control p-1 text-ink hover:bg-surface-hover">
              <X aria-hidden className="size-5" />
            </RadixDialog.Close>
          </div>
          <div className="overflow-auto p-5">{children}</div>
          {footer && <div className="flex justify-end gap-2 border-t border-border-subtle p-4">{footer}</div>}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
