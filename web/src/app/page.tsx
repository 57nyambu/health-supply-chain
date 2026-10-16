import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto max-w-xl p-8">
      <h1 className="text-xl font-bold">AfyaSync</h1>
      <p className="mt-2 text-ink-muted">Hospital management for Kenyan facilities.</p>
      <Link className="mt-6 inline-block text-primary underline" href="/login">
        Sign in
      </Link>
    </main>
  );
}
