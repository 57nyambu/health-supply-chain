"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { destination, useMe } from "@/lib/auth/session";

/** "/" sends a signed-in user to their first workspace; everyone else to sign-in. */
export default function Home() {
  const router = useRouter();
  const { data: me, isError } = useMe();
  useEffect(() => {
    if (me) router.replace(destination(me));
    else if (isError) router.replace("/login");
  }, [me, isError, router]);
  return (
    <p role="status" className="p-8 text-ink-muted">
      Loading…
    </p>
  );
}
