"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Field } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { Callout } from "@/components/ui/status";
import { QueueList } from "@/components/visits/queue-list";
import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/query";

/** Any service point's queue: call, recall, skip, transfer, send back, prioritise (DESIGN §6.3). */
export default function QueuePage() {
  const router = useRouter();
  const queues = useQuery({ queryKey: ["queues"], queryFn: () => unwrap(api.GET("/api/v1/visits/queues/")), refetchInterval: 30_000 });
  const [point, setPoint] = useState<string>();
  const options = (queues.data ?? []).map((q) => ({ value: String(q.id), label: `${q.name} — ${q.waiting} waiting` }));
  const chosen = point ?? options[0]?.value;
  return (
    <div className="flex flex-col gap-4 p-6">
      <h1 className="text-xl font-bold">Queues</h1>
      {queues.isError && <Callout tone="danger" title="The queues could not be loaded." />}
      <div className="max-w-md">
        <Field label="Service point">
          {(control) => <Select {...control} value={chosen} onValueChange={setPoint} options={options} />}
        </Field>
      </div>
      {chosen && <QueueList pointId={Number(chosen)} onOpen={(t) => router.push(`/patients/${t.visit.patient.id}`)} />}
    </div>
  );
}
