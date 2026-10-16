"use client";

import { useQuery } from "@tanstack/react-query";

import { DataTable } from "@/components/ui/data-table";
import { Callout, StatusPill } from "@/components/ui/status";
import { api } from "@/lib/api/client";
import { rows, type Schemas, unwrap } from "@/lib/api/query";
import { formatDate, formatDateTime } from "@/lib/format";

/** Facility operations: what the legacy /admin, /facility and /reports dashboards showed
 * (daily statistics, facility alerts, low-stock alerts), now inside the role workspaces. */

type Stats = Schemas["FacilityDailyStats"];
const STATS_KEY = ["operations", "stats"] as const;

const percent = (value: number | null | undefined) => (value === null || value === undefined ? "—" : `${value.toFixed(1)} %`);

const SEVERITY_TONE = { low: "neutral", medium: "warning", high: "danger" } as const;
const ALERT_TYPES: Record<string, string> = {
  understaffed: "Understaffed",
  low_footfall: "Low footfall",
  overcrowded: "Overcrowded",
  stockout_risk: "Stock-out risk",
  custom: "Other",
};

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="flex flex-col gap-1 border border-border-strong bg-surface p-4">
      <span className="text-sm text-ink-muted">{label}</span>
      <span className="tabular text-2xl font-bold text-ink">{value}</span>
      {hint && <span className="text-sm text-ink-muted">{hint}</span>}
    </div>
  );
}

/** The latest day per store as figures, then every day in a table, newest first. */
export function StatsOverview() {
  const stats = useQuery({ queryKey: STATS_KEY, queryFn: () => unwrap(api.GET("/api/v1/facility-ops/stats/")) });
  const list = [...rows<Stats>(stats.data)].sort((a, b) => b.date.localeCompare(a.date) || a.warehouse_name.localeCompare(b.warehouse_name));
  const latest = list[0];
  const week = list.filter((s) => s.warehouse === latest?.warehouse).slice(0, 7);
  const footfall = week.reduce((sum, s) => sum + (s.patient_footfall ?? 0), 0);

  if (stats.isError) return <Callout tone="danger" title="Daily statistics could not be loaded." />;
  return (
    <div className="flex flex-col gap-4">
      {latest ? (
        <div className="grid gap-3 md:grid-cols-4">
          <Kpi label={`Patients on ${formatDate(latest.date)}`} value={String(latest.patient_footfall ?? 0)} hint={latest.warehouse_name} />
          <Kpi label="Patients, last 7 days" value={String(footfall)} hint={`${week.length} days reported`} />
          <Kpi label="Bed occupancy" value={percent(latest.bed_occupancy_rate)} hint={`${latest.beds_occupied ?? 0} of ${latest.beds_total ?? 0} beds`} />
          <Kpi label="Doctors present" value={percent(latest.attendance_rate)} hint={`${latest.doctors_present ?? 0} of ${latest.doctors_scheduled ?? 0} scheduled`} />
        </div>
      ) : null}
      <DataTable
        caption="Daily statistics, newest first"
        density="compact"
        rows={list}
        rowKey={(s) => String(s.id)}
        empty={stats.isPending ? "Loading…" : "No daily statistics yet. Stores submit them at the end of each day."}
        columns={[
          { key: "date", header: "Date", cell: (s) => formatDate(s.date), sortValue: (s) => s.date },
          { key: "store", header: "Store or unit", cell: (s) => s.warehouse_name, sortValue: (s) => s.warehouse_name },
          { key: "footfall", header: "Patients", cell: (s) => s.patient_footfall ?? 0, numeric: true, sortValue: (s) => s.patient_footfall ?? 0 },
          { key: "beds", header: "Beds occupied", cell: (s) => `${s.beds_occupied ?? 0} / ${s.beds_total ?? 0}`, numeric: true },
          { key: "occupancy", header: "Occupancy", cell: (s) => percent(s.bed_occupancy_rate), numeric: true },
          { key: "doctors", header: "Doctors present", cell: (s) => `${s.doctors_present ?? 0} / ${s.doctors_scheduled ?? 0}`, numeric: true },
        ]}
      />
    </div>
  );
}

export function FacilityAlerts() {
  const alerts = useQuery({ queryKey: ["operations", "alerts"], queryFn: () => unwrap(api.GET("/api/v1/facility-ops/alerts/")) });
  const list = [...rows<Schemas["FacilityAlert"]>(alerts.data)].sort((a, b) => Number(a.resolved) - Number(b.resolved) || b.created_at.localeCompare(a.created_at));
  if (alerts.isError) return <Callout tone="danger" title="Facility alerts could not be loaded." />;
  return (
    <DataTable
      caption="Facility alerts, open first"
      rows={list}
      rowKey={(a) => String(a.id)}
      empty={alerts.isPending ? "Loading…" : "No facility alerts."}
      columns={[
        { key: "when", header: "Raised", cell: (a) => formatDateTime(a.created_at), sortValue: (a) => a.created_at },
        { key: "store", header: "Store or unit", cell: (a) => a.warehouse_name },
        { key: "type", header: "Alert", cell: (a) => ALERT_TYPES[a.alert_type] ?? a.alert_type },
        {
          key: "severity",
          header: "Severity",
          cell: (a) => <StatusPill tone={SEVERITY_TONE[(a.severity ?? "medium") as keyof typeof SEVERITY_TONE] ?? "neutral"}>{a.severity ?? "medium"}</StatusPill>,
        },
        { key: "message", header: "Details", cell: (a) => <span className="block max-w-[48ch]">{a.message}</span> },
        { key: "state", header: "State", cell: (a) => (a.resolved ? <StatusPill tone="success">Resolved</StatusPill> : <StatusPill tone="warning">Open</StatusPill>) },
      ]}
    />
  );
}

export function InventoryAlerts() {
  const alerts = useQuery({ queryKey: ["operations", "inventory-alerts"], queryFn: () => unwrap(api.GET("/api/v1/analytics/inventory-alerts/")) });
  const list = [...rows<Schemas["RTInventoryAlert"]>(alerts.data)].sort((a, b) => Number(a.resolved) - Number(b.resolved) || a.current_stock - b.current_stock);
  if (alerts.isError) return <Callout tone="danger" title="Low-stock alerts could not be loaded." />;
  return (
    <DataTable
      caption="Low-stock alerts, open first"
      rows={list}
      rowKey={(a) => String(a.id)}
      empty={alerts.isPending ? "Loading…" : "No low-stock alerts."}
      columns={[
        { key: "item", header: "Item", cell: (a) => a.product_name, sortValue: (a) => a.product_name },
        { key: "store", header: "Store", cell: (a) => a.warehouse_name },
        { key: "stock", header: "In stock", cell: (a) => a.current_stock, numeric: true, sortValue: (a) => a.current_stock },
        { key: "when", header: "Raised", cell: (a) => formatDateTime(a.created_at), sortValue: (a) => a.created_at },
        { key: "state", header: "State", cell: (a) => (a.resolved ? <StatusPill tone="success">Resolved</StatusPill> : <StatusPill tone="warning">Open</StatusPill>) },
      ]}
    />
  );
}
