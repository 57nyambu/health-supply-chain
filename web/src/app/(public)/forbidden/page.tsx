import type { Metadata } from "next";

import Link from "next/link";

import { Button } from "@/components/ui/button";

export const metadata: Metadata = { title: "No access" };

/** Shown when the API refuses an action (403). */
export default function ForbiddenPage() {
  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-xl font-bold">You do not have access to this</h1>
      <p className="text-ink">
        Your roles at this facility do not allow it. If you need it for your work, ask your facility administrator to
        review your role. Emergency access to a patient record is available from the record itself.
      </p>
      <Button asChild variant="secondary">
        <Link href="/">Back to your workspace</Link>
      </Button>
    </div>
  );
}
