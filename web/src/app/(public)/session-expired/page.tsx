import type { Metadata } from "next";

import Link from "next/link";

import { Button } from "@/components/ui/button";

export const metadata: Metadata = { title: "Session ended" };

export default function SessionExpiredPage() {
  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-xl font-bold">Your session has ended</h1>
      <p className="text-ink">
        To protect patients&rsquo; information, AfyaSync signs you out after a period without activity and at the end
        of a long shift. Anything you had saved is safe.
      </p>
      <Button asChild>
        <Link href="/login">Sign in again</Link>
      </Button>
    </div>
  );
}
