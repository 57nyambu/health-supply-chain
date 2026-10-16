import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { Catalogue } from "./catalogue";

export const metadata: Metadata = { title: "Design system" };

// A developer catalogue: hidden in production unless DESIGN_CATALOGUE=on.
export const dynamic = "force-dynamic";

export default function DesignPage() {
  if (process.env.NODE_ENV === "production" && process.env.DESIGN_CATALOGUE !== "on") notFound();
  return <Catalogue />;
}
