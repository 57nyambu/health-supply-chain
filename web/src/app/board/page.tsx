import type { Metadata } from "next";

import { BoardScreen } from "./board-screen";

export const metadata: Metadata = { title: "Queue board" };
export const dynamic = "force-dynamic";

/** TV queue board (DESIGN-SYSTEM §6.4): opened as /board#<device token>; no sign-in, no names. */
export default function BoardPage() {
  return <BoardScreen />;
}
