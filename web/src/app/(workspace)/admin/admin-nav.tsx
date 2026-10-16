"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useMe } from "@/lib/auth/session";
import { cn } from "@/lib/cn";

import { sectionsFor } from "./sections";

export function AdminNav() {
  const pathname = usePathname();
  const { data: me } = useMe();
  const sections = sectionsFor(me?.permissions ?? []);
  return (
    <nav aria-label="Administration sections" className="mt-3 flex flex-wrap gap-1">
      {sections.map((section) => {
        const active = pathname.startsWith(section.href);
        return (
          <Link
            key={section.href}
            href={section.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "-mb-px border-b-2 px-4 py-2 font-semibold",
              active ? "border-primary text-ink" : "border-transparent text-ink-muted hover:text-ink",
            )}
          >
            {section.label}
          </Link>
        );
      })}
    </nav>
  );
}
