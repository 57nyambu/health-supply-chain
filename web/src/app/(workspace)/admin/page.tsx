"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Callout } from "@/components/ui/status";
import { useMe } from "@/lib/auth/session";

import { sectionsFor } from "./sections";

/** /admin opens the first section the user may use. */
export default function AdminHome() {
  const router = useRouter();
  const { data: me } = useMe();
  const first = me ? sectionsFor(me.permissions)[0] : undefined;
  useEffect(() => {
    if (first) router.replace(first.href);
  }, [first, router]);
  if (me && !first) {
    return <Callout tone="info" title="No administration sections are available to your roles." />;
  }
  return (
    <p role="status" className="text-ink-muted">
      Loading…
    </p>
  );
}
