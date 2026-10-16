"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, type ReactNode, useState } from "react";

import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { Field, TextInput } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { Callout, StatusPill } from "@/components/ui/status";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, problemMessage } from "@/lib/api/client";
import { rows, type Schemas, unwrap } from "@/lib/api/query";
import { useMe } from "@/lib/auth/session";

const KINDS: { value: Schemas["ServicePointKindEnum"]; label: string }[] = [
  { value: "reception", label: "Reception" },
  { value: "triage", label: "Triage" },
  { value: "consultation", label: "Consultation room" },
  { value: "emergency", label: "Emergency / resuscitation" },
  { value: "lab", label: "Laboratory" },
  { value: "imaging", label: "Imaging" },
  { value: "pharmacy", label: "Pharmacy" },
  { value: "cashier", label: "Cashier" },
  { value: "treatment_room", label: "Treatment / procedure room" },
  { value: "ward_station", label: "Ward station" },
  { value: "records", label: "Health records" },
  { value: "other", label: "Other" },
];
const BED_STATUS = { available: "success", occupied: "info", cleaning: "warning", out_of_service: "danger" } as const;
const SETTINGS: { name: keyof Schemas["Facility"]; label: string; hint: string }[] = [
  { name: "workstation_lock_minutes", label: "Workstation lock (minutes idle)", hint: "1–30" },
  { name: "session_idle_minutes", label: "Sign-out after inactivity (minutes)", hint: "5–120" },
  { name: "session_absolute_hours", label: "Longest session (hours)", hint: "1–24" },
  { name: "care_team_expiry_hours", label: "Care-team access after discharge (hours)", hint: "1–720" },
  { name: "break_glass_minutes", label: "Break-glass access (minutes)", hint: "15–240" },
];

const failure = (caught: unknown) => (caught instanceof ApiError ? problemMessage(caught.problem) : "That did not work. Try again.");

/** Facility registry data, security settings and layout (DESIGN §4, §5). */
export default function FacilityPage() {
  const { data: me } = useMe();
  const manage = me?.permissions.includes("facilities.facility.manage") ?? false;
  const facilityId = me?.facility?.id;
  const facility = useQuery({
    queryKey: ["admin", "facility", facilityId],
    enabled: Boolean(facilityId),
    queryFn: () => unwrap(api.GET("/api/v1/facilities/facilities/{id}/", { params: { path: { id: facilityId! } } })),
  });
  return (
    <div className="flex flex-col gap-8">
      {facility.data && <Settings facility={facility.data} editable={manage} />}
      <Layout editable={manage} />
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section aria-label={title} className="flex flex-col gap-3">
      <h2 className="text-lg font-bold">{title}</h2>
      {children}
    </section>
  );
}

function Settings({ facility, editable }: { facility: Schemas["Facility"]; editable: boolean }) {
  const client = useQueryClient();
  const toast = useToast();
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const body: Record<string, string | number> = {};
    for (const name of ["name", "mfl_code", "fid", "sha_contract_number", "kra_pin", "odpc_controller_registration"]) {
      body[name] = String(form.get(name) ?? "").trim();
    }
    for (const { name } of SETTINGS) body[name] = Number(form.get(name));
    setSaving(true);
    setError(undefined);
    try {
      await unwrap(api.PATCH("/api/v1/facilities/facilities/{id}/", { params: { path: { id: facility.id } }, body: body as never }));
      await client.invalidateQueries({ queryKey: ["admin", "facility"] });
      toast({ title: "Facility saved", tone: "success" });
    } catch (caught) {
      setError(failure(caught));
    } finally {
      setSaving(false);
    }
  }

  const text = (name: keyof Schemas["Facility"], label: string, hint?: string) => (
    <Field label={label} hint={hint}>
      {(control) => <TextInput {...control} name={name} defaultValue={String(facility[name] ?? "")} readOnly={!editable} autoComplete="off" />}
    </Field>
  );
  return (
    <Section title="Facility details and security settings">
      <form method="post" onSubmit={save} noValidate className="grid gap-4 border border-border-subtle bg-surface p-4 md:grid-cols-3">
        {error && <div className="md:col-span-3"><Callout tone="danger" title={error} /></div>}
        {text("name", "Facility name")}
        {text("mfl_code", "MFL code", "5 or 6 digits")}
        {text("fid", "Facility Registry ID", "FID-…")}
        {text("sha_contract_number", "SHA contract number")}
        {text("kra_pin", "KRA PIN")}
        {text("odpc_controller_registration", "ODPC registration (controller)")}
        {SETTINGS.map((s) => (
          <Field key={s.name} label={s.label} hint={s.hint}>
            {(control) => (
              <TextInput {...control} name={s.name} type="number" defaultValue={String(facility[s.name] ?? "")} readOnly={!editable} className="tabular w-32 text-right" />
            )}
          </Field>
        ))}
        {editable && (
          <div className="md:col-span-3">
            <Button type="submit" loading={saving}>
              Save facility
            </Button>
          </div>
        )}
      </form>
    </Section>
  );
}

function Layout({ editable }: { editable: boolean }) {
  const client = useQueryClient();
  const toast = useToast();
  const departments = useQuery({ queryKey: ["admin", "departments"], queryFn: () => unwrap(api.GET("/api/v1/facilities/departments/")) });
  const points = useQuery({ queryKey: ["admin", "points"], queryFn: () => unwrap(api.GET("/api/v1/facilities/service-points/")) });
  const wards = useQuery({ queryKey: ["admin", "wards"], queryFn: () => unwrap(api.GET("/api/v1/facilities/wards/")) });
  const [ward, setWard] = useState<number>();
  const beds = useQuery({
    queryKey: ["admin", "beds", ward],
    enabled: Boolean(ward),
    queryFn: () => unwrap(api.GET("/api/v1/facilities/beds/", { params: { query: { ward } as never } })),
  });
  const deptOptions = rows<Schemas["Department"]>(departments.data).map((d) => ({ value: String(d.id), label: d.name }));
  const deptName = (id?: number | null) => deptOptions.find((d) => d.value === String(id))?.label ?? "—";
  const refresh = (key: string) => client.invalidateQueries({ queryKey: ["admin", key] });

  async function create(run: () => Promise<unknown>, key: string, done: string) {
    try {
      await run();
    } catch (caught) {
      toast({ title: failure(caught), tone: "danger" });
      return false;
    }
    // Not awaited: the form clears now, so a quick next entry is not wiped when the list lands.
    void refresh(key);
    toast({ title: done, tone: "success" });
    return true;
  }

  return (
    <>
      <Section title="Departments">
        <DataTable
          caption="Departments"
          rows={rows<Schemas["Department"]>(departments.data)}
          rowKey={(d) => String(d.id)}
          empty="No departments yet."
          columns={[
            { key: "code", header: "Code", cell: (d) => <span className="tabular">{d.code}</span>, sortValue: (d) => d.code },
            { key: "name", header: "Name", cell: (d) => d.name, sortValue: (d) => d.name },
          ]}
        />
        {editable && (
          <AddRow
            fields={[{ name: "code", label: "Code" }, { name: "name", label: "Name" }]}
            action="Add department"
            onSubmit={(v) => create(() => unwrap(api.POST("/api/v1/facilities/departments/", { body: { code: v.code!, name: v.name! } })), "departments", "Department added")}
          />
        )}
      </Section>

      <Section title="Service points">
        <DataTable
          caption="Service points"
          rows={rows<Schemas["ServicePoint"]>(points.data)}
          rowKey={(p) => String(p.id)}
          empty="No service points yet."
          columns={[
            { key: "code", header: "Code", cell: (p) => <span className="tabular">{p.code}</span>, sortValue: (p) => p.code },
            { key: "name", header: "Name", cell: (p) => p.name, sortValue: (p) => p.name },
            { key: "kind", header: "Kind", cell: (p) => KINDS.find((k) => k.value === p.kind)?.label ?? p.kind },
            { key: "dept", header: "Department", cell: (p) => deptName(p.department) },
          ]}
        />
        {editable && (
          <AddRow
            fields={[{ name: "code", label: "Code" }, { name: "name", label: "Name" }]}
            choices={[{ name: "kind", label: "Kind", options: KINDS }, { name: "department", label: "Department", options: deptOptions }]}
            action="Add service point"
            onSubmit={(v) =>
              create(
                () =>
                  unwrap(
                    api.POST("/api/v1/facilities/service-points/", {
                      body: { code: v.code!, name: v.name!, kind: v.kind as Schemas["ServicePointKindEnum"], department: v.department ? Number(v.department) : null },
                    }),
                  ),
                "points",
                "Service point added",
              )
            }
          />
        )}
      </Section>

      <Section title="Wards and beds">
        <DataTable
          caption="Wards"
          rows={rows<Schemas["Ward"]>(wards.data)}
          rowKey={(w) => String(w.id)}
          selectedKey={ward ? String(ward) : undefined}
          onOpen={(w) => setWard(w.id)}
          empty="No wards yet."
          columns={[
            { key: "name", header: "Ward", cell: (w) => <button type="button" className="font-semibold text-primary hover:underline" onClick={() => setWard(w.id)}>{w.name}</button> },
            { key: "kind", header: "Kind", cell: (w) => w.kind ?? "—" },
            { key: "sex", header: "Sex", cell: (w) => w.sex ?? "—" },
            { key: "beds", header: "Beds", cell: (w) => w.beds_total, numeric: true },
            { key: "free", header: "Available", cell: (w) => w.beds_available, numeric: true },
          ]}
        />
        {editable && (
          <AddRow
            fields={[{ name: "code", label: "Code" }, { name: "name", label: "Name" }]}
            action="Add ward"
            onSubmit={(v) => create(() => unwrap(api.POST("/api/v1/facilities/wards/", { body: { code: v.code!, name: v.name! } })), "wards", "Ward added")}
          />
        )}
        {ward && (
          <div className="flex flex-col gap-3 border-l-4 border-l-primary pl-4">
            <h3 className="font-bold">Beds in {rows<Schemas["Ward"]>(wards.data).find((w) => w.id === ward)?.name}</h3>
            <ul className="flex flex-wrap gap-2">
              {rows<Schemas["Bed"]>(beds.data).map((b) => (
                <li key={b.id} className="flex items-center gap-2 border border-border-strong bg-surface px-3 py-2">
                  <span className="tabular font-semibold">{b.code}</span>
                  <StatusPill tone={BED_STATUS[b.status as keyof typeof BED_STATUS] ?? "neutral"}>{b.status.replace(/_/g, " ")}</StatusPill>
                </li>
              ))}
            </ul>
            {editable && (
              <AddRow
                fields={[{ name: "code", label: "Bed code" }]}
                action="Add bed"
                onSubmit={(v) =>
                  create(() => unwrap(api.POST("/api/v1/facilities/beds/", { body: { ward, code: v.code! } })), "beds", "Bed added").then((ok) => {
                    if (ok) void refresh("wards");
                    return ok;
                  })
                }
              />
            )}
          </div>
        )}
      </Section>
    </>
  );
}

type Choice = { name: string; label: string; options: { value: string; label: string }[] };

function AddRow({
  fields,
  choices = [],
  action,
  onSubmit,
}: {
  fields: { name: string; label: string }[];
  choices?: Choice[];
  action: string;
  onSubmit: (values: Record<string, string | undefined>) => Promise<boolean>;
}) {
  const [picked, setPicked] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const values: Record<string, string | undefined> = { ...picked };
    for (const f of fields) values[f.name] = String(data.get(f.name) ?? "").trim();
    setSaving(true);
    const ok = await onSubmit(values);
    setSaving(false);
    if (ok) {
      form.reset();
      setPicked({});
    }
  }
  return (
    <form method="post" onSubmit={submit} noValidate className="flex flex-wrap items-end gap-3 border border-border-subtle bg-surface-sunken p-3">
      {fields.map((f) => (
        <Field key={f.name} label={f.label} required className="w-48">
          {(control) => <TextInput {...control} name={f.name} autoComplete="off" />}
        </Field>
      ))}
      {choices.map((c) => (
        <Field key={c.name} label={c.label} className="w-60">
          {(control) => <Select {...control} value={picked[c.name]} onValueChange={(v) => setPicked({ ...picked, [c.name]: v })} options={c.options} />}
        </Field>
      ))}
      <Button type="submit" variant="secondary" loading={saving}>
        {action}
      </Button>
    </form>
  );
}
