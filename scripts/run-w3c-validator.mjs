#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { existsSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

function usage() {
  console.error("Usage: node scripts/run-w3c-validator.mjs <input.html> <output.json>");
}

const [inputPath, outputPath] = process.argv.slice(2);
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

const report = result.stdout.trim() || result.stderr.trim();
try {
  JSON.parse(report);
} catch {
  console.error("Nu checker did not return JSON.");
  if (result.stderr) console.error(result.stderr.trim());
  process.exit(70);
}

writeFileSync(resolve(outputPath), report);
process.exit(result.status ?? 1);
