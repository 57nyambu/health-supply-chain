"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { ReasonDialog } from "@/components/ui/reason-dialog";
import { Callout, StatusPill } from "@/components/ui/status";
import { Tabs } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, problemMessage } from "@/lib/api/client";
import { rows, type Schemas, unwrap } from "@/lib/api/query";
import { formatDateTime } from "@/lib/format";

type Grant = Schemas["BreakGlass"];

const REASONS: Record<string, string> = {
  emergency: "Emergency",
  continuity_of_care: "Continuity of care",
  clinical_review: "Clinical review",
};

/** Every break-glass grant is reviewed: justified, or escalated with a note (DESIGN §7.8). */
export default function BreakGlassPage() {
  return (
    <Tabs
      label="Break-glass reviews"
      tabs={[
        { value: "pending", label: "Waiting for review", content: <Queue status="pending" /> },
        { value: "reviewed", label: "Escalated", content: <Queue status="escalated" /> },
        { value: "justified", label: "Justified", content: <Queue status="justified" /> },
      ]}
    />
  );
}

function Queue({ status }: { status: "pending" | "escalated" | "justified" }) {
  const client = useQueryClient();
  const toast = useToast();
  const [escalating, setEscalating] = useState<Grant>();
  const grants = useQuery({
    queryKey: ["admin", "break-glass", status],
    queryFn: () => unwrap(api.GET("/api/v1/access/break-glass/", { params: { query: { review_status: status } as never } })),
  });
  const refresh = () => client.invalidateQueries({ queryKey: ["admin", "break-glass"] });

  async function justify(grant: Grant) {
    try {
      await unwrap(api.POST("/api/v1/access/break-glass/{id}/review/", { params: { path: { id: grant.id } }, body: { outcome: "justified", note: "" } }));
      await refresh();
      toast({ title: "Marked justified", tone: "success" });
    } catch (caught) {
      toast({ title: caught instanceof ApiError ? problemMessage(caught.problem) : "Could not record the review.", tone: "danger" });
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {grants.isError && <Callout tone="danger" title="The review queue could not be loaded." />}
      <DataTable
        caption={`Break-glass grants: ${status}`}
        rows={rows<Grant>(grants.data)}
        rowKey={(g) => g.id}
        empty={grants.isPending ? "Loading…" : "Nothing here."}
        columns={[
          { key: "when", header: "Granted", cell: (g) => formatDateTime(g.granted_at), sortValue: (g) => g.granted_at },
          { key: "who", header: "Clinician", cell: (g) => g.user_name },
          { key: "reason", header: "Reason", cell: (g) => REASONS[g.reason] ?? g.reason },
          { key: "why", header: "Justification", cell: (g) => <span className="block max-w-[40ch]">{g.justification}</span> },
          {
            key: "review",
            header: status === "pending" ? "Review" : "Note",
            cell: (g) =>
              status === "pending" ? (
                <div className="flex gap-2">
                  <Button density="compact" variant="success" onClick={() => justify(g)}>
                    Justified
                  </Button>
                  <Button density="compact" variant="danger" onClick={() => setEscalating(g)}>
                    Escalate
                  </Button>
                </div>
              ) : (
                <>
                  <StatusPill tone={status === "escalated" ? "danger" : "success"}>{status === "escalated" ? "Escalated" : "Justified"}</StatusPill>
                  {g.review_note && <span className="ml-2 text-sm">{g.review_note}</span>}
                </>
              ),
          },
        ]}
      />
      <ReasonDialog
        open={Boolean(escalating)}
        onOpenChange={(open) => !open && setEscalating(undefined)}
        title="Escalate break-glass access"
        description="Say what needs investigating. The data protection officer follows escalated grants up."
        label="Note"
        action="Escalate"
        variant="danger"
        onConfirm={async (note) => {
          if (!escalating) return;
          await unwrap(api.POST("/api/v1/access/break-glass/{id}/review/", { params: { path: { id: escalating.id } }, body: { outcome: "escalated", note } }));
          await refresh();
          toast({ title: "Escalated", tone: "success" });
        }}
      />
    </div>
  );
}
