import { expect, type Page, test } from "@playwright/test";

import { createUser, expectNoSeriousA11yIssues, signIn } from "./support";

// P1-WEB-05: search before create (local and Client Registry fake), registration with the
// privacy notice, duplicate warning with override, unidentified quick registration, and a
// returning patient found and updated keyboard-only in under a minute. Synthetic data only.

test.describe.configure({ mode: "serial" });

let page: Page;

/** A made-up name no one else in the seed has (consonant-vowel syllables). */
function syntheticName(syllables = 3): string {
  const consonants = "bdfghjklmnprstw";
  const vowels = "aeiou";
  let word = "";
  for (let i = 0; i < syllables; i++) {
    word += consonants[Math.floor(Math.random() * consonants.length)]! + vowels[Math.floor(Math.random() * vowels.length)]!;
  }
  return word[0]!.toUpperCase() + word.slice(1);
}

const given = syntheticName();
const family = syntheticName(4);
// Unique per run: a shared number would match other patients' phones (a likely duplicate).
const phone = `07${String(Math.floor(Math.random() * 1e8)).padStart(8, "0")}`;

test.beforeAll(async ({ browser }) => {
  const receptionist = createUser("receptionist");
  page = await (await browser.newContext()).newPage();
  await signIn(page, receptionist.email);
  await expect(page).toHaveURL(/\/reception$/);
});

test.afterAll(async () => {
  await page.context().close();
});

async function registerByKeyboard(name: { given: string; family: string }, dob: string, override?: string) {
  const form = page.getByRole("region", { name: "Register a new patient" });
  await expect(form.getByLabel(/^Given name/)).toBeFocused();
  await expect(form.getByLabel(/^Given name/)).toHaveValue(name.given);
  await expect(form.getByLabel(/^Family name/)).toHaveValue(name.family);
  await form.getByRole("combobox", { name: /^Sex/ }).focus();
  await page.keyboard.press("Enter");
  await page.getByRole("option", { name: "Female" }).press("Enter");
  await form.getByRole("textbox", { name: /^Date of birth/ }).fill(dob);
  await form.getByLabel(/^Phone/).fill(phone);
  await form.getByLabel(/^Next of kin name/).fill("Synthetic Kin");
  await form.getByLabel(/^Relationship/).fill("sister");
  await form.getByRole("checkbox", { name: /I gave this privacy notice/ }).check();
  await form.getByRole("button", { name: "Register patient" }).click();
  if (override) {
    await expect(form.getByText("This looks like a patient who is already registered.")).toBeVisible();
    await expectNoSeriousA11yIssues(page);
    await form.getByLabel(/^Reason to register anyway/).fill(override);
    await form.getByRole("button", { name: "Register anyway" }).click();
  }
  await expect(page).toHaveURL(/\/patients\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("region", { name: "Patient" }).getByRole("heading", { name: `${name.given} ${name.family}` })).toBeVisible();
}

test("search before create: nothing found, then register with the privacy notice", async () => {
  await expectNoSeriousA11yIssues(page);
  await expect(page.getByRole("button", { name: "Register new patient" })).toBeDisabled();
  // "/" brings the keyboard back to the search box from anywhere on the page.
  await page.getByRole("heading", { name: "Reception" }).click();
  await page.keyboard.press("/");
  await expect(page.getByLabel(/ID, phone, MRN or name/)).toBeFocused();
  await page.keyboard.type(`${given} ${family}`);
  await page.keyboard.press("Enter");
  await expect(page.getByText("No patient here matches.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Register new patient" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expectNoSeriousA11yIssues(page);
  await registerByKeyboard({ given, family }, "14/03/1991");
  const details = page.getByRole("region", { name: "Registration details" });
  await expect(details.getByText("Privacy notice given")).toBeVisible();
  await expect(details.getByText(`+254${phone.slice(1)}`)).toBeVisible();
  await expect(details.getByText("Synthetic Kin")).toBeVisible();
  await expectNoSeriousA11yIssues(page);
});

test("a second registration of the same person is warned, and needs a reason to go ahead", async () => {
  await page.goto("/reception");
  await page.getByLabel(/ID, phone, MRN or name/).fill(`${given} ${family}`);
  await page.keyboard.press("Enter");
  await expect(page.getByRole("row", { name: new RegExp(`${given} ${family}`) })).toBeVisible();
  await page.getByRole("button", { name: "Register new patient" }).click();
  await registerByKeyboard({ given, family }, "14/03/1991", "Twin sister with the same name, confirmed with ID");
});

test("Client Registry: a match is registered with its verified CR ID; an outage never blocks", async () => {
  await page.goto("/reception");
  const registry = page.getByRole("region", { name: "Client Registry (national)" });
  const number = `19${String(Math.floor(Math.random() * 1e7)).padStart(7, "0")}`;
  await registry.getByLabel(/^Number/).fill("99999999");
  await registry.getByRole("button", { name: "Search the registry" }).click();
  await expect(registry.getByText("The Client Registry did not answer.")).toBeVisible();

  await registry.getByLabel(/^Number/).fill(number);
  await registry.getByRole("button", { name: "Search the registry" }).click();
  await expect(registry.getByText("In the Client Registry")).toBeVisible();
  await expectNoSeriousA11yIssues(page);
  await registry.getByRole("checkbox", { name: /I gave this privacy notice/ }).check();
  await registry.getByRole("button", { name: "Register from the Client Registry" }).click();
  await expect(page).toHaveURL(/\/patients\/[0-9a-f-]{36}$/);
  const details = page.getByRole("region", { name: "Registration details" });
  // The CR ID and the national ID both come from the registry, so both are verified.
  for (const value of [`CR-SYN-G${number}`, number]) {
    const row = details.getByRole("listitem").filter({ has: page.getByText(value, { exact: true }) });
    await expect(row.getByText("Verified with the Client Registry")).toBeVisible();
  }

  // Searching the same number again offers the existing record instead of a second one.
  await page.goto("/reception");
  await registry.getByLabel(/^Number/).fill(number);
  await registry.getByRole("button", { name: "Search the registry" }).click();
  await expect(registry.getByText("Already registered at this facility.")).toBeVisible();
});

test("an unidentified emergency patient is registered in seconds with a temporary ID", async () => {
  await page.goto("/reception");
  await page.getByRole("button", { name: "Unidentified emergency patient" }).click();
  const dialog = page.getByRole("dialog", { name: "Unidentified emergency patient" });
  await dialog.getByLabel(/Approximate age/).fill("40");
  await expectNoSeriousA11yIssues(page);
  await dialog.getByRole("button", { name: "Register unidentified patient" }).click();
  await expect(page).toHaveURL(/\/patients\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("navigation", { name: "Visit journey" }).getByText("Emergency")).toBeVisible();
  await expect(page.getByRole("region", { name: "Registration details" }).getByText(/^ER-\d{4}-\d{4,}$/)).toBeVisible();
});

test("a returning patient is found and updated keyboard-only in under 60 seconds", async () => {
  await page.goto("/reception");
  await expect(page.getByLabel(/ID, phone, MRN or name/)).toBeFocused();
  const started = Date.now();
  // Seed patient with national ID 00000001 (synthetic); only keys from here on.
  await page.keyboard.type("00000001");
  await page.keyboard.press("Enter");
  await expect(page.locator("tbody tr").first()).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/patients\/[0-9a-f-]{36}$/);
  const addPhone = page.getByRole("button", { name: "Add phone" });
  await expect(addPhone).toBeVisible();
  for (let i = 0; i < 15 && !(await addPhone.evaluate((el) => el === document.activeElement)); i++) {
    await page.keyboard.press("Tab");
  }
  await expect(addPhone).toBeFocused();
  await page.keyboard.press("Enter");
  const newPhone = `07${String(Math.floor(Math.random() * 1e8)).padStart(8, "0")}`;
  await page.keyboard.type(newPhone);
  await page.keyboard.press("Enter");
  await expect(page.getByText("Phone added").first()).toBeVisible();
  const e164 = `+254${newPhone.slice(1)}`;
  await expect(page.getByRole("region", { name: "Registration details" }).getByText(e164)).toBeVisible();
  const elapsed = Date.now() - started;
  test.info().annotations.push({ type: "returning-patient-ms", description: String(elapsed) });
  expect(elapsed).toBeLessThan(60_000);
});
