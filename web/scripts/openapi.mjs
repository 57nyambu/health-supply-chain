// Generate src/lib/api/schema.d.ts from api/openapi.yaml, or with --check fail when the
// committed file is stale (make openapi / make openapi-check).
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import openapiTS, { astToString } from "openapi-typescript";

const schemaUrl = new URL("../../api/openapi.yaml", import.meta.url);
const target = fileURLToPath(new URL("../src/lib/api/schema.d.ts", import.meta.url));
const HEADER = "// Generated from api/openapi.yaml by `make openapi` — do not edit.\n\n";

const ast = await openapiTS(schemaUrl);
const generated = (HEADER + astToString(ast)).replace(/\r\n/g, "\n");

if (process.argv.includes("--check")) {
  let current = "";
  try {
    current = (await readFile(target, "utf8")).replace(/\r\n/g, "\n");
  } catch {
    // missing counts as stale
  }
  if (current !== generated) {
    console.error("web/src/lib/api/schema.d.ts is stale: run `make openapi` and commit the result.");
    process.exit(1);
  }
  console.log("openapi: typed client is up to date");
} else {
  await writeFile(target, generated, "utf8");
  console.log(`wrote ${target}`);
}
