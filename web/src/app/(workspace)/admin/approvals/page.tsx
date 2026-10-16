"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { ReasonDialog } from "@/components/ui/reason-dialog";
import { Callout, StatusPill } from "@/components/ui/status";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, problemMessage } from "@/lib/api/client";
import { rows, type Schemas, unwrap } from "@/lib/api/query";
import { useMe } from "@/lib/auth/session";
import { formatDateTime } from "@/lib/format";

type Approval = Schemas["Approval"];

const ACTIONS: Record<string, string> = {
  "access.assignment.grant": "Privileged role grant",
  "patients.merge": "Patient record merge",
  "patients.unmerge": "Reverse a patient merge",
};

/** Maker-checker inbox (DESIGN §7.9): nobody approves their own request (the API refuses). */
export default function ApprovalsPage() {
  const client = useQueryClient();
  const toast = useToast();
  const { data: me } = useMe();
  const [rejecting, setRejecting] = useState<Approval>();
  const approvals = useQuery({
    queryKey: ["admin", "approvals"],
    queryFn: () => unwrap(api.GET("/api/v1/access/approvals/", { params: { query: { status: "pending" } as never } })),
  });
  const refresh = () => client.invalidateQueries({ queryKey: ["admin", "approvals"] });

  async function approve(approval: Approval) {
    try {
      await unwrap(api.POST("/api/v1/access/approvals/{id}/approve/", { params: { path: { id: approval.id } }, body: { comment: "" } }));
      await refresh();
      toast({ title: "Request approved", tone: "success" });
    } catch (caught) {
      toast({ title: caught instanceof ApiError ? problemMessage(caught.problem) : "Could not approve.", tone: "danger" });
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="max-w-[75ch] text-ink-muted">
        Requests that need a second person. You can decide requests made by others; your own wait for a colleague.
      </p>
      {approvals.isError && <Callout tone="danger" title="Approvals could not be loaded." />}
      <DataTable
        caption="Requests waiting for a decision"
        rows={rows<Approval>(approvals.data)}
        rowKey={(a) => a.id}
        empty={approvals.isPending ? "Loading…" : "Nothing is waiting for a decision."}
        columns={[
          { key: "action", header: "Request", cell: (a) => ACTIONS[a.action] ?? a.action },
          { key: "reason", header: "Reason", cell: (a) => a.reason },
          {
            key: "by",
            header: "Requested",
            cell: (a) => (
              <>
                {formatDateTime(a.requested_at)}
                {a.requested_by === me?.id && <span className="ml-2"><StatusPill tone="info">Yours</StatusPill></span>}
              </>
            ),
            sortValue: (a) => a.requested_at,
          },
          { key: "expires", header: "Expires", cell: (a) => formatDateTime(a.expires_at) },
          {
            key: "decide",
            header: "Decision",
            cell: (a) =>
              a.requested_by === me?.id ? (
                <span className="text-ink-muted">Waiting for a colleague</span>
              ) : (
                <div className="flex gap-2">
                  <Button density="compact" variant="success" onClick={() => approve(a)}>
                    Approve
                  </Button>
                  <Button density="compact" variant="secondary" onClick={() => setRejecting(a)}>
                    Reject
                  </Button>
                </div>
              ),
          },
        ]}
      />
      <ReasonDialog
        open={Boolean(rejecting)}
        onOpenChange={(open) => !open && setRejecting(undefined)}
        title="Reject request"
        label="Comment"
        action="Reject"
        variant="danger"
        onConfirm={async (comment) => {
          if (!rejecting) return;
          await unwrap(api.POST("/api/v1/access/approvals/{id}/reject/", { params: { path: { id: rejecting.id } }, body: { comment } }));
          await refresh();
          toast({ title: "Request rejected", tone: "success" });
        }}
      />
    </div>
  );
}
