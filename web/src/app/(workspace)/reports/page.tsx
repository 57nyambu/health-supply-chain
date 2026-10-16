"use client";

import type { ReactNode } from "react";

import { FacilityAlerts, InventoryAlerts, StatsOverview } from "@/components/operations/operations";
import { Callout } from "@/components/ui/status";
import { Tabs } from "@/components/ui/tabs";
import { useMe } from "@/lib/auth/session";

/** Reports: facility operations as the legacy /admin and /reports dashboards showed them
 * (P1-WEB-06). The MOH registers and summaries (705A/B, 717…) arrive with Phase 2. */
export default function ReportsPage() {
  const { data: me } = useMe();
  const can = (code: string) => me?.permissions.includes(code) ?? false;
  const tabs = [
    can("operations.stats.read") && { value: "operations", label: "Facility operations", content: <StatsOverview /> },
    can("operations.alert.read") && { value: "alerts", label: "Facility alerts", content: <FacilityAlerts /> },
    can("inventory.alert.read") && { value: "stock", label: "Low-stock alerts", content: <InventoryAlerts /> },
  ].filter(Boolean) as { value: string; label: string; content: ReactNode }[];

  return (
    <div className="flex flex-col gap-4 p-6">
      <h1 className="text-xl font-bold">Reports</h1>
      <Callout tone="info" title="MOH reports (705A, 705B, 717 and others) arrive in Phase 2.">
        Until then this workspace shows daily facility operations and alerts.
      </Callout>
      {me && tabs.length > 0 ? (
        <Tabs label="Reports" tabs={tabs} />
      ) : me ? (
        <Callout tone="warning" title="None of these reports are available to your roles." />
      ) : null}
    </div>
  );
}
