import { type BrowserContext, expect, type Locator, type Page, test } from "@playwright/test";

import { apiFromPage, createUser, expectNoSeriousA11yIssues, signIn, signInEnrolling } from "./support";

// P1-WEB-04: users (create, deactivate, reset), role assignments with the approval inbox,
// licences, facility setup, break-glass review queue and the audit viewer — and every admin
// action shows up in the audit log. Two administrators, each in their own browser.

test.describe.configure({ mode: "serial" });

const suffix = Date.now().toString(36).slice(-6);
const newEmail = `staff-${suffix}@seed.afyasync.test`;
let contexts: BrowserContext[] = [];
let admin: Page; // facility administrator
let checker: Page; // second administrator, also data protection officer (reviews and audit)
let facilityId: number;

test.beforeAll(async ({ browser }) => {
  const first = createUser("facility_admin");
  const second = createUser("facility_admin", "dpo");
  contexts = [await browser.newContext(), await browser.newContext()];
  admin = await contexts[0]!.newPage();
  checker = await contexts[1]!.newPage();
  await signInEnrolling(admin, first.email);
  // Long scenario: widen the idle lock for the run (restored in afterAll); new sessions pick it up.
  const me = await apiFromPage(admin, "/api/v1/me");
  facilityId = me.body.facility.id;
  await patchFacility(admin, { workstation_lock_minutes: 30 });
  await signInEnrolling(checker, second.email);
});

test.afterAll(async () => {
  await patchFacility(admin, { workstation_lock_minutes: 5 });
  await Promise.all(contexts.map((c) => c.close()));
});

async function patchFacility(page: Page, body: Record<string, number>) {
  await page.evaluate(
    async ({ id, body }) => {
      const token = document.cookie.split("; ").find((c) => c.startsWith("csrftoken="))?.split("=")[1] ?? "";
      await fetch(`/api/v1/facilities/facilities/${id}/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "X-CSRFToken": token },
        body: JSON.stringify(body),
      });
    },
    { id: facilityId, body },
  );
}

async function openUser(page: Page, email: string): Promise<Locator> {
  await page.goto("/admin/users");
  await page.getByLabel("Find a user").fill(email);
  await page.getByRole("row", { name: new RegExp(email) }).getByRole("button").first().click();
  return page.getByRole("dialog");
}

async function grant(panel: Locator, page: Page, role: string, reason: string) {
  await panel.getByRole("combobox", { name: /Role/ }).click();
  await page.getByRole("option", { name: role, exact: true }).click();
  await panel.getByLabel(/^Reason/).fill(reason);
  await panel.getByRole("button", { name: "Grant role" }).click();
}

test("an administrator adds a user, grants roles, records a licence and resets credentials", async () => {
  await admin.goto("/admin/users");
  await expect(admin.getByRole("button", { name: "Add user" })).toBeVisible();
  await expectNoSeriousA11yIssues(admin);

  await admin.getByRole("button", { name: "Add user" }).click();
  const add = admin.getByRole("dialog", { name: "Add user" });
  await add.getByLabel(/E-mail address/).fill(newEmail);
  await add.getByLabel("Given name").fill("Synthetic");
  await add.getByLabel("Family name").fill("Newstaff");
  await add.getByRole("button", { name: "Add user" }).click();
  await expect(admin.getByTestId("temporary-password")).toHaveText(/\S{12,}/);
  await admin.getByRole("button", { name: "Done, grant roles" }).click();

  const panel = admin.getByRole("dialog", { name: "Synthetic Newstaff" });
  await expect(panel).toBeVisible();
  await expectNoSeriousA11yIssues(admin);
  await grant(panel, admin, "Nurse", "Ward nurse from Monday");
  await expect(panel.getByText("nurse", { exact: true })).toBeVisible();
  await grant(panel, admin, "Facility administrator", `Covering the administrator on leave ${suffix}`);
  await expect(panel.getByText("Waiting for a second administrator")).toBeVisible();

  await panel.getByRole("combobox", { name: /Regulator/ }).click();
  await admin.getByRole("option", { name: "Nursing Council of Kenya" }).click();
  await panel.getByLabel(/Registration number/).fill(`TEST-${suffix.toUpperCase()}`);
  await panel.getByLabel(/Valid to/).fill("31/12/2030");
  await panel.getByRole("button", { name: "Record licence" }).click();
  await panel.getByRole("button", { name: "Verify with the registry" }).click();
  await expect(panel.getByText("Verified")).toBeVisible();

  await panel.getByRole("button", { name: "Reset password and two-step" }).click();
  await expect(panel.getByTestId("temporary-password")).toHaveText(/\S{12,}/);
});

test("the second administrator approves the privileged grant", async () => {
  await checker.goto("/admin/approvals");
  const row = checker.getByRole("row").filter({ hasText: `Covering the administrator on leave ${suffix}` });
  await expect(row).toBeVisible();
  await expectNoSeriousA11yIssues(checker);
  await row.getByRole("button", { name: "Approve" }).click();
  await expect(checker.getByText("Request approved").first()).toBeVisible();
  const panel = await openUser(checker, newEmail);
  await expect(panel.getByText("facility_admin", { exact: true })).toBeVisible();
  await expect(panel.getByText("Waiting for a second administrator")).toHaveCount(0);
});

test("facility setup: departments, service points, wards and beds", async () => {
  await admin.goto("/admin/facility");
  await expect(admin.getByRole("heading", { name: "Facility details and security settings" })).toBeVisible();
  await expectNoSeriousA11yIssues(admin);
  const departments = admin.getByRole("region", { name: "Departments" });
  await departments.getByLabel(/^Code/).fill(`D${suffix}`.toUpperCase());
  await departments.getByLabel(/^Name/).fill(`Synthetic department ${suffix}`);
  await departments.getByRole("button", { name: "Add department" }).click();
  await expect(departments.getByText(`Synthetic department ${suffix}`)).toBeVisible();

  const points = admin.getByRole("region", { name: "Service points" });
  await points.getByLabel(/^Code/).fill(`SP${suffix}`.toUpperCase());
  await points.getByLabel(/^Name/).fill(`Synthetic room ${suffix}`);
  await points.getByRole("combobox", { name: /Kind/ }).click();
  await admin.getByRole("option", { name: "Treatment / procedure room" }).click();
  await points.getByRole("combobox", { name: /Department/ }).click();
  await admin.getByRole("option", { name: `Synthetic department ${suffix}` }).click();
  await points.getByRole("button", { name: "Add service point" }).click();
  await expect(points.getByRole("row").filter({ hasText: `Synthetic room ${suffix}` })).toContainText(`Synthetic department ${suffix}`);

  const wards = admin.getByRole("region", { name: "Wards and beds" });
  await wards.getByRole("button", { name: "Female medical ward" }).click();
  await expect(wards.getByText("FMW-01")).toBeVisible();
  await wards.getByLabel(/^Code/).first().fill(`W${suffix}`.toUpperCase());
  await wards.getByLabel(/^Name/).fill(`Synthetic ward ${suffix}`);
  await wards.getByRole("button", { name: "Add ward" }).click();
  await wards.getByRole("button", { name: `Synthetic ward ${suffix}` }).click();
  await expect(wards.getByRole("heading", { name: `Beds in Synthetic ward ${suffix}` })).toBeVisible();
  await wards.getByLabel(/^Bed code/).fill(`B${suffix}-01`.toUpperCase());
  await wards.getByRole("button", { name: "Add bed" }).click();
  await expect(wards.getByText(`B${suffix}-01`.toUpperCase())).toBeVisible();
  await expect(wards.getByRole("row").filter({ hasText: `Synthetic ward ${suffix}` })).toContainText("1");
});

test("break-glass is escalated in the review queue", async ({ browser }) => {
  // A clinician off the care team uses break-glass on a synthetic patient.
  const clinician = createUser("clinical_officer");
  const other = await browser.newContext();
  const clinicianPage = await other.newPage();
  await signIn(clinicianPage, clinician.email);
  await expect(clinicianPage).toHaveURL(/\/reception$/);
  const found = await apiFromPage(clinicianPage, "/api/v1/patients/search/?q=00000001");
  const patientId = found.body.results[0].id as string;
  const granted = await apiFromPage(clinicianPage, `/api/v1/patients/${patientId}/break-glass/`, {
    reason: "emergency",
    justification: `Collapsed at the gate ${suffix}, history needed now`,
  });
  expect(granted.status).toBe(201);
  await other.close();

  await checker.goto("/admin/break-glass");
  const row = checker.getByRole("row").filter({ hasText: `Collapsed at the gate ${suffix}` });
  await expectNoSeriousA11yIssues(checker);
  await row.getByRole("button", { name: "Escalate" }).click();
  const dialog = checker.getByRole("dialog", { name: "Escalate break-glass access" });
  await dialog.getByLabel(/Note/).fill("No visit on record");
  await dialog.getByRole("button", { name: "Escalate" }).click();
  await expect(checker.getByText("Escalated").first()).toBeVisible();
});

test("deactivating a user is immediate", async () => {
  const panel = await openUser(admin, newEmail);
  await panel.getByRole("button", { name: "Deactivate" }).click();
  const dialog = admin.getByRole("dialog", { name: /Deactivate/ });
  await dialog.getByLabel(/Reason/).fill("Left the facility");
  await dialog.getByRole("button", { name: "Deactivate" }).click();
  await expect(admin.getByRole("dialog", { name: "Synthetic Newstaff" }).getByText("Deactivated")).toBeVisible();
});

test("every admin action is in the audit log", async () => {
  await checker.goto("/admin/audit");
  await expectNoSeriousA11yIssues(checker);
  const show = async (action: string) => {
    await checker.getByLabel(/^Action/).fill(action);
    await checker.getByRole("button", { name: "Show events" }).click();
  };
  await show("admin.*");
  for (const action of ["admin.user.created", "admin.user.credentials_reset", "admin.user.deactivated"]) {
    await expect(checker.getByRole("row").filter({ hasText: action }).first()).toBeVisible();
  }
  await show("access.*");
  for (const action of ["access.assignment.granted", "access.approval.approved", "access.licence.verified", "access.breakglass.escalated"]) {
    await expect(checker.getByRole("row").filter({ hasText: action }).first()).toBeVisible();
  }
  await show("facilities.*");
  for (const action of ["facilities.department.created", "facilities.service_point.created", "facilities.ward.created", "facilities.bed.created"]) {
    await expect(checker.getByRole("row").filter({ hasText: action }).first()).toBeVisible();
  }
});
