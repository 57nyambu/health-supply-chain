"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { Dialog } from "@/components/ui/dialog";
import { Field, TextInput } from "@/components/ui/field";
import { MoneyInput } from "@/components/ui/inputs";
import { Select } from "@/components/ui/select";
import { Callout, StatusPill } from "@/components/ui/status";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, problemMessage } from "@/lib/api/client";
import { rows, type Schemas, unwrap } from "@/lib/api/query";
import { formatDate, formatKES } from "@/lib/format";

type Service = Schemas["Service"];
type PriceItem = Schemas["PriceItem"];

export const SERVICE_KINDS = [
  { value: "consultation", label: "Consultation" },
  { value: "lab", label: "Laboratory test" },
  { value: "imaging", label: "Imaging" },
  { value: "procedure", label: "Procedure" },
  { value: "bed_day", label: "Bed-day" },
  { value: "nursing", label: "Nursing care" },
  { value: "drug_dispense", label: "Medicine dispensing" },
  { value: "package", label: "Package" },
  { value: "other", label: "Other" },
];
const KIND_LABEL = Object.fromEntries(SERVICE_KINDS.map((k) => [k.value, k.label]));

/** Service catalogue and price lists (P2-BIL-01). New services and price changes wait for the
 * finance manager under Approvals (maker-checker, DESIGN §7.9). */
export default function ServicesPage() {
  const client = useQueryClient();
  const toast = useToast();
  const [kind, setKind] = useState("all");
  const [listId, setListId] = useState<string>();
  const [pricing, setPricing] = useState<Service | null>(null);
  const [mapping, setMapping] = useState<Service | null>(null);
  const [adding, setAdding] = useState(false);
  const services = useQuery({
    queryKey: ["billing", "services", kind],
    queryFn: () =>
      unwrap(api.GET("/api/v1/billing/services/", { params: { query: { page_size: 200, ...(kind === "all" ? {} : { kind }) } as never } })),
  });
  const lists = useQuery({ queryKey: ["billing", "price-lists"], queryFn: () => unwrap(api.GET("/api/v1/billing/price-lists/")) });
  const chosenList = listId ?? lists.data?.find((l) => l.basis === "cash")?.id ?? lists.data?.[0]?.id;
  const prices = useQuery({
    queryKey: ["billing", "prices", chosenList],
    enabled: Boolean(chosenList),
    queryFn: () =>
      unwrap(api.GET("/api/v1/billing/price-lists/{id}/items/", { params: { path: { id: chosenList! }, query: { current: "true" } as never } })),
  });
  const priceOf = new Map((prices.data ?? []).map((p: PriceItem) => [p.service, p]));
  const refresh = () => client.invalidateQueries({ queryKey: ["billing"] });

  return (
    <div className="flex flex-col gap-4">
      <p className="max-w-[75ch] text-ink-muted">
        Everything the facility charges for. Price changes and new services take effect after the finance manager approves
        them under Approvals. SHA intervention codes here are synthetic until the SHA tariff is imported.
      </p>
      <div className="flex flex-wrap items-end gap-3">
        <Field label="Kind" className="w-56">
          {(control) => <Select {...control} value={kind} onValueChange={setKind} options={[{ value: "all", label: "All kinds" }, ...SERVICE_KINDS]} />}
        </Field>
        <Field label="Price list" className="w-80">
          {(control) => (
            <Select
              {...control}
              value={chosenList}
              onValueChange={setListId}
              options={(lists.data ?? []).map((l) => ({ value: l.id, label: l.name }))}
            />
          )}
        </Field>
        <Button className="ml-auto" onClick={() => setAdding(true)}>
          Request a new service
        </Button>
      </div>
      {services.isError && <Callout tone="danger" title="Services could not be loaded." />}
      <DataTable
        caption="Service catalogue with prices on the chosen list"
        rows={rows<Service>(services.data)}
        rowKey={(s) => s.id}
        empty={services.isPending ? "Loading…" : "No services yet. Request the first one."}
        columns={[
          { key: "code", header: "Code", cell: (s) => <span className="tabular">{s.code}</span>, sortValue: (s) => s.code },
          { key: "name", header: "Service", cell: (s) => s.name, sortValue: (s) => s.name },
          { key: "kind", header: "Kind", cell: (s) => KIND_LABEL[s.kind] ?? s.kind },
          {
            key: "price",
            header: "Price",
            numeric: true,
            cell: (s) => {
              const p = priceOf.get(s.id);
              return p ? formatKES(p.price) : <span className="text-ink-muted">No price</span>;
            },
          },
          { key: "since", header: "Since", cell: (s) => (priceOf.get(s.id) ? formatDate(priceOf.get(s.id)!.effective_from) : "—") },
          { key: "sha", header: "SHA interventions", cell: (s) => s.sha_interventions.join(", ") || "—" },
          { key: "status", header: "Status", cell: (s) => <StatusPill tone={s.status === "active" ? "success" : "neutral"}>{s.status === "active" ? "Active" : "Inactive"}</StatusPill> },
          {
            key: "actions",
            header: "Actions",
            cell: (s) => (
              <div className="flex gap-1">
                <Button density="compact" variant="secondary" onClick={() => setPricing(s)}>
                  Change price
                </Button>
                <Button density="compact" variant="quiet" onClick={() => setMapping(s)}>
                  Edit codes
                </Button>
              </div>
            ),
          },
        ]}
      />
      {pricing && chosenList && (
        <PriceDialog
          service={pricing}
          listId={chosenList}
          listName={lists.data?.find((l) => l.id === chosenList)?.name ?? ""}
          current={priceOf.get(pricing.id)?.price}
          onClose={() => setPricing(null)}
          onDone={async () => {
            toast({ title: "Price change sent for approval", tone: "success" });
            await refresh();
          }}
        />
      )}
      {mapping && <MappingDialog service={mapping} onClose={() => setMapping(null)} onDone={refresh} />}
      {adding && (
        <NewServiceDialog
          onClose={() => setAdding(false)}
          onDone={async () => {
            toast({ title: "New service sent for approval", tone: "success" });
            await refresh();
          }}
        />
      )}
    </div>
  );
}

function useSubmit(onDone: () => Promise<unknown>, onClose: () => void) {
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);
  const submit = async (call: () => Promise<unknown>) => {
    setSaving(true);
    setError(undefined);
    try {
      await call();
      await onDone();
      onClose();
    } catch (caught) {
      setError(caught instanceof ApiError ? problemMessage(caught.problem) : "That did not work. Try again.");
    } finally {
      setSaving(false);
    }
  };
  return { error, setError, saving, submit };
}

function PriceDialog({
  service,
  listId,
  listName,
  current,
  onClose,
  onDone,
}: {
  service: Service;
  listId: string;
  listName: string;
  current?: string;
  onClose: () => void;
  onDone: () => Promise<unknown>;
}) {
  const [price, setPrice] = useState<string | null>(current ?? null);
  const { error, setError, saving, submit } = useSubmit(onDone, onClose);
  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const reason = String(new FormData(event.currentTarget).get("reason") ?? "").trim();
    if (!price) return setError("Enter the new price.");
    if (!reason) return setError("Say why the price changes.");
    void submit(() =>
      unwrap(
        api.POST("/api/v1/billing/price-lists/{id}/prices/", {
          params: { path: { id: listId } },
          body: { service: service.id, price, reason, effective_from: null },
        }),
      ),
    );
  }
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()} title={`Change the price of ${service.name}`} description={`${listName}. Takes effect when approved.`}>
      <form method="post" onSubmit={save} noValidate className="flex flex-col gap-4">
        {error && <Callout tone="danger" title={error} />}
        <Field label="New price (KES)" required hint={current ? `Current price ${formatKES(current)}` : "No price on this list yet."}>
          {(control) => <MoneyInput {...control} value={price ?? ""} onValueChange={setPrice} />}
        </Field>
        <Field label="Reason" required>
          {(control) => <TextInput {...control} name="reason" maxLength={255} />}
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            Send for approval
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

function MappingDialog({ service, onClose, onDone }: { service: Service; onClose: () => void; onDone: () => Promise<unknown> }) {
  const { error, saving, submit } = useSubmit(onDone, onClose);
  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const codes = String(form.get("sha") ?? "")
      .split(/[,\s]+/)
      .map((c) => c.trim())
      .filter(Boolean);
    void submit(() =>
      unwrap(
        api.PATCH("/api/v1/billing/services/{id}/", {
          params: { path: { id: service.id } },
          body: { sha_interventions: codes, etims_item_code: String(form.get("etims") ?? ""), revenue_code: String(form.get("revenue") ?? "") },
        }),
      ),
    );
  }
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()} title={`Codes for ${service.name}`}>
      <form method="post" onSubmit={save} noValidate className="flex flex-col gap-4">
        {error && <Callout tone="danger" title={error} />}
        <Field label="SHA intervention codes" hint="Separate codes with commas.">
          {(control) => <TextInput {...control} name="sha" defaultValue={service.sha_interventions.join(", ")} />}
        </Field>
        <Field label="eTIMS item code">{(control) => <TextInput {...control} name="etims" defaultValue={service.etims_item_code} />}</Field>
        <Field label="Revenue code">{(control) => <TextInput {...control} name="revenue" defaultValue={service.revenue_code} />}</Field>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            Save codes
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

function NewServiceDialog({ onClose, onDone }: { onClose: () => void; onDone: () => Promise<unknown> }) {
  const [kind, setKind] = useState<string>();
  const [price, setPrice] = useState<string | null>(null);
  const { error, setError, saving, submit } = useSubmit(onDone, onClose);
  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const code = String(form.get("code") ?? "").trim();
    const name = String(form.get("name") ?? "").trim();
    const reason = String(form.get("reason") ?? "").trim();
    if (!code || !name || !kind || !reason) return setError("Enter the code, name, kind and reason.");
    void submit(() =>
      unwrap(
        api.POST("/api/v1/billing/services/", {
          body: { code, name, kind: kind as Schemas["ServiceRequestRequest"]["kind"], reason, cash_price: price, revenue_code: "", etims_item_code: "" },
        }),
      ),
    );
  }
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()} title="Request a new service" description="The finance manager approves it under Approvals.">
      <form method="post" onSubmit={save} noValidate className="flex flex-col gap-4">
        {error && <Callout tone="danger" title={error} />}
        <Field label="Code" required>
          {(control) => <TextInput {...control} name="code" maxLength={40} />}
        </Field>
        <Field label="Name" required>
          {(control) => <TextInput {...control} name="name" maxLength={160} />}
        </Field>
        <Field label="Kind" required>
          {(control) => <Select {...control} value={kind} onValueChange={setKind} options={SERVICE_KINDS} />}
        </Field>
        <Field label="Cash price (KES)" hint="Optional; set prices for other lists afterwards.">
          {(control) => <MoneyInput {...control} value={price ?? ""} onValueChange={setPrice} />}
        </Field>
        <Field label="Reason" required>
          {(control) => <TextInput {...control} name="reason" maxLength={255} />}
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            Send for approval
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
