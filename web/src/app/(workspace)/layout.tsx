import { Shell } from "@/components/shell/shell";

// Workspaces show patient data once loaded: always rendered per request, never cached.
export const dynamic = "force-dynamic";

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return <Shell>{children}</Shell>;
}
