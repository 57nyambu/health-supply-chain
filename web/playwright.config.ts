import { defineConfig, devices } from "@playwright/test";

import { EPHEMERAL_S3, LOCAL_S3_PORT, S3_API, S3_ENV } from "./tests/e2e/storage-env";

// Scenarios run against the real API (fake integrations, synthetic seed data) and a
// production build of the web app on port 3100 (`next dev` compiles routes on first visit,
// which is slow and not what users get). E2E_REUSE=1 reuses a server already on 3100.
const API = "http://127.0.0.1:8000";
const WEB = "http://127.0.0.1:3100";
const DJANGO_ENV = process.env.DJANGO_ENV ?? "dev";
const MANAGE = "uv run --project ../api python ../api/manage.py";
// E2E-12 needs an S3 endpoint and a second API server writing to it; `make smoke` skips
// them (E2E_STORAGE=off) to keep the commit gate quick.
const STORAGE = process.env.E2E_STORAGE !== "off";

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
    ...(STORAGE && EPHEMERAL_S3
      ? [
          {
            command: `uv run --project ../api python -m moto.server -H 127.0.0.1 -p ${LOCAL_S3_PORT}`,
            url: `http://127.0.0.1:${LOCAL_S3_PORT}/moto-api/`,
            reuseExistingServer: true,
            timeout: 120_000,
          },
        ]
      : []),
    {
      command: `${MANAGE} runserver 127.0.0.1:8000 --noreload`,
      url: `${API}/healthz`,
      reuseExistingServer: true,
      timeout: 180_000,
      env: { DJANGO_ENV, ...(STORAGE ? S3_ENV : {}) },
    },
    ...(STORAGE
      ? [
          {
            command: `${MANAGE} runserver 127.0.0.1:8001 --noreload`,
            url: `${S3_API}/healthz`,
            reuseExistingServer: true,
            timeout: 180_000,
            env: { DJANGO_ENV, ...S3_ENV, STORAGE_BACKEND: "s3" },
          },
        ]
      : []),
    {
      command: "pnpm build && pnpm exec next start --hostname 127.0.0.1 --port 3100",
      url: WEB,
      reuseExistingServer: process.env.E2E_REUSE === "1",
      timeout: 600_000,
      env: { API_ORIGIN: API, DESIGN_CATALOGUE: "on" },
    },
  ],
});
