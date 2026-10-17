"use client";

import { useEffect, useRef, useState } from "react";

type BoardTicket = { number: string; room: string; service_point: string; status: string; called_at: string | null };
type Board = { name: string; now_calling: BoardTicket[]; waiting: BoardTicket[] };

const POLL_MS = 5_000;

/** Reads the device token from the URL fragment (never sent to a server or logged) and keeps it
 * in memory only (ADR-042). Polls the board endpoint; announces new calls politely. */
export function BoardScreen() {
  const token = useRef<string | null>(null);
  const [board, setBoard] = useState<Board | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const lastCalled = useRef<string | null>(null);
  const [announcement, setAnnouncement] = useState("");

  useEffect(() => {
    token.current = window.location.hash.slice(1) || null;
    // Drop the token from the address bar so it is not shown on the TV.
    if (token.current) history.replaceState(null, "", window.location.pathname);
    let stopped = false;
    async function load() {
      if (!token.current) {
        setProblem("This board has no device token. An administrator opens it from Administration → Queue boards.");
        return;
      }
      try {
        const response = await fetch("/api/v1/visits/board-display/", {
          headers: { "X-Board-Token": token.current },
          cache: "no-store",
          credentials: "omit",
        });
        if (!response.ok) {
          setProblem(response.status === 401 ? "This board is not recognised. Ask an administrator for a new board link." : "The board cannot reach the server.");
          return;
        }
        const data = (await response.json()) as Board;
        setProblem(null);
        setBoard(data);
        const first = data.now_calling[0];
        const key = first ? `${first.number}-${first.called_at}` : null;
        if (first && key !== lastCalled.current) {
          setAnnouncement(`Ticket ${first.number}, please go to ${first.room}.`);
        }
        lastCalled.current = key;
      } catch {
        setProblem("The board cannot reach the server.");
      }
    }
    void load();
    const timer = setInterval(() => !stopped && void load(), POLL_MS);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, []);

  return (
    <main className="flex min-h-screen flex-col gap-6 bg-canvas p-8 text-ink">
      <header className="flex items-baseline justify-between">
        <h1 className="text-[39px] font-bold">{board?.name ?? "Queue board"}</h1>
      </header>
      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>
      {problem && (
        <p role="alert" className="border-l-4 border-danger bg-danger-tint p-6 text-2xl font-semibold text-danger-ink">
          {problem}
        </p>
      )}
      {board && (
        <div className="grid flex-1 gap-8 lg:grid-cols-[2fr_1fr]">
          <section aria-labelledby="now-heading" className="border border-border-strong bg-surface">
            <h2 id="now-heading" className="border-b border-border-subtle bg-surface-sunken px-6 py-3 text-[31px] font-bold">
              Now serving
            </h2>
            {board.now_calling.length === 0 ? (
              <p className="px-6 py-8 text-2xl text-ink-muted">Please wait to be called.</p>
            ) : (
              <ul className="divide-y divide-border-subtle">
                {board.now_calling.map((t) => (
                  <li key={t.number} className="flex items-baseline justify-between gap-6 px-6 py-4">
                    <span className="tabular text-[96px] leading-none font-bold">{t.number}</span>
                    <span className="text-[39px] font-semibold">{t.room}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section aria-labelledby="next-heading" className="border border-border-strong bg-surface">
            <h2 id="next-heading" className="border-b border-border-subtle bg-surface-sunken px-6 py-3 text-[31px] font-bold">
              Next
            </h2>
            <ul className="grid grid-cols-2 gap-x-6 px-6 py-4">
              {board.waiting.map((t) => (
                <li key={t.number} className="tabular py-2 text-[39px] font-semibold">
                  {t.number}
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </main>
  );
}
