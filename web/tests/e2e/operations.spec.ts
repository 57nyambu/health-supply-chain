import { expect, test } from "@playwright/test";

import { createUser, expectNoSeriousA11yIssues, signIn } from "./support";

// P1-WEB-06: the legacy /admin, /facility and /reports dashboards as Next.js routes —
// facility operations and alerts in Reports, low stock and daily figures in Inventory.
// Synthetic seed data at the synthetic facility (apps/facility_ops/synthetic.py).

test("a report viewer sees facility operations and alerts, read-only", async ({ page }) => {
  await signIn(page, createUser("report_viewer").email);
  await expect(page).toHaveURL(/\/reports$/);
  await expect(page.getByRole("heading", { name: "Reports" })).toBeVisible();
  await expect(page.getByText("Patients, last 7 days")).toBeVisible();
  await expect(page.getByRole("table", { name: "Daily statistics, newest first" }).getByRole("row")).toHaveCount(8);
  await expectNoSeriousA11yIssues(page);

  await page.getByRole("tab", { name: "Facility alerts" }).click();
  await expect(page.getByRole("row").filter({ hasText: "Understaffed" }).first()).toBeVisible();
  await page.getByRole("tab", { name: "Low-stock alerts" }).click();
  await expect(page.getByRole("table", { name: "Low-stock alerts, open first" }).getByRole("row").nth(1)).toBeVisible();
  await expectNoSeriousA11yIssues(page);
  // Read-only: no other workspace, no AI.
  await expect(page.getByRole("navigation", { name: "Workspaces" }).getByRole("link")).toHaveCount(1);
});

test("store staff see low stock and daily figures in Inventory", async ({ page }) => {
  await signIn(page, createUser("store_keeper").email);
  await expect(page).toHaveURL(/\/inventory$/); // their first workspace
  await expect(page.getByRole("heading", { name: "Inventory" })).toBeVisible();
  await expect(page.getByRole("table", { name: "Low-stock alerts, open first" }).getByRole("row").nth(1)).toBeVisible();
  await expectNoSeriousA11yIssues(page);
  await page.getByRole("tab", { name: "Daily figures" }).click();
  await expect(page.getByText("Bed occupancy")).toBeVisible();
  await expectNoSeriousA11yIssues(page);
});
