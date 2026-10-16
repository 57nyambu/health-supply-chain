import { expect, test } from "@playwright/test";

// P1-WEB-01: the browser reaches Django through /api/* on its own origin; the session
// cookie is httpOnly and unsafe requests need Django's CSRF token — no CORS involved.
test("the API is same-origin and CSRF-protected", async ({ page }) => {
  // A public page that stays put ("/" redirects signed-out visitors to sign in).
  await page.goto("/session-expired");
  const result = await page.evaluate(async () => {
    const csrf = await fetch("/api/v1/auth/csrf").then((r) => r.json());
    const login = (headers: Record<string, string>) =>
      fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers },
        body: JSON.stringify({ email: "nobody@example.test", password: "not-the-password-123" }),
      }).then(async (r) => ({ status: r.status, body: await r.json() }));
    return {
      tokenInCookie: document.cookie.includes("csrftoken="),
      withToken: await login({ "X-CSRFToken": csrf.csrf_token }),
      withoutToken: await login({}),
      trailingSlash: (await fetch("/api/v1/patients/search/?q=abc")).status,
    };
  });
  expect(result.tokenInCookie).toBe(true);
  expect(result.withToken.status).toBe(401);
  expect(result.withToken.body.code).toBe("invalid_credentials");
  expect(result.withoutToken.status).toBe(403);
  expect(result.withoutToken.body.code).toBe("csrf_failed");
  expect([401, 403]).toContain(result.trailingSlash);
});

test("pages are never cached and never framed", async ({ request }) => {
  const response = await request.get("/");
  expect(response.headers()["cache-control"]).toBe("no-store");
  expect(response.headers()["x-frame-options"]).toBe("DENY");
  expect(response.headers()["x-powered-by"]).toBeUndefined();
});
