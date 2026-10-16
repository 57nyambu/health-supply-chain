"use client";

import * as RadixTabs from "@radix-ui/react-tabs";
import type { ReactNode } from "react";

/** Underline tabs, sentence case (DESIGN-SYSTEM §7). */
export function Tabs({ tabs, defaultValue, label }: { tabs: { value: string; label: string; content: ReactNode }[]; defaultValue?: string; label: string }) {
  return (
    <RadixTabs.Root defaultValue={defaultValue ?? tabs[0]?.value}>
      <RadixTabs.List aria-label={label} className="flex gap-1 border-b border-border-subtle">
        {tabs.map((tab) => (
          <RadixTabs.Trigger
            key={tab.value}
            value={tab.value}
            className="-mb-px border-b-2 border-transparent px-4 py-2 font-semibold text-ink-muted hover:text-ink data-[state=active]:border-primary data-[state=active]:text-ink"
          >
            {tab.label}
          </RadixTabs.Trigger>
        ))}
      </RadixTabs.List>
      {tabs.map((tab) => (
        <RadixTabs.Content key={tab.value} value={tab.value} className="pt-4">
          {tab.content}
        </RadixTabs.Content>
      ))}
    </RadixTabs.Root>
  );
}
