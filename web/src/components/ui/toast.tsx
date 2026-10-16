"use client";

import * as RadixToast from "@radix-ui/react-toast";
import { X } from "lucide-react";
import { createContext, type ReactNode, useCallback, useContext, useState } from "react";

import { cn } from "@/lib/cn";

type ToastItem = { id: number; title: string; body?: string; tone: "info" | "success" | "danger"; critical: boolean };
type Notify = (toast: Omit<ToastItem, "id" | "critical" | "tone"> & Partial<Pick<ToastItem, "critical" | "tone">>) => void;

const ToastContext = createContext<Notify>(() => undefined);

/** `const toast = useToast(); toast({ title: "Result released" })` — repeat the action verb. */
export function useToast(): Notify {
  return useContext(ToastContext);
}

const RAIL = { info: "border-l-primary", success: "border-l-success", danger: "border-l-danger" };

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const notify = useCallback<Notify>((toast) => {
    setItems((current) => [
      ...current,
      { id: Date.now() + Math.random(), tone: "info", critical: false, ...toast },
    ]);
  }, []);
  const remove = (id: number) => setItems((current) => current.filter((t) => t.id !== id));
  // Radix's provider wraps only the toasts (a sibling after the page), so it never shifts
  // the useId paths of the page itself between server and client renders.
  return (
    <ToastContext.Provider value={notify}>
      {children}
      <RadixToast.Provider swipeDirection="right" duration={5000}>
        {items.map((item) => (
          <RadixToast.Root
            key={item.id}
            // Critical toasts persist until dismissed (DESIGN-SYSTEM §7).
            duration={item.critical ? Infinity : 5000}
            type={item.critical ? "foreground" : "background"}
            onOpenChange={(open) => !open && remove(item.id)}
            className={cn(
              "flex items-start gap-3 rounded-overlay border border-border-strong border-l-4 bg-surface p-4 shadow-menu",
              RAIL[item.tone],
            )}
          >
            <div className="flex-1">
              <RadixToast.Title className="font-semibold text-ink">{item.title}</RadixToast.Title>
              {item.body && <RadixToast.Description className="mt-1 text-ink-muted">{item.body}</RadixToast.Description>}
            </div>
            <RadixToast.Close aria-label="Dismiss" className="rounded-control p-1 text-ink hover:bg-surface-hover">
              <X aria-hidden className="size-4" />
            </RadixToast.Close>
          </RadixToast.Root>
        ))}
        <RadixToast.Viewport className="fixed right-4 bottom-4 z-50 flex w-96 max-w-[calc(100vw-2rem)] flex-col gap-2 outline-none" />
      </RadixToast.Provider>
    </ToastContext.Provider>
  );
}
