import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

// P1-WEB-02: the component catalogue is accessible, focus is always visible, and the
// design system honours forced colours and reduced motion (DESIGN-SYSTEM §4, §5).

test.beforeEach(async ({ page }) => {
  await page.goto("/design");
  await expect(page.getByRole("heading", { name: "Design system" })).toBeVisible();
});

test("the catalogue has no serious or critical accessibility violations", async ({ page }) => {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  const blocking = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(blocking.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
});

test("keyboard focus shows the two-ring indicator", async ({ page }) => {
  const button = page.getByRole("button", { name: "Open visit" });
  await button.focus();
  await page.keyboard.press("Shift+Tab");
  await page.keyboard.press("Tab");
  await expect(button).toBeFocused();
  const style = await button.evaluate((el) => {
    const s = getComputedStyle(el);
    return { outline: `${s.outlineStyle} ${s.outlineWidth}`, shadow: s.boxShadow };
  });
  expect(style.outline).toBe("solid 2px");
  expect(style.shadow).toContain("rgb(255, 212, 0)");
  expect(style.shadow).toContain("4px");
});

test("text uses Atkinson Hyperlegible Next with tabular figures for numbers", async ({ page }) => {
  const fonts = await page.evaluate(() => getComputedStyle(document.body).fontFamily);
  expect(fonts).toMatch(/Atkinson/);
  const numeric = await page.getByText("Tabular figures").evaluate((el) => getComputedStyle(el).fontVariantNumeric);
  expect(numeric).toBe("tabular-nums");
});

test("forced colours keep borders and words on controls and triage tags", async ({ page }) => {
  await page.emulateMedia({ forcedColors: "active" });
  const border = await page.getByRole("button", { name: "Record vitals" }).evaluate((el) => getComputedStyle(el).borderStyle);
  expect(border).toBe("solid");
  await expect(page.getByText("Red (emergency)").first()).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter((v) => v.impact === "critical")).toEqual([]);
});

test("reduced motion removes transitions", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  const duration = await page.getByRole("button", { name: "Open visit" }).evaluate((el) => getComputedStyle(el).transitionDuration);
  expect(duration).toBe("0s");
});

test("dialogs trap focus and close with Escape; toasts announce the action", async ({ page }) => {
  await page.getByRole("button", { name: "Open dialog" }).click();
  const dialog = page.getByRole("dialog", { name: "Record vitals" });
  await expect(dialog).toBeVisible();
  await page.keyboard.press("Tab");
  expect(await dialog.evaluate((el) => el.contains(document.activeElement))).toBe(true);
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await page.getByRole("region", { name: "Toast and dialog" }).getByRole("button", { name: "Release result" }).click();
  // Radix also renders an off-screen copy for the live-region announcement.
  await expect(page.getByText("Result released").first()).toBeVisible();
});
