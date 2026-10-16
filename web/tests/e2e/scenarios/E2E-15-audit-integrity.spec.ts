import { expect, test } from "@playwright/test";

import { apiFromPage, createUser, djangoShell, expectNoSeriousA11yIssues, manage, signIn, signInEnrolling } from "../support";

// E2E-15 Audit integrity (COMPLETION.md §2): perform audited actions; alter one audit row
// directly in the database (as someone with DBA access would, past the append-only
// trigger); `make audit-verify` reports the exact break; restore the row and it passes.

test("tampering with one audit row is found and located; restoring it verifies again", async ({ browser }) => {
  test.setTimeout(240_000); // three full chain verifications of today's facility chain
  // Audited actions through the UI: a receptionist finds and opens a record.
  const page = await (await browser.newContext()).newPage();
  const receptionist = createUser("receptionist");
  await signIn(page, receptionist.email);
  await expect(page).toHaveURL(/\/reception$/);
  await page.keyboard.type("00000006");
  await page.keyboard.press("Enter");
  await expect(page.locator("tbody tr").first()).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("region", { name: "Registration details" })).toBeVisible();
  const me = await apiFromPage(page, "/api/v1/me");
  const facility = String(me.body.facility.id);
  const today = new Date().toLocaleDateString("en-CA", { timeZone: "Africa/Nairobi" });
  const scope = ["--facility", facility, "--from", today, "--to", today];

  expect(manage(["audit_verify", ...scope]).status).toBe(0);

  // The receptionist's chart open, as stored: id, sequence and original action.
  const [eventId, seq, action] = djangoShell(
    "from apps.audit.models import AuditEvent; " +
      `e = AuditEvent.objects.filter(actor_id=${receptionist.id}, action='patients.chart.opened').latest('ts'); ` +
      "print(e.id, e.seq, e.action)",
  ).split(" ");
  expect(action).toBe("patients.chart.opened");

  const rewrite = (value: string) =>
    djangoShell(
      "from django.db import connection, transaction\n" +
        "with transaction.atomic(), connection.cursor() as c:\n" +
        "    c.execute('ALTER TABLE audit_auditevent DISABLE TRIGGER audit_auditevent_append_only')\n" +
        `    c.execute('UPDATE audit_auditevent SET action = %s WHERE id = %s', ['${value}', '${eventId}'])\n` +
        "    c.execute('ALTER TABLE audit_auditevent ENABLE TRIGGER audit_auditevent_append_only')\n" +
        "    print(c.rowcount)",
    );

  try {
    rewrite("patients.patient.searched"); // an insider hides that the record was opened
    const tampered = manage(["audit_verify", ...scope]);
    expect(tampered.status).not.toBe(0);
    expect(tampered.stderr).toContain(`facility ${facility} ${today} seq ${seq}`);
    expect(tampered.stderr).toMatch(/problem\(s\)/);
  } finally {
    rewrite(action!);
  }
  const restored = manage(["audit_verify", ...scope]);
  expect(restored.status).toBe(0);
  expect(restored.stdout).toContain("chains intact");

  // The DPO can see the event in the viewer, unchanged.
  const dpo = await (await browser.newContext()).newPage();
  await signInEnrolling(dpo, createUser("dpo").email);
  await dpo.goto("/admin/audit");
  await dpo.getByLabel(/^Action/).fill("patients.chart.opened");
  await dpo.getByLabel(/^User ID/).fill(String(receptionist.id));
  await dpo.getByRole("button", { name: "Show events" }).click();
  await expect(dpo.getByRole("row").filter({ hasText: "patients.chart.opened" }).first()).toBeVisible();
  await expectNoSeriousA11yIssues(dpo);
  await Promise.all([page.context().close(), dpo.context().close()]);
});
