#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash scripts/a11y-audit.sh <http-url> [output-directory]

Run axe, Pa11y, QualWeb ACT rules, and Nu HTML validation against an HTTP page.
Prerequisites: axe, pa11y, vnu, curl, node, @qualweb/cli, Chrome/Chromium, and
matching Chromedriver. Override browser discovery with AXE_CHROME_PATH and
AXE_CHROMEDRIVER_PATH.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage >&2
  exit 64
fi

url="$1"
out_dir="${2:-a11y-reports}"
mkdir -p "$out_dir"

# Prefer tools pinned in package.json (installed via `npm ci`) over anything
# found elsewhere on PATH, for reproducible tool versions.
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -d "$repo_root/node_modules/.bin" ]]; then
  PATH="$repo_root/node_modules/.bin:$PATH"
fi

for command in axe pa11y vnu curl node npm; do
  command -v "$command" >/dev/null || {
    echo "Missing required command: $command" >&2
    exit 69
  }
done

chrome_path="${AXE_CHROME_PATH:-}"
if [[ -z "$chrome_path" ]]; then
  chrome_path="$(command -v google-chrome || command -v chromium || command -v chromium-browser || true)"
fi
driver_path="${AXE_CHROMEDRIVER_PATH:-$(command -v chromedriver || true)}"
[[ -n "$chrome_path" ]] || { echo "Chrome/Chromium was not found." >&2; exit 69; }
[[ -n "$driver_path" ]] || { echo "Chromedriver was not found." >&2; exit 69; }

qualweb_cli="$repo_root/node_modules/@qualweb/cli/dist/cli.js"
if [[ ! -f "$qualweb_cli" ]]; then
  qualweb_cli="$(npm root -g)/@qualweb/cli/dist/cli.js"
fi
[[ -f "$qualweb_cli" ]] || { echo "@qualweb/cli was not found at $qualweb_cli" >&2; exit 69; }

echo "Running axe..."
axe "$url" --chrome-path "$chrome_path" --chromedriver-path "$driver_path" --stdout > "$out_dir/axe_report.json"

echo "Running Pa11y..."
PUPPETEER_EXECUTABLE_PATH="$chrome_path" pa11y "$url" --reporter json > "$out_dir/pa11y_report.json"

echo "Running QualWeb ACT rules..."
PUPPETEER_EXECUTABLE_PATH="$chrome_path" node "$qualweb_cli" -u "$url" -m act-rules --act-levels A AA AAA -o "$out_dir/qualweb_report.json"

echo "Running Nu HTML Checker..."
html_file="$out_dir/fetched-page.html"
curl --fail --location --silent --show-error "$url" > "$html_file"
node "$(dirname "$0")/run-w3c-validator.mjs" "$html_file" "$out_dir/w3c_source_html_report.json" "$url"

echo "Reports written to $out_dir"
