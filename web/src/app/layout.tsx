import type { Metadata } from "next";
import { Atkinson_Hyperlegible_Next } from "next/font/google";

import "@/styles/tokens.css";

import { Providers } from "./providers";

// Separates confusable glyphs (I l 1, O 0, rn m) — DESIGN-SYSTEM §3. Self-hosted by next/font.
const atkinson = Atkinson_Hyperlegible_Next({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-atkinson",
  // No metric overrides exist for this family; fall back to system UI fonts.
  adjustFontFallback: false,
  fallback: ["system-ui", "sans-serif"],
});

// Titles never carry patient details (web/CLAUDE.md).
export const metadata: Metadata = {
  title: { default: "AfyaSync", template: "%s · AfyaSync" },
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en-KE" className={atkinson.variable}>
      <body className="min-h-screen bg-canvas text-ink antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
