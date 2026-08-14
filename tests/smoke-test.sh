#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

python3 -m py_compile benchmark/scripts/check-tag-coverage.py
node --check scripts/run-w3c-validator.mjs
bash scripts/a11y-audit.sh --help >/dev/null

node scripts/run-w3c-validator.mjs tests/fixtures/valid-page.html "$tmp_dir/w3c_report.json"
grep -q '"messages":\[\]' "$tmp_dir/w3c_report.json"

python3 benchmark/scripts/check-tag-coverage.py benchmark/templates/index.html > "$tmp_dir/tag_report.txt"
grep -q 'Missing: 0' "$tmp_dir/tag_report.txt"

CLAWHUB_TOKEN=smoke-test-token python3 scripts/publish-web.py --dry-run > "$tmp_dir/publish_dry_run.txt"
grep -q '"version": "2.0.0"' "$tmp_dir/publish_dry_run.txt"
grep -q '"path": "SKILL.md"' "$tmp_dir/publish_dry_run.txt"
grep -q '"path": "benchmark/README.md"' "$tmp_dir/publish_dry_run.txt"
! grep -q '"path": "README.md"' "$tmp_dir/publish_dry_run.txt"
! grep -q '"path": "tests/' "$tmp_dir/publish_dry_run.txt"

echo "WCAG skill smoke tests passed."
