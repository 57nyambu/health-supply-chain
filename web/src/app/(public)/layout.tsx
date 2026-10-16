export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center bg-canvas px-4 py-16">
      <p className="mb-6 text-lg font-bold text-ink">AfyaSync</p>
      <main className="w-full max-w-md border border-border-strong bg-surface p-8">{children}</main>
    </div>
  );
}
