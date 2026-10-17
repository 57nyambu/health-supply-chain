"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { Dialog } from "@/components/ui/dialog";
import { Field, TextInput } from "@/components/ui/field";
import { Callout, StatusPill } from "@/components/ui/status";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, problemMessage } from "@/lib/api/client";
import { rows, type Schemas, unwrap } from "@/lib/api/query";
import { formatDateTime } from "@/lib/format";

type Board = Schemas["Board"];

/** TV queue boards (P2-VIS-03): ticket numbers and rooms only. Each board has its own device
 * link, shown once; revoking it stops that TV at once (ADR-042). */
export default function BoardsPage() {
  const client = useQueryClient();
  const toast = useToast();
  const [creating, setCreating] = useState(false);
  const [link, setLink] = useState<string | null>(null);
  const boards = useQuery({ queryKey: ["visits", "boards"], queryFn: () => unwrap(api.GET("/api/v1/visits/boards/")) });
  const points = useQuery({ queryKey: ["service-points"], queryFn: () => unwrap(api.GET("/api/v1/facilities/service-points/")) });
  const pointName = new Map(rows(points.data).map((p) => [p.id, p.name]));
  const refresh = () => client.invalidateQueries({ queryKey: ["visits", "boards"] });

  async function revoke(board: Board) {
    try {
      await unwrap(api.POST("/api/v1/visits/boards/{id}/revoke/", { params: { path: { id: board.id } } }));
      toast({ title: "Board link revoked", tone: "success" });
      await refresh();
    } catch (caught) {
      toast({ title: caught instanceof ApiError ? problemMessage(caught.problem) : "Could not revoke.", tone: "danger" });
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <p className="mr-auto max-w-[75ch] text-ink-muted">Boards show ticket numbers and rooms, never names.</p>
        <Button onClick={() => setCreating(true)}>Set up a board</Button>
      </div>
      {link && (
        <Callout tone="success" title="Open this link on the TV now. It is shown only once.">
          <p className="tabular font-semibold break-all">{link}</p>
        </Callout>
      )}
      <DataTable
        caption="Queue boards"
        rows={boards.data ?? []}
        rowKey={(b) => b.id}
        empty={boards.isPending ? "Loading…" : "No boards yet. Set one up for each waiting area."}
        columns={[
          { key: "name", header: "Board", cell: (b) => b.name },
          { key: "points", header: "Service points", cell: (b) => b.service_points.map((id) => pointName.get(id) ?? id).join(", ") },
          { key: "seen", header: "Last seen", cell: (b) => (b.last_seen_at ? formatDateTime(b.last_seen_at) : "Never") },
          {
            key: "state",
            header: "State",
            cell: (b) => <StatusPill tone={b.active ? "success" : "neutral"}>{b.active ? "Active" : "Revoked"}</StatusPill>,
          },
          {
            key: "actions",
            header: "Actions",
            cell: (b) =>
              b.active ? (
                <Button density="compact" variant="secondary" onClick={() => revoke(b)}>
                  Revoke
                </Button>
              ) : null,
          },
        ]}
      />
      {creating && (
        <CreateDialog
          points={rows(points.data).filter((p) => p.active)}
          onClose={() => setCreating(false)}
          onCreated={async (token) => {
            setLink(`${window.location.origin}/board#${token}`);
            await refresh();
          }}
        />
      )}
    </div>
  );
}

function CreateDialog({
  points,
  onClose,
  onCreated,
}: {
  points: Schemas["ServicePoint"][];
  onClose: () => void;
  onCreated: (token: string) => Promise<unknown>;
}) {
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") ?? "").trim();
    const chosen = form.getAll("point").map(Number);
    if (!name || chosen.length === 0) return setError("Name the board and choose at least one service point.");
    setSaving(true);
    try {
      const created = await unwrap(api.POST("/api/v1/visits/boards/", { body: { name, service_points: chosen } }));
      await onCreated(created.token);
      onClose();
    } catch (caught) {
      setError(caught instanceof ApiError ? problemMessage(caught.problem) : "That did not work. Try again.");
    } finally {
      setSaving(false);
    }
  }
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()} title="Set up a queue board">
      <form method="post" onSubmit={save} noValidate className="flex flex-col gap-4">
        {error && <Callout tone="danger" title={error} />}
        <Field label="Board name" required>
          {(control) => <TextInput {...control} name="name" maxLength={80} />}
        </Field>
        <fieldset className="flex flex-col gap-2">
          <legend className="font-semibold">Service points shown</legend>
          {points.map((p) => (
            <label key={p.id} className="inline-flex items-center gap-2">
              <input type="checkbox" name="point" value={p.id} className="size-5" />
              {p.name}
            </label>
          ))}
        </fieldset>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            Create board
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
