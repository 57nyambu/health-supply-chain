import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { Callout } from "@/components/ui/status";
import { WORKSPACES } from "@/lib/auth/workspaces";

export const metadata: Metadata = { title: "Workspace" };

/** Workspaces that later phases build: say what is coming instead of an empty screen. */
export default async function WorkspacePage({ params }: { params: Promise<{ workspace: string }> }) {
  const { workspace } = await params;
  const known = WORKSPACES.find((w) => w.key === workspace);
  if (!known) notFound();
  return (
    <div className="p-8">
      <h1 className="text-xl font-bold">{known.label}</h1>
      <div className="mt-4 max-w-2xl">
        <Callout tone="info" title={`The ${known.label.toLowerCase()} workspace arrives in Phase 2.`}>
          Your role already gives you access; the worklist and forms will appear here.
        </Callout>
      </div>
    </div>
  );
}
