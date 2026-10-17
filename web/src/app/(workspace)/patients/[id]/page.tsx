"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";

import { BreakGlassBanner, PatientBanner } from "@/components/clinical/patient-banner";
import { JourneyRail } from "@/components/clinical/journey-rail";
import { Callout } from "@/components/ui/status";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, problemMessage } from "@/lib/api/client";
import { type Schemas, unwrap } from "@/lib/api/query";
import { useMe } from "@/lib/auth/session";
import { identifierLabel, maskIdentifier } from "@/lib/patients";

import { VisitPanel } from "@/components/visits/visit-panel";
import { journeyStep, PAYER_TYPE_LABEL } from "@/lib/visits";

import { ClinicalRecord, type ChartSummary } from "./clinical-record";
import { RegistrationDetails } from "./registration-details";

export type PatientRecord = Schemas["PatientRecord"];

/** One patient: banner, journey, registration details and the clinical record at the user's
 * access level (DESIGN §7.7). Opaque UUID in the URL, no name in the title (web/CLAUDE.md). */
export default function PatientPage() {
  const { id } = useParams<{ id: string }>();
  const client = useQueryClient();
  const toast = useToast();
  const { data: me } = useMe();
  const can = (code: string) => me?.permissions.includes(code) ?? false;
  const clinical = can("clinical.record.read_summary");
  // One audited open per view: clinicians read the chart (it carries the demographics);
  // everyone else, or a clinician below summary level, reads the registration record.
  const chart = useQuery({
    queryKey: ["patient", id, "chart"],
    enabled: clinical,
    retry: false,
    queryFn: () => unwrap(api.GET("/api/v1/patients/{id}/chart/", { params: { path: { id }, query: { purpose: "care" } } })),
  });
  const record = useQuery({
    queryKey: ["patient", id, clinical ? "care" : "registration"],
    enabled: Boolean(me) && (!clinical || chart.isError),
    retry: false,
    queryFn: () =>
      unwrap(api.GET("/api/v1/patients/{id}/", { params: { path: { id }, query: { purpose: clinical ? "care" : "registration" } } })),
  });
  const visits = useQuery({
    queryKey: ["patient", id, "open-visit"],
    enabled: can("visits.visit.read"),
    retry: false,
    queryFn: () => unwrap(api.GET("/api/v1/visits/", { params: { query: { patient: id, open: true } } })),
  });
  const openVisit = visits.data?.results?.[0] ?? null;
  const refresh = () => client.invalidateQueries({ queryKey: ["patient", id] });
  const loaded: PatientRecord | undefined = chart.data ? { ...chart.data.patient, access: chart.data.access } : record.data;

  const failed = record.isError && (!clinical || chart.isError);
  if (!loaded && !failed) {
    return (
      <p role="status" className="p-8 text-ink-muted">
        Loading the record…
      </p>
    );
  }
  if (!loaded) {
    const error = record.error;
    const notFound = error instanceof ApiError && error.status === 404;
    return (
      <div className="p-8">
        <Callout tone="danger" title={notFound ? "There is no such patient at this facility." : "The record could not be opened."}>
          {!notFound && error instanceof ApiError ? problemMessage(error.problem) : null}{" "}
          <Link href="/reception" className="font-semibold text-primary underline">
            Back to reception
          </Link>
        </Callout>
      </div>
    );
  }

  const patient = loaded;
  const access = patient.access;
  const summary = (chart.data?.summary ?? null) as ChartSummary | null;
  const second = patient.identifiers.find((i) => i.type !== "temporary") ?? patient.identifiers[0];
  const grant = access.break_glass;

  async function endEmergencyAccess() {
    if (!grant) return;
    try {
      await unwrap(api.POST("/api/v1/access/break-glass/{id}/end/", { params: { path: { id: grant.id } } }));
      await refresh();
      toast({ title: "Emergency access ended", tone: "success" });
    } catch (caught) {
      toast({ title: caught instanceof ApiError ? problemMessage(caught.problem) : "Could not end emergency access.", tone: "danger" });
    }
  }

  return (
    <div className="flex flex-col">
      <PatientBanner
        patient={{
          displayName: patient.display_name,
          sex: patient.sex,
          dateOfBirth: patient.date_of_birth,
          dobEstimated: patient.dob_estimated,
          mrn: patient.mrn,
          secondIdentifier: second ? { label: identifierLabel(second.type), value: maskIdentifier(second.value) } : undefined,
          allergies: summary?.allergies.length
            ? { state: "recorded", items: summary.allergies.map((a) => a.label ?? String(a.substance ?? "")) }
            : { state: "not_recorded" },
          payer: openVisit
            ? openVisit.payer_type === "cash" || openVisit.payer_type === "waiver"
              ? { name: PAYER_TYPE_LABEL[openVisit.payer_type] ?? "Cash", status: "self_pay" }
              : { name: openVisit.scheme_name ?? PAYER_TYPE_LABEL[openVisit.payer_type] ?? "", status: "pending" }
            : undefined,
          alerts: [
            ...(patient.is_unidentified ? ["Unidentified — confirm identity"] : []),
            ...(summary?.alerts.map((a) => a.label ?? "") ?? []),
          ].filter(Boolean),
        }}
      />
      {grant && <BreakGlassBanner expiresAt={grant.expires_at} onEnd={endEmergencyAccess} />}
      <JourneyRail
        current={journeyStep(openVisit?.status)}
        emergency={openVisit ? openVisit.visit_type === "emergency" : patient.is_unidentified}
      />
      {patient.status === "merged" && (
        <div className="px-6 pt-4">
          <Callout tone="warning" title="This record was merged into another record.">
            {patient.merged_into && (
              <Link href={`/patients/${patient.merged_into}`} className="font-semibold text-primary underline">
                Open the surviving record
              </Link>
            )}
          </Callout>
        </div>
      )}
      <div className={clinical ? "grid gap-6 p-6 xl:grid-cols-2" : "flex max-w-4xl flex-col gap-6 p-6"}>
        {can("visits.visit.read") && patient.status === "active" && (
          <VisitPanel
            patientId={id}
            visit={visits.isPending ? undefined : openVisit}
            canOpen={can("visits.visit.create")}
            onOpened={refresh}
          />
        )}
        <RegistrationDetails patient={patient} editable={can("patients.patient.update") && patient.status === "active"} onChanged={refresh} />
        {clinical && (
          <ClinicalRecord
            patientId={id}
            access={access}
            chart={chart.data}
            error={chart.error}
            loading={chart.isPending}
            canBreakGlass={can("access.breakglass.request")}
            onChanged={refresh}
          />
        )}
      </div>
    </div>
  );
}
