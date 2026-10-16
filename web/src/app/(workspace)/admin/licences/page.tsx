"use client";

import { useQuery } from "@tanstack/react-query";

import { DataTable } from "@/components/ui/data-table";
import { Callout, StatusPill } from "@/components/ui/status";
import { api } from "@/lib/api/client";
import { rows, type Schemas, unwrap } from "@/lib/api/query";
import { formatDate } from "@/lib/format";

type Licence = Schemas["Licence"];

function expiry(validTo: string) {
  const days = Math.floor((new Date(`${validTo}T23:59:59+03:00`).getTime() - Date.now()) / 86_400_000);
  if (days < 0) return <StatusPill tone="danger">Expired</StatusPill>;
  if (days <= 30) return <StatusPill tone="warning">Expires in {days} days</StatusPill>;
  return <StatusPill tone="success">Valid</StatusPill>;
}

/** Practising licences at this facility; clinical permissions depend on them (DESIGN §7.10). */
export default function LicencesPage() {
  const licences = useQuery({
    queryKey: ["admin", "licences", "all"],
    queryFn: () => unwrap(api.GET("/api/v1/accounts/licences/", { params: { query: { page_size: 200 } as never } })),
  });
  return (
    <div className="flex flex-col gap-4">
      <p className="max-w-[75ch] text-ink-muted">
        Record and verify licences from a user&rsquo;s page under Users and roles. Expired licences switch off
        prescribing, ordering and full-record access until renewed.
      </p>
      {licences.isError && <Callout tone="danger" title="Licences could not be loaded." />}
      <DataTable
        caption="Practising licences"
        rows={rows<Licence>(licences.data)}
        rowKey={(l) => String(l.id)}
        empty={licences.isPending ? "Loading…" : "No licences recorded yet."}
        columns={[
          { key: "user", header: "User", cell: (l) => `#${l.user}`, sortValue: (l) => l.user },
          { key: "regulator", header: "Regulator", cell: (l) => l.regulator, sortValue: (l) => l.regulator },
          { key: "number", header: "Registration number", cell: (l) => <span className="tabular">{l.registration_number}</span> },
          { key: "valid", header: "Valid to", cell: (l) => formatDate(l.valid_to), sortValue: (l) => l.valid_to },
          { key: "state", header: "State", cell: (l) => expiry(l.valid_to) },
          { key: "verified", header: "Registry", cell: (l) => (l.verified_at ? "Verified" : "Not verified") },
        ]}
      />
    </div>
  );
}
