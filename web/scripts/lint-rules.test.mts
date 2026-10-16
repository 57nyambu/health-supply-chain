// @vitest-environment node
import { ESLint } from "eslint";
import { beforeAll, describe, expect, it } from "vitest";

// DESIGN-SYSTEM §2 / web/CLAUDE.md: colours come from tokens; no PHI in the console.
describe("project lint rules", () => {
  const eslint = new ESLint({ cwd: process.cwd() });
  const lint = async (code: string) => {
    const [result] = await eslint.lintText(code, { filePath: "src/components/ui/sample.tsx" });
    return result?.messages.map((m) => m.message) ?? [];
  };

  // The first lint loads the config and the typed program for the whole project; that cold
  // start grows with the codebase, so it gets its own allowance and the checks keep theirs.
  beforeAll(async () => {
    await lint("export const warm = 1;\n");
  }, 240_000);

  it("rejects raw hex colours in components", async () => {
    const messages = await lint('export const Swatch = () => <div style={{ color: "#A3121A" }} />;\n');
    expect(messages.some((m) => m.includes("design token"))).toBe(true);
    const template = await lint("export const c = `border: 1px solid #fff`;\n");
    expect(template.some((m) => m.includes("design token"))).toBe(true);
  });

  it("accepts tokens and rejects console logging", async () => {
    expect(await lint('export const Swatch = () => <div style={{ color: "var(--color-danger)" }} />;\n')).toEqual([]);
    expect((await lint('export function f() {\n  console.log("x");\n}\n')).join(" ")).toMatch(/console/);
  });
}, 60_000);
