import { expect, test } from "@playwright/test";

import { apiFromPage, createUser, expectNoSeriousA11yIssues, signIn } from "./support";

// P1-UAC-08 in the browser: a clinician off the care team sees the summary; break-glass with
// a reason opens the full record for a limited time behind a banner, and can be ended early.
// A receptionist sees registration details only — no clinical section at all.

test("break-glass opens the full record behind a banner, and ends", async ({ page }) => {
  const clinician = createUser("clinical_officer");
  await signIn(page, clinician.email);
  await expect(page).toHaveURL(/\/reception$/);
  const found = await apiFromPage(page, "/api/v1/patients/search/", { q: "00000001" });
  const patientId = found.body.results[0].id as string;
  await page.goto(`/patients/${patientId}`);

  const clinical = page.getByRole("region", { name: "Clinical record" });
  await expect(clinical.getByText("You see the summary because you are not on this patient's care team.")).toBeVisible();
  await expect(clinical.getByRole("heading", { name: "Allergies" })).toBeVisible();
  await expect(clinical.getByRole("heading", { name: "Documents" })).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Patient" }).getByText("Allergies not recorded")).toBeVisible();
  await expectNoSeriousA11yIssues(page);

  await clinical.getByRole("button", { name: "Use emergency access" }).click();
  const dialog = page.getByRole("dialog", { name: "Use emergency access" });
  await expect(dialog.getByLabel(/Why you need the full record now/)).toBeFocused();
  await page.keyboard.type("Collapsed in the waiting area, history needed now");
  await expectNoSeriousA11yIssues(page);
  await dialog.getByRole("button", { name: "Open the full record" }).click();

  const banner = page.getByRole("status").filter({ hasText: "Every view is logged and reviewed" });
  await expect(banner).toBeVisible();
  await expect(clinical.getByRole("heading", { name: "Documents" })).toBeVisible();
  await expect(clinical.getByText("Full record")).toBeVisible();
  await expectNoSeriousA11yIssues(page);

  await banner.getByRole("button", { name: "End emergency access" }).click();
  await expect(banner).toHaveCount(0);
  await expect(clinical.getByRole("heading", { name: "Documents" })).toHaveCount(0);
});

test("reception sees registration details only", async ({ page }) => {
  const receptionist = createUser("receptionist");
  await signIn(page, receptionist.email);
  await expect(page).toHaveURL(/\/reception$/);
  const found = await apiFromPage(page, "/api/v1/patients/search/", { q: "00000001" });
  await page.goto(`/patients/${found.body.results[0].id as string}`);
  await expect(page.getByRole("region", { name: "Registration details" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Clinical record" })).toHaveCount(0);
  const chart = await apiFromPage(page, `/api/v1/patients/${found.body.results[0].id as string}/chart/`);
  expect(chart.status).toBe(403);
});
