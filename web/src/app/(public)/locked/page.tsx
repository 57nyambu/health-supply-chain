import type { Metadata } from "next";

import { LockScreen } from "./lock-screen";

export const metadata: Metadata = { title: "Workstation locked" };

export default function LockedPage() {
  return <LockScreen />;
}
