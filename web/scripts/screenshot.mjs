// node scripts/screenshot.mjs <path> <output.png> — full-page screenshot of a dev-server page
// for docs/evidence/screens (synthetic data only).
import { chromium } from "@playwright/test";

const [path = "/", output = "screenshot.png"] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, locale: "en-KE", timezoneId: "Africa/Nairobi" });
await page.goto(new URL(path, "http://127.0.0.1:3000").toString(), { waitUntil: "networkidle" });
await page.screenshot({ path: output, fullPage: true });
await browser.close();
console.log(`wrote ${output}`);
