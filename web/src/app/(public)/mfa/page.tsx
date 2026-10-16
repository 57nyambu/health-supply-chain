import type { Metadata } from "next";
import { Suspense } from "react";

import { MfaChallenge } from "./mfa-challenge";

export const metadata: Metadata = { title: "Second step" };

export default function MfaPage() {
  return (
    <Suspense>
      <MfaChallenge />
    </Suspense>
  );
}
