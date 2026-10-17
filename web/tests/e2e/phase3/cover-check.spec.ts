import { expect, type Page, test } from "@playwright/test";

import { createUser, djangoShell, expectNoSeriousA11yIssues, signInEnrolling } from "../support";

// Phase 3 stage A in fake mode (P3-SHA-01, P3-SHA-02; slot W1): a claims officer checks a
// patient's SHA cover against the fake HIE and takes visit consent by SMS code. Synthetic
// seed patients are picked by the last two digits of their national ID (ADR-073):
// 11 eligible, 98 suspended for arrears.

test.describe.configure({ mode: "serial" });

/** National ID of the seeded patient with SHA cover whose national ID ends with ``suffix``. */
function idFor(suffix: string): string {
  return djangoShell(
    [
      "from apps.patients.models import PatientIdentifier",
      "from apps.insurance.models import Coverage",
      `rows = sorted((r for r in PatientIdentifier.objects.filter(type='national_id', active=True).select_related('patient') if r.value.endswith('${suffix}') and Coverage.objects.filter(patient=r.patient, scheme__code='shif', active=True).exists()), key=lambda r: r.value)`,
      "print(rows[0].value)",
    ].join("\n"),
  );
}

const SHA = "Social Health Authority (SHA) — Social Health Insurance Fund (SHIF)";

async function openCover(page: Page, nationalId: string) {
  await page.goto("/claims");
  await expect(page.getByRole("heading", { name: "Claims", level: 1 })).toBeVisible();
  await page.getByLabel("Find the patient").fill(nationalId);
  await page.getByRole("button", { name: "Search" }).click();
  await page.getByRole("button", { name: "Check cover" }).first().click();
  const cover = page.getByRole("region", { name: SHA });
  await expect(cover).toBeVisible();
  return cover;
}

test("an eligible SHA member: check eligibility, then consent by SMS code", async ({ page }) => {
  await signInEnrolling(page, createUser("claims_officer").email);
  const cover = await openCover(page, idFor("11"));
  await cover.getByRole("button", { name: /Check (eligibility|again)/ }).click();
  await expect(cover.getByText("Eligible", { exact: true })).toBeVisible();
  await cover.getByRole("button", { name: "Send SMS code" }).click();
  await expect(cover.getByText("Which phone should get the code?")).toBeVisible();
  await expect(cover.getByRole("radio", { name: "+254700***001" })).toBeChecked();
  await cover.getByRole("button", { name: "Send code" }).click();
  const code = cover.getByLabel(/Code the member received/);
  await code.fill("000000");
  await cover.getByRole("button", { name: "Confirm consent" }).click();
  await expect(cover.getByText(/The code is not correct/)).toBeVisible();
  await code.fill("123456");
  await cover.getByRole("button", { name: "Confirm consent" }).click();
  await expect(cover.getByText("Consent recorded for this visit")).toBeVisible();
  await expectNoSeriousA11yIssues(page);
  await page.screenshot({ path: "test-results/phase3-cover-check.png", fullPage: true });
});

test("a suspended SHA member is told why, and nothing is blocked", async ({ page }) => {
  await signInEnrolling(page, createUser("claims_officer").email);
  const cover = await openCover(page, idFor("98"));
  await cover.getByRole("button", { name: /Check (eligibility|again)/ }).click();
  await expect(cover.getByText("Cover inactive")).toBeVisible();
  await expect(cover.getByText(/Contributions in arrears/)).toBeVisible();
  await expect(cover.getByRole("button", { name: "Send SMS code" })).toHaveCount(0);
  await expectNoSeriousA11yIssues(page);
});
