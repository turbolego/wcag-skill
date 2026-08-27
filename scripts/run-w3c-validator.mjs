#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { existsSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

function usage() {
  console.error("Usage: node scripts/run-w3c-validator.mjs <input.html> <output.json> [source-url]");
}

const [inputPath, outputPath, sourceUrl] = process.argv.slice(2);
if (!inputPath || !outputPath) {
  usage();
  process.exit(64);
}

const absoluteInput = resolve(inputPath);
if (!existsSync(absoluteInput)) {
  console.error(`Input file not found: ${absoluteInput}`);
  process.exit(66);
}

const result = spawnSync("vnu", ["--format", "json", absoluteInput], { encoding: "utf8" });
if (result.error) {
  console.error("Unable to start vnu. Install vnu-jar and ensure Java is available.");
  console.error(result.error.message);
  process.exit(69);
}

const rawReport = result.stdout.trim() || result.stderr.trim();
let parsed;
try {
  parsed = JSON.parse(rawReport);
} catch {
  console.error("Nu checker did not return JSON.");
  if (result.stderr) console.error(result.stderr.trim());
  process.exit(70);
}

// This report validates the raw HTTP response markup only. It does not see
// DOM mutations produced by JavaScript, authenticated routes, or other
// post-load states — those require the browser-based tools (axe, Pa11y,
// QualWeb) run against each relevant state.
const report = {
  scope: "source-html",
  scopeNote: "Validates the raw HTTP response body, not the JavaScript-rendered DOM.",
  sourceUrl: sourceUrl ?? null,
  messages: parsed.messages ?? [],
};

writeFileSync(resolve(outputPath), JSON.stringify(report));
process.exit(result.status ?? 1);

