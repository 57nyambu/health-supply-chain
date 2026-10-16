// make contrast: recompute every required pair from src/styles/tokens.css (DESIGN-SYSTEM §2.4).
import { readFile } from "node:fs/promises";

import { check, readTokens } from "./contrast-lib.mjs";

const css = await readFile(new URL("../src/styles/tokens.css", import.meta.url), "utf8");
const results = check(readTokens(css));
const failures = results.filter((r) => !r.ok);
for (const r of results) {
  const label = r.missing ? "missing token" : `${r.ratio.toFixed(2)} (≥ ${r.minimum})`;
  console.log(`${r.ok ? "ok  " : "FAIL"} ${r.fg} on ${r.bg}: ${label}`);
}
if (failures.length) {
  console.error(`contrast: ${failures.length} pair(s) below the required ratio`);
  process.exit(1);
}
console.log(`contrast: all ${results.length} pairs pass`);
