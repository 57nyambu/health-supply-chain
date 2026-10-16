/**
 * Typed API client (openapi-fetch over src/lib/api/schema.d.ts, generated from
 * api/openapi.yaml by `make openapi`). Same origin only: the session cookie is httpOnly
 * and unsafe methods carry Django's CSRF token. Nothing is cached in browser storage.
 */
import createClient, { type Middleware } from "openapi-fetch";

import type { paths } from "./schema";

const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const CSRF_COOKIE = "csrftoken";

export type Problem = {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  code?: string;
  request_id?: string;
  errors?: { field?: string; message: string }[];
  [key: string]: unknown;
};

export function readCookie(name: string, cookies: string = typeof document === "undefined" ? "" : document.cookie) {
  for (const part of cookies.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) return decodeURIComponent(rest.join("="));
  }
  return undefined;
}

let pending: Promise<string> | null = null;

/** The CSRF token from the cookie, fetching one first when there is none yet. */
export async function csrfToken(): Promise<string> {
  const fromCookie = readCookie(CSRF_COOKIE);
  if (fromCookie) return fromCookie;
  pending ??= fetch("/api/v1/auth/csrf", { credentials: "same-origin" })
    .then((response) => response.json() as Promise<{ csrf_token: string }>)
    .then((body) => body.csrf_token)
    .finally(() => {
      pending = null;
    });
  return pending;
}

export const csrfMiddleware: Middleware = {
  async onRequest({ request }) {
    if (UNSAFE.has(request.method.toUpperCase())) {
      request.headers.set("X-CSRFToken", await csrfToken());
    }
    return request;
  },
};

export const api = createClient<paths>({ baseUrl: "", credentials: "same-origin" });
api.use(csrfMiddleware);

/** A short, PHI-free message for a problem+json error. */
export function problemMessage(problem: unknown, fallback = "Something went wrong. Try again."): string {
  if (problem && typeof problem === "object") {
    const p = problem as Problem;
    if (p.errors?.length) return p.errors.map((e) => e.message).join(" ");
    if (p.detail) return p.detail;
  }
  return fallback;
}
