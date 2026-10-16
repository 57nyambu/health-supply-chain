import { type BrowserContext, expect, type Page, test } from "@playwright/test";

import {
  apiFromPage,
  createUser,
  createUserWith,
  djangoShell,
  expectNoSeriousA11yIssues,
  signIn,
  signInEnrolling,
} from "../support";

// E2E-11 Access control (COMPLETION.md §2): reception can't open clinical notes (API 403,
// UI hides); a clinician off the care team sees the summary only; break-glass with a reason
// opens the full record for 60 minutes behind a banner, notifies the medical superintendent
// and the DPO, then expires; an expired licence blocks prescribing; a privileged role grant
// waits for a second administrator; the DPO sees all of it in the audit viewer.

test.describe.configure({ mode: "serial" });

const suffix = Date.now().toString(36).slice(-6);
let patientId: string;
let grantId: string;
const contexts: BrowserContext[] = [];

async function fresh(browser: import("@playwright/test").Browser): Promise<Page> {
  const context = await browser.newContext();
  contexts.push(context);
  return context.newPage();
}

test.afterAll(async () => {
  await Promise.all(contexts.map((c) => c.close()));
});

test("reception cannot open the clinical record: the UI hides it and the API refuses", async ({ browser }) => {
  const page = await fresh(browser);
  await signIn(page, createUser("receptionist").email);
  await expect(page).toHaveURL(/\/reception$/);
  await page.keyboard.type("00000005");
  await page.keyboard.press("Enter");
  await expect(page.locator("tbody tr").first()).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/patients\/[0-9a-f-]{36}$/);
  patientId = page.url().split("/").pop()!;
  await expect(page.getByRole("region", { name: "Registration details" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Clinical record" })).toHaveCount(0);
  await expectNoSeriousA11yIssues(page);
  const chart = await apiFromPage(page, `/api/v1/patients/${patientId}/chart/`);
  expect(chart.status).toBe(403);
});

test("off the care team: summary only; break-glass opens the full record for 60 minutes, notifies, then expires", async ({ browser }) => {
  const page = await fresh(browser);
  await signIn(page, createUser("clinical_officer").email);
  await expect(page).toHaveURL(/\/reception$/);
  await page.goto(`/patients/${patientId}`);
  const clinical = page.getByRole("region", { name: "Clinical record" });
  await expect(clinical.getByText("You see the summary because you are not on this patient's care team.")).toBeVisible();
  await expect(clinical.getByRole("heading", { name: "Notes" })).toHaveCount(0);
  const before = await apiFromPage(page, `/api/v1/patients/${patientId}/chart/`);
  expect([before.body.access.level, before.body.record]).toEqual(["summary", null]);
  await expectNoSeriousA11yIssues(page);

  await clinical.getByRole("button", { name: "Use emergency access" }).click();
  await page.keyboard.type(`Unresponsive at triage ${suffix}, needs the full history`);
  await page.getByRole("button", { name: "Open the full record" }).click();
  const banner = page.getByRole("status").filter({ hasText: "Every view is logged and reviewed" });
  await expect(banner).toBeVisible();
  await expect(clinical.getByRole("heading", { name: "Notes" })).toBeVisible();
  await expectNoSeriousA11yIssues(page);

  const during = await apiFromPage(page, `/api/v1/patients/${patientId}/chart/`);
  expect(during.body.access.level).toBe("full");
  grantId = during.body.access.break_glass.id as string;
  const minutes = (Date.parse(during.body.access.break_glass.expires_at) - Date.now()) / 60_000;
  expect(minutes).toBeGreaterThan(58);
  expect(minutes).toBeLessThanOrEqual(60);

  // Notices to the medical superintendent and the DPO: stored for each, then e-mailed
  // (delivery needs the mail server — mailpit in compose/CI — and is covered by the API
  // tests); they name the grant, never the patient.
  const notified = djangoShell(
    "from apps.integrations.models import Notification; " +
      `rows = Notification.objects.filter(message__contains='${grantId}'); ` +
      "print(sorted({r.user.email.split('@')[0] for r in rows}))",
  );
  expect(notified).toContain("medical_superintendent");
  expect(notified).toContain("dpo");
  const leaks = djangoShell(
    "from apps.integrations.models import Notification; " +
      `rows = Notification.objects.filter(message__contains='${grantId}'); ` +
      `print(sum(any(v in (r.subject + r.message) for v in ${JSON.stringify([before.body.patient.display_name, before.body.patient.mrn])}) for r in rows))`,
  );
  expect(leaks).toBe("0");

  // Sixty minutes pass (the grant's clock is moved to now — test-only DB access).
  djangoShell(
    "from django.utils import timezone; from apps.access.models import BreakGlassGrant; " +
      `print(BreakGlassGrant.objects.filter(pk='${grantId}').update(expires_at=timezone.now()))`,
  );
  await page.reload();
  await expect(clinical.getByText("You see the summary because you are not on this patient's care team.")).toBeVisible();
  await expect(banner).toHaveCount(0);
  const after = await apiFromPage(page, `/api/v1/patients/${patientId}/chart/`);
  expect([after.body.access.level, after.body.record, after.body.access.break_glass]).toEqual(["summary", null, null]);
});

test("an expired licence blocks prescribing and the full record, even on the care team", async ({ browser }) => {
  const licensed = await fresh(browser);
  await signIn(licensed, createUserWith({ roles: ["clinical_officer"], careTeam: patientId }).email);
  await expect(licensed).toHaveURL(/\/reception$/);
  const ok = await apiFromPage(licensed, "/api/v1/me");
  expect(ok.body.permissions).toContain("pharmacy.prescription.create");
  expect((await apiFromPage(licensed, `/api/v1/patients/${patientId}/chart/`)).body.access.level).toBe("full");

  const lapsed = await fresh(browser);
  await signIn(lapsed, createUserWith({ roles: ["clinical_officer"], careTeam: patientId, licenceExpired: true }).email);
  await expect(lapsed).toHaveURL(/\/reception$/);
  const me = await apiFromPage(lapsed, "/api/v1/me");
  expect(me.body.permissions).not.toContain("pharmacy.prescription.create");
  expect(me.body.permissions).not.toContain("clinical.record.read_full");
  // No consultation workspace without a valid licence.
  await expect(lapsed.getByRole("navigation", { name: "Workspaces" }).getByRole("link", { name: "Consultation" })).toHaveCount(0);
  const chart = await apiFromPage(lapsed, `/api/v1/patients/${patientId}/chart/`);
  expect([chart.body.access.care_team, chart.body.access.level, chart.body.record]).toEqual([true, "summary", null]);
});

test("a privileged grant waits for a second administrator, and the DPO sees everything in the audit viewer", async ({ browser }) => {
  const admin = await fresh(browser);
  const dpo = await fresh(browser);
  await signInEnrolling(admin, createUser("facility_admin").email);
  await signInEnrolling(dpo, createUser("facility_admin", "dpo").email);
  const target = createUser("nurse");
  const granted = await apiFromPage(admin, "/api/v1/access/assignments/", {
    user: target.id,
    role: "facility_admin",
    reason: `Acting administrator ${suffix}`,
  });
  expect([granted.status, granted.body.status]).toEqual([201, "pending_approval"]);
  // The requesting administrator cannot approve their own request.
  await admin.goto("/admin/approvals");
  const own = admin.getByRole("row").filter({ hasText: `Acting administrator ${suffix}` });
  await expect(own).toBeVisible();
  await expect(own.getByRole("button", { name: "Approve" })).toHaveCount(0);

  await dpo.goto("/admin/approvals");
  const row = dpo.getByRole("row").filter({ hasText: `Acting administrator ${suffix}` });
  await row.getByRole("button", { name: "Approve" }).click();
  await expect(dpo.getByText("Request approved").first()).toBeVisible();

  await dpo.goto("/admin/audit");
  await expectNoSeriousA11yIssues(dpo);
  const show = async (action: string) => {
    await dpo.getByLabel(/^Action/).fill(action);
    await dpo.getByRole("button", { name: "Show events" }).click();
  };
  // Reception's refused request for the clinical record (step one) is on record.
  await show("access.denied");
  await expect(dpo.getByRole("row").filter({ hasText: "access.denied" }).first()).toBeVisible();
  await show("access.*");
  for (const action of ["access.breakglass.granted", "access.approval.requested", "access.approval.approved", "access.care_team.added"]) {
    await expect(dpo.getByRole("row").filter({ hasText: action }).first()).toBeVisible();
  }
  await dpo.goto("/admin/break-glass");
  await expect(dpo.getByRole("row").filter({ hasText: `Unresponsive at triage ${suffix}` })).toBeVisible();
});
