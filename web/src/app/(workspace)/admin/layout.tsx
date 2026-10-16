import { AdminNav } from "./admin-nav";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col">
      <div className="border-b border-border-subtle bg-surface px-6 pt-5">
        <h1 className="text-xl font-bold">Administration</h1>
        <AdminNav />
      </div>
      <div className="p-6">{children}</div>
    </div>
  );
}
