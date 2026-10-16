import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    // Colours come only from design tokens (DESIGN-SYSTEM §2, §10). (esquery regexes cannot use .)
    files: ["src/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-syntax": [
        "error",
        {
          selector: "Literal[value=/#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})([^0-9a-zA-Z]|$)/]",
          message: "Use a design token (var(--color-…) or a Tailwind token class), not a raw hex colour.",
        },
        {
          selector: "TemplateElement[value.raw=/#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})([^0-9a-zA-Z]|$)/]",
          message: "Use a design token (var(--color-…) or a Tailwind token class), not a raw hex colour.",
        },
      ],
      // No PHI in the console (web/CLAUDE.md).
      "no-console": ["error", { allow: ["error"] }],
    },
  },
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts", "src/lib/api/schema.d.ts", "playwright-report/**", "test-results/**"]),
]);
