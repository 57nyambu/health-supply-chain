import { expect, type Page, test } from "@playwright/test";

import { createBoardToken, createPatient, evidence, signInAs, syntheticName } from "../lanes/phase2";
import { apiFromPage, createUser, expectNoSeriousA11yIssues, signIn, signInEnrolling } from "../support";

// P2-VIS-01..03: reception opens a visit (journey rail moves to Triage, ticket issued), the
// triage queue calls the patient, and the TV board shows the ticket and room — never the name.

test.describe.configure({ mode: "serial" });

let reception: Page;
let patient: ReturnType<typeof createPatient>;

test.beforeAll(async ({ browser }) => {
  patient = createPatient();
  reception = await (await browser.newContext()).newPage();
  await signIn(reception, createUser("receptionist").email);
  await expect(reception).toHaveURL(/\/reception$/);
});

test.afterAll(async () => {
  await reception.context().close();
});

test("reception opens a visit from the patient record with the keyboard", async () => {
  await reception.goto(`/patients/${patient.id}`);
  const panel = reception.getByRole("region", { name: "Open a visit" });
  await expect(panel).toBeVisible();
  await expect(reception.getByRole("navigation", { name: "Visit journey" }).locator('[aria-current="step"]')).toHaveText("Reception");
  await expectNoSeriousA11yIssues(reception);
  await reception.keyboard.press("Alt+N");
  await expect(panel.getByRole("button", { name: "Open visit" })).toBeFocused();
  await reception.keyboard.press("Enter");
  const visit = reception.getByRole("region", { name: /^Visit OP-/ });
  await expect(visit).toBeVisible();
  await expect(visit.getByText("Waiting for triage")).toBeVisible();
  await expect(visit.getByRole("list", { name: "Queue tickets" })).toContainText("Triage 1");
  await expect(reception.getByRole("navigation", { name: "Visit journey" }).locator('[aria-current="step"]')).toHaveText("Triage");
  await expectNoSeriousA11yIssues(reception);
  await evidence(reception, "p2-vis-01-visit-opened");
});

test("triage calls the patient and the board shows the ticket without a name", async ({ browser }) => {
  const token = createBoardToken(`E2E board ${syntheticName()}`, ["TRI1"]);
  const nurse = await (await browser.newContext()).newPage();
  await signInAs(nurse, ["triage_nurse"], "/queue");
  await nurse.getByRole("combobox", { name: "Service point" }).click();
  await nurse.getByRole("option", { name: /^Triage 1/ }).click();
  const row = nurse.getByRole("row", { name: new RegExp(patient.family) });
  await expect(row).toBeVisible();
  await expectNoSeriousA11yIssues(nurse);
  const ticket = (await row.getByRole("cell").first().textContent())!.trim();
  await row.getByRole("button", { name: "Call" }).click();
  await expect(nurse.getByText(`Called ${ticket}`).first()).toBeVisible();
  await expect(row.getByText("Called", { exact: true })).toBeVisible();
  await evidence(nurse, "p2-vis-01-queue");

  const tv = await (await browser.newContext()).newPage();
  await tv.goto(`/board#${token}`);
  const now = tv.getByRole("region", { name: "Now serving" });
  await expect(now.getByText(ticket)).toBeVisible();
  await expect(tv.getByText(patient.family)).toHaveCount(0);
  await expect(tv.getByText(patient.given)).toHaveCount(0);
  expect(tv.url()).not.toContain(token); // the token leaves the address bar
  await evidence(tv, "p2-vis-03-board");
  await expectNoSeriousA11yIssues(tv);

  await row.getByRole("button", { name: "Start" }).click();
  await expect(row.getByText("Being seen")).toBeVisible();
  await tv.context().close();
  await nurse.context().close();
});

test("a board link that is wrong shows a clear message", async ({ browser }) => {
  const tv = await (await browser.newContext()).newPage();
  await tv.goto("/board#nope.nope");
  await expect(tv.getByText(/This board is not recognised/)).toBeVisible();
  await tv.context().close();
});

test("administrators see the gate matrix and set up a board link", async ({ browser }) => {
  const admin = await (await browser.newContext()).newPage();
  await signInEnrolling(admin, createUser("facility_admin").email);
  await admin.goto("/admin/gates");
  await expect(admin.getByText("Emergency care and discharge are never held for payment.")).toBeVisible();
  await expect(admin.getByRole("button", { name: /OPD consultation, Cash: Pay before service/ })).toBeVisible();
  await expectNoSeriousA11yIssues(admin);
  await evidence(admin, "p2-vis-02-gates");
  await admin.goto("/admin/boards");
  await admin.getByRole("button", { name: "Set up a board" }).click();
  const dialog = admin.getByRole("dialog", { name: "Set up a queue board" });
  await dialog.getByLabel(/Board name/).fill(`Lab area ${syntheticName()}`);
  await dialog.getByRole("checkbox", { name: "Laboratory" }).check();
  await dialog.getByRole("button", { name: "Create board" }).click();
  await expect(admin.getByText("Open this link on the TV now.")).toBeVisible();
  await expect(admin.getByText(/\/board#[0-9a-f]{8}\./)).toBeVisible();
  await expectNoSeriousA11yIssues(admin);
  await admin.context().close();
});

test("billing sends a price change for approval", async ({ browser }) => {
  const officer = await (await browser.newContext()).newPage();
  await signInAs(officer, ["billing_officer"], "/admin/services");
  const row = officer.getByRole("row", { name: /CONS-GEN/ });
  await expect(row).toContainText("500.00");
  await expectNoSeriousA11yIssues(officer);
  await evidence(officer, "p2-bil-01-services");
  await row.getByRole("button", { name: "Change price" }).click();
  const dialog = officer.getByRole("dialog");
  await dialog.getByLabel(/New price/).fill("550");
  await dialog.getByLabel(/^Reason/).fill("Annual review (synthetic)");
  await dialog.getByRole("button", { name: "Send for approval" }).click();
  await expect(officer.getByText("Price change sent for approval").first()).toBeVisible();
  const pending = await apiFromPage(officer, "/api/v1/billing/quote/?service=" + (await serviceId(officer, "CONS-GEN")));
  expect(pending.body.amount).toBe("500.00"); // unchanged until the finance manager approves
  await officer.context().close();
});

async function serviceId(page: Page, code: string): Promise<string> {
  const found = await apiFromPage(page, `/api/v1/billing/services/?q=${code}`);
  return found.body.results[0].id as string;
}
