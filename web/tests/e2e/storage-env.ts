// S3 settings for the browser scenarios (E2E-12). With E2E_S3_ENDPOINT (MinIO from the
// compose services in CI) the scenarios use it; otherwise playwright.config.ts starts a
// throwaway moto S3 server. Test-runner settings only — never used by a deployed app.

export const LOCAL_S3_PORT = 9105;
export const EPHEMERAL_S3 = !process.env.E2E_S3_ENDPOINT;

const ENDPOINT = process.env.E2E_S3_ENDPOINT ?? `http://127.0.0.1:${LOCAL_S3_PORT}`;

export const S3_ENV: Record<string, string> = {
  S3_ENDPOINT_URL: ENDPOINT,
  // The residency guard only lets storage traffic reach allowed hosts (DESIGN §8.3).
  RESIDENCY_ALLOWED_HOSTS: [new URL(ENDPOINT).hostname, "127.0.0.1", "localhost"].join(","),
  S3_BUCKET: process.env.E2E_S3_BUCKET ?? process.env.S3_BUCKET ?? "afyasync-dev",
  S3_REGION_NAME: "us-east-1",
  S3_ACCESS_KEY_ID: process.env.E2E_S3_ACCESS_KEY_ID ?? process.env.MINIO_ROOT_USER ?? "afyasync",
  S3_SECRET_ACCESS_KEY: process.env.E2E_S3_SECRET_ACCESS_KEY ?? process.env.MINIO_ROOT_PASSWORD ?? "afyasync-dev-only",
};

/** The second API server: same database and DATA_DIR, new uploads go to S3. */
export const S3_API = "http://127.0.0.1:8001";
