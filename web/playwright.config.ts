import { defineConfig, devices } from "@playwright/test";

// Scenarios run against the real API (fake integrations, synthetic seed data) and a
// production build of the web app on port 3100 (`next dev` compiles routes on first visit,
// which is slow and not what users get). E2E_REUSE=1 reuses a server already on 3100.
const API = "http://127.0.0.1:8000";
const WEB = "http://127.0.0.1:3100";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: process.env.CI ? [["junit", { outputFile: "test-results/e2e.xml" }], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: WEB,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    locale: "en-KE",
    timezoneId: "Africa/Nairobi",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } }],
  webServer: [
    {
      command: "uv run --project ../api python ../api/manage.py runserver 127.0.0.1:8000 --noreload",
      url: `${API}/healthz`,
      reuseExistingServer: true,
      timeout: 180_000,
      env: { DJANGO_ENV: process.env.DJANGO_ENV ?? "dev" },
    },
    {
      command: "pnpm build && pnpm exec next start --hostname 127.0.0.1 --port 3100",
      url: WEB,
      reuseExistingServer: process.env.E2E_REUSE === "1",
      timeout: 600_000,
      env: { API_ORIGIN: API, DESIGN_CATALOGUE: "on" },
    },
  ],
});
