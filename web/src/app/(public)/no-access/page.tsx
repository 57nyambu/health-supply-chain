import type { Metadata } from "next";

import Link from "next/link";

import { Button } from "@/components/ui/button";

export const metadata: Metadata = { title: "No workspace" };

/** Signed in, but no role at this facility opens a workspace yet. */
export default function NoAccessPage() {
  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-xl font-bold">No workspace for your roles yet</h1>
      <p className="text-ink">
        You are signed in, but none of your roles at this facility opens a workspace. Ask your facility administrator
        to check your role assignment.
      </p>
      <Button asChild variant="secondary">
        <Link href="/login">Sign in as someone else</Link>
      </Button>
    </div>
  );
}
