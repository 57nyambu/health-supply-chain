import { expect, test } from "@playwright/test";

import { createUser, expectNoSeriousA11yIssues, signIn } from "./support";

// make smoke (part of make check): sign in, open a workspace, no serious accessibility issues.
test("smoke: sign in and open a workspace", async ({ page }) => {
  const { email } = createUser("receptionist");
  await signIn(page, email);
  await expect(page).toHaveURL(/\/reception$/);
  await expect(page.getByRole("navigation", { name: "Workspaces" })).toBeVisible();
  await expectNoSeriousA11yIssues(page);
});
