import { expect, test } from "@playwright/test";

import { apiFromPage, createUser, expectNoSeriousA11yIssues, signIn, totp } from "./support";

// P1-WEB-03: sign-in, MFA enrolment and challenge, lock screen with PIN, session-expired and
// 403 pages, and the role-aware shell — keyboard only where the acceptance criteria say so.

test("keyboard-only sign-in opens the user's workspace", async ({ page }) => {
  const { email } = createUser("receptionist");
  await expectNoSeriousA11yIssuesAt(page, "/login");
  await signIn(page, email);
  await expect(page).toHaveURL(/\/reception$/);
  const nav = page.getByRole("navigation", { name: "Workspaces" });
  await expect(nav.getByRole("link")).toHaveText(["Reception"]);
  await expectNoSeriousA11yIssues(page);
});

test("a wrong password is refused with a specific message", async ({ page }) => {
  const { email } = createUser("receptionist");
  await signIn(page, email, "not-the-right-password-1");
  await expect(page.getByRole("alert").filter({ hasText: "not correct" })).toHaveText(
    "The e-mail address or password is not correct.",
  );
  await expect(page).toHaveURL(/\/login$/);
});

test("privileged roles enrol an authenticator, then answer the challenge", async ({ page }) => {
  const { email } = createUser("facility_admin");
  await signIn(page, email);
  await expect(page).toHaveURL(/\/mfa\/setup$/);
  const secret = (await page.getByTestId("totp-secret").textContent())!.replace(/\s/g, "");
  await expect(page.getByLabel(/6-digit code/)).toBeFocused();
  await page.keyboard.type(totp(secret));
  await page.keyboard.press("Enter");
  const items = page.getByRole("list", { name: "Recovery codes" }).getByRole("listitem");
  await expect(items).toHaveCount(10);
  const codes = await items.allTextContents();
  await expectNoSeriousA11yIssues(page);
  await page.keyboard.press("Enter"); // "I have saved them, continue" has focus
  await expect(page).toHaveURL(/\/admin$/);

  // Next sign-in asks for the second factor; a recovery code works once.
  await apiFromPage(page, "/api/v1/auth/logout", {});
  await signIn(page, email);
  await expect(page).toHaveURL(/\/mfa$/);
  await expectNoSeriousA11yIssues(page);
  await page.getByRole("button", { name: "Use a recovery code instead" }).click();
  await page.getByLabel(/Recovery code/).fill(codes[0]!);
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/admin$/);
});

test("keyboard-only lock and unlock with a PIN", async ({ page }) => {
  const { email } = createUser("receptionist");
  await signIn(page, email);
  await expect(page).toHaveURL(/\/reception$/);
  const saved = await apiFromPage(page, "/api/v1/auth/pin", { pin: "246813", password: process.env.SEED_PASSWORD });
  expect(saved.status).toBe(204);

  await page.keyboard.press("Alt+L");
  await expect(page).toHaveURL(/\/locked$/);
  await expect(page.getByRole("heading", { name: "Workstation locked" })).toBeVisible();
  await expectNoSeriousA11yIssues(page);
  // While locked the API refuses patient data.
  expect((await apiFromPage(page, "/api/v1/patients/search/?q=000")).body.code).toBe("workstation_locked");

  await expect(page.getByLabel(/PIN/)).toBeFocused();
  await page.keyboard.type("111111");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("alert").filter({ hasText: "PIN" })).toHaveText("The PIN is not correct.");
  await page.keyboard.type("246813");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/reception$/);
});

test("a colleague switches in on the locked workstation with their own PIN", async ({ page }) => {
  const first = createUser("receptionist");
  const second = createUser("receptionist", "nurse");
  // The colleague must have signed in on this workstation before (DESIGN §7.2).
  await signIn(page, second.email);
  await expect(page).toHaveURL(/\/reception$/);
  await apiFromPage(page, "/api/v1/auth/pin", { pin: "135792", password: process.env.SEED_PASSWORD });
  await apiFromPage(page, "/api/v1/auth/logout", {});
  await signIn(page, first.email);
  await expect(page).toHaveURL(/\/reception$/);
  await page.keyboard.press("Alt+L");
  await page.getByRole("button", { name: "Switch user" }).click();
  await page.getByLabel(/E-mail address/).fill(second.email);
  await page.getByLabel(/PIN/).fill("135792");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/reception$/);
  // The shell now belongs to the second user, with their workspaces.
  await expect(page.getByRole("navigation", { name: "Workspaces" }).getByRole("link")).toHaveText(["Reception", "Wards"]);
});

test("workspace switcher lists only the user's workspaces", async ({ page }) => {
  const { email } = createUser("receptionist", "nurse");
  await signIn(page, email);
  await expect(page).toHaveURL(/\/reception$/);
  await page.getByRole("button", { name: /Workspace: Reception/ }).focus();
  await page.keyboard.press("Enter"); // opens with the first item focused
  await expect(page.getByRole("menuitem")).toHaveText(["Reception", "Wards"]);
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/wards$/);
  await expect(page.getByText("The wards workspace arrives in Phase 2.")).toBeVisible();
  await page.goto("/admin");
  await expect(page.getByText("This workspace is not available to your roles.")).toBeVisible();
});

test("session-ended and access pages", async ({ page }) => {
  for (const [path, heading] of [
    ["/session-expired", "Your session has ended"],
    ["/forbidden", "You do not have access to this"],
    ["/no-access", "No workspace for your roles yet"],
  ] as const) {
    await page.goto(path);
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    await expectNoSeriousA11yIssues(page);
  }
  // Signed-out visitors to a workspace are sent to sign in.
  await page.goto("/reception");
  await expect(page).toHaveURL(/\/login$/);
});

async function expectNoSeriousA11yIssuesAt(page: import("@playwright/test").Page, path: string) {
  await page.goto(path);
  await expectNoSeriousA11yIssues(page);
}
