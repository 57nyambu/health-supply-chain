import type { Metadata } from "next";

import { MfaSetup } from "./mfa-setup";

export const metadata: Metadata = { title: "Set up two-step sign-in" };

export default function MfaSetupPage() {
  return <MfaSetup />;
}
