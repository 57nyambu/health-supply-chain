"use client";

import type { ReactNode } from "react";

import { FacilityAlerts, InventoryAlerts, StatsOverview } from "@/components/operations/operations";
import { Callout } from "@/components/ui/status";
import { Tabs } from "@/components/ui/tabs";
import { useMe } from "@/lib/auth/session";

/** Inventory: the legacy facility dashboard (daily figures, alerts, low stock) for store staff
 * (P1-WEB-06). Stock, batches, transfers and dispensing screens arrive with Phase 2. */
export default function InventoryPage() {
  const { data: me } = useMe();
  const can = (code: string) => me?.permissions.includes(code) ?? false;
  const tabs = [
    can("inventory.alert.read") && { value: "stock", label: "Low-stock alerts", content: <InventoryAlerts /> },
    can("operations.stats.read") && { value: "figures", label: "Daily figures", content: <StatsOverview /> },
    can("operations.alert.read") && { value: "alerts", label: "Facility alerts", content: <FacilityAlerts /> },
  ].filter(Boolean) as { value: string; label: string; content: ReactNode }[];

  return (
    <div className="flex flex-col gap-4 p-6">
      <h1 className="text-xl font-bold">Inventory</h1>
      <Callout tone="info" title="Stock, batches, transfers and dispensing screens arrive in Phase 2.">
        Until then this workspace shows low-stock alerts and the daily figures each store submits.
      </Callout>
      {me && tabs.length > 0 ? (
        <Tabs label="Inventory" tabs={tabs} />
      ) : me ? (
        <Callout tone="warning" title="None of these views are available to your roles." />
      ) : null}
    </div>
  );
}
