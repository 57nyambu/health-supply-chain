import { expect, type Page, test } from "@playwright/test";

import { EPHEMERAL_S3, S3_API, S3_ENV } from "../storage-env";
import { apiFromPage, createUserWith, djangoShell, expectNoSeriousA11yIssues, manage, signIn } from "../support";

// E2E-12 Storage switch (COMPLETION.md §2): upload a lab PDF with STORAGE_BACKEND=local;
// switch to s3; upload another; both download through the API; storage_migrate --from local
// --to s3 --verify; all rows on S3; switch back to local: new uploads local, old still
// readable. The S3 side is MinIO in compose/CI (E2E_S3_ENDPOINT) and a moto server
// otherwise; the API on :8000 runs with STORAGE_BACKEND=local and the one on S3_API with
// STORAGE_BACKEND=s3, both against the same database and DATA_DIR (playwright.config.ts).

const pdf = (label: string) =>
  Buffer.from(
    `%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n` +
      `% synthetic lab report ${label}\ntrailer<</Root 1 0 R>>\n%%EOF\n`,
  );

async function csrf(page: Page): Promise<string> {
  return page.evaluate(() => document.cookie.split("; ").find((c) => c.startsWith("csrftoken="))?.split("=")[1] ?? "");
}

/** Upload through one API server; the browser's session cookie is valid on both. */
async function upload(page: Page, origin: string, patient: string, label: string) {
  const response = await page.request.post(`${origin}/api/v1/documents/`, {
    headers: { "X-CSRFToken": await csrf(page) },
    multipart: {
      file: { name: `lab-${label}.pdf`, mimeType: "application/pdf", buffer: pdf(label) },
      category: "lab_report",
      patient,
    },
  });
  expect(response.status(), await response.text()).toBe(201);
  return (await response.json()) as { id: string; storage_backend: string };
}

async function download(page: Page, origin: string, id: string): Promise<Buffer> {
  const response = await page.request.get(`${origin}/api/v1/documents/${id}/content/?purpose=care`);
  expect(response.status()).toBe(200);
  return response.body();
}

test("documents survive a switch from local disk to S3 and back", async ({ page }) => {
  test.skip(process.env.E2E_STORAGE === "off", "storage servers are off (E2E_STORAGE=off)");
  test.setTimeout(180_000);
  expect(manage(["storage_init"], S3_ENV).status).toBe(0);

  const clinicianPage = page;
  // Seed patient with national ID 00000007 (synthetic), found by its blind index.
  const seedPatient = djangoShell(
    "from apps.patients import identifiers as ids; from apps.patients.models import PatientIdentifier as I; " +
      "print(I.objects.get(type='national_id', active=True, value_index=ids.index('national_id', '00000007')).patient_id)",
  );
  const clinician = createUserWith({ roles: ["clinical_officer"], careTeam: seedPatient });
  await signIn(clinicianPage, clinician.email);
  await expect(clinicianPage).toHaveURL(/\/reception$/);
  const facility = String((await apiFromPage(clinicianPage, "/api/v1/me")).body.facility.id);

  // 1. Local (the web app's API).
  const first = await upload(clinicianPage, "", seedPatient, "local");
  expect(first.storage_backend).toBe("local");
  // 2. Switched to S3.
  const second = await upload(clinicianPage, S3_API, seedPatient, "s3");
  expect(second.storage_backend).toBe("s3");
  // Both download through either API, byte for byte.
  for (const origin of ["", S3_API]) {
    expect((await download(clinicianPage, origin, first.id)).equals(pdf("local"))).toBe(true);
    expect((await download(clinicianPage, origin, second.id)).equals(pdf("s3"))).toBe(true);
  }

  // 3. Migrate everything of this facility to S3, reading every copy back.
  const migrated = manage(["storage_migrate", "--from", "local", "--to", "s3", "--facility", facility, "--verify"], S3_ENV);
  expect(migrated.status, migrated.stderr).toBe(0);
  expect(djangoShell(`from apps.documents.models import Document; print(Document.objects.filter(facility_id=${facility}, storage_backend='local').count())`)).toBe("0");

  // 4. Back to local: new uploads land on disk, the migrated ones still open.
  const third = await upload(clinicianPage, "", seedPatient, "back");
  expect(third.storage_backend).toBe("local");
  expect((await download(clinicianPage, "", first.id)).equals(pdf("local"))).toBe(true);
  expect((await download(clinicianPage, "", third.id)).equals(pdf("back"))).toBe(true);

  // The chart lists all three to the clinician on the care team (the UI never shows where a file lives).
  await clinicianPage.goto(`/patients/${seedPatient}`);
  const documents = clinicianPage.getByRole("region", { name: "Clinical record" });
  for (const label of ["local", "s3", "back"]) {
    await expect(documents.getByText(`lab-${label}.pdf`).first()).toBeVisible();
  }
  await expectNoSeriousA11yIssues(clinicianPage);

  // A throwaway moto server forgets its objects when it stops: bring this facility's files
  // back to local disk so the dev database never points at missing objects.
  if (EPHEMERAL_S3) {
    const back = manage(["storage_migrate", "--from", "s3", "--to", "local", "--facility", facility, "--verify"], S3_ENV);
    expect(back.status, back.stderr).toBe(0);
  }
});
