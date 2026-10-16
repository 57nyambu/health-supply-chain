// @vitest-environment node
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { check, contrast, parseHex, readTokens } from "./contrast-lib.mjs";

describe("contrast", () => {
  it("matches the WCAG reference values", () => {
    expect(contrast("#000000", "#ffffff")).toBeCloseTo(21, 5);
    expect(contrast("#ffffff", "#ffffff")).toBeCloseTo(1, 5);
    expect(contrast("#0B1220", "#FFFFFF")).toBeCloseTo(18.72, 1); // DESIGN-SYSTEM §2.3
    expect(contrast("#0B4F9C", "#DCE9F8")).toBeCloseTo(6.53, 1); // the documented failing pair
  });

  it("parses short and long hex", () => {
    expect(parseHex("#fff")).toEqual([255, 255, 255]);
    expect(() => parseHex("#12")).toThrow();
  });

  it("fails a pair below the minimum and reports missing tokens", () => {
    const results = check({ a: "#777777", b: "#888888" }, [["a", "b", 3], ["a", "nope", 3]]);
    expect(results.map((r) => r.ok)).toEqual([false, false]);
    expect(results[1]?.missing).toBe(true);
  });

  it("every required pair in tokens.css passes", () => {
    const css = readFileSync(new URL("../src/styles/tokens.css", import.meta.url), "utf8");
    expect(check(readTokens(css)).filter((r) => !r.ok)).toEqual([]);
  });
});
