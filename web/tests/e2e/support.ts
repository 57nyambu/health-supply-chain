import { execFileSync } from "node:child_process";
import { createHmac } from "node:crypto";

import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

/** Password of the synthetic seed and test users (never a real one). */
export function seedPassword(): string {
  const value = process.env.SEED_PASSWORD;
  if (!value) throw new Error("Set SEED_PASSWORD (the synthetic seed password) to run the browser scenarios.");
  return value;
}

/** A fresh synthetic user with these roles at the seed facility (`manage.py e2e_user`). */
export function createUser(...roles: string[]): { email: string; id: number } {
  const output = execFileSync(
    "uv",
    ["run", "--project", "../api", "python", "../api/manage.py", "e2e_user", ...roles.flatMap((r) => ["--role", r])],
    { encoding: "utf8", env: { ...process.env, DJANGO_ENV: process.env.DJANGO_ENV ?? "dev" } },
  );
  const last = output.trim().split(/\r?\n/).pop() ?? "{}";
  return JSON.parse(last) as { email: string; id: number };
}

function base32(secret: string): Buffer {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const char of secret.replace(/=+$/, "").toUpperCase()) {
    const value = alphabet.indexOf(char);
    if (value < 0) throw new Error("not base32");
    bits += value.toString(2).padStart(5, "0");
  }
  const bytes = bits.match(/.{8}/g) ?? [];
  return Buffer.from(bytes.map((b) => parseInt(b, 2)));
}

/** RFC 6238 TOTP (SHA-1, 6 digits, 30 s) — what an authenticator app shows. */
export function totp(secret: string, at: number = Date.now()): string {
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(at / 1000 / 30)));
  const digest = createHmac("sha1", base32(secret)).update(counter).digest();
  const offset = digest[digest.length - 1]! & 0xf;
  const code = (digest.readUInt32BE(offset) & 0x7fffffff) % 1_000_000;
  return String(code).padStart(6, "0");
}

/** Keyboard-only sign-in from /login (the e-mail field has focus on load). */
export async function signIn(page: Page, email: string, password = seedPassword()) {
  await page.goto("/login");
  await expect(page.getByLabel(/E-mail address/)).toBeFocused();
  await page.keyboard.type(email);
  await page.keyboard.press("Tab");
  await page.keyboard.type(password);
  // Submit stays disabled until the page is interactive (no native fallback submission).
  await expect(page.getByRole("button", { name: "Sign in" })).toBeEnabled();
  await page.keyboard.press("Enter");
}

/** Call the API from inside the page (same origin, session cookie, CSRF header). */
export async function apiFromPage(page: Page, path: string, body?: unknown) {
  return page.evaluate(
    async ({ path, body }) => {
      const token = document.cookie.split("; ").find((c) => c.startsWith("csrftoken="))?.split("=")[1] ?? "";
      const response = await fetch(path, {
        method: body === undefined ? "GET" : "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": token },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      return { status: response.status, body: response.status === 204 ? null : await response.json() };
    },
    { path, body },
  );
}

export async function expectNoSeriousA11yIssues(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  const blocking = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
}
