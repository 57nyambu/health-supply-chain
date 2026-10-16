import { Slot } from "@radix-ui/react-slot";
import { LoaderCircle } from "lucide-react";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export type ButtonVariant = "primary" | "secondary" | "quiet" | "danger" | "success";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "border-primary bg-primary text-on-primary hover:border-primary-hover hover:bg-primary-hover",
  secondary: "border-border-strong bg-surface text-ink hover:bg-surface-hover",
  quiet: "border-transparent bg-transparent text-primary hover:underline",
  danger: "border-danger bg-danger text-on-primary hover:border-danger-ink hover:bg-danger-ink",
  success: "border-success bg-success text-on-primary hover:border-success-ink hover:bg-success-ink",
};

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  density?: "comfortable" | "compact";
  /** Keeps the button's width and shows a spinner with "Saving…" (or `loadingLabel`). */
  loading?: boolean;
  loadingLabel?: string;
  asChild?: boolean;
};

/** Labels are verbs: "Open visit", "Record vitals", "Receive payment" (DESIGN-SYSTEM §7). */
export function Button({
  variant = "primary",
  density = "comfortable",
  loading = false,
  loadingLabel = "Saving…",
  asChild = false,
  className,
  disabled,
  children,
  type,
  ...props
}: ButtonProps) {
  const Component = asChild ? Slot : "button";
  const inactive = disabled || loading;
  return (
    <Component
      type={asChild ? undefined : (type ?? "button")}
      disabled={asChild ? undefined : inactive}
      aria-disabled={inactive || undefined}
      aria-busy={loading || undefined}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-control border font-semibold",
        "transition-colors duration-[120ms] ease-state",
        density === "compact" ? "h-8 px-3 text-sm" : "h-10 px-4 text-base",
        inactive
          ? "cursor-not-allowed border-border-strong bg-surface-sunken text-ink-disabled"
          : VARIANTS[variant],
        className,
      )}
      {...props}
    >
      {asChild ? (
        children
      ) : (
        <span className="grid items-center">
          <span className={cn("col-start-1 row-start-1 inline-flex items-center gap-2", loading && "invisible")}>
            {children}
          </span>
          {loading && (
            <span className="col-start-1 row-start-1 inline-flex items-center justify-center gap-2">
              <LoaderCircle aria-hidden className="size-4 animate-spin" />
              {loadingLabel}
            </span>
          )}
        </span>
      )}
    </Component>
  );
}
