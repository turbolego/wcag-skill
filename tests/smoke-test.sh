#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

python3 -m py_compile benchmark/scripts/check-tag-coverage.py
python3 tests/test-publish-web.py
python3 tests/test-bump-skill-version.py
node --check scripts/run-w3c-validator.mjs
bash scripts/a11y-audit.sh --help >/dev/null

node scripts/run-w3c-validator.mjs tests/fixtures/valid-page.html "$tmp_dir/w3c_source_html_report.json" http://localhost:8000/valid-page.html
grep -q '"scope":"source-html"' "$tmp_dir/w3c_source_html_report.json"
grep -q '"messages":\[\]' "$tmp_dir/w3c_source_html_report.json"

python3 benchmark/scripts/check-tag-coverage.py benchmark/templates/index.html > "$tmp_dir/tag_report.txt"
grep -q 'Missing: 0' "$tmp_dir/tag_report.txt"
grep -q 'Balance: OK' "$tmp_dir/tag_report.txt"
! grep -q 'UNMATCHED\|structural mismatch' "$tmp_dir/tag_report.txt"

# A genuinely mismatched fixture must still be reported as a real error.
printf '<div><section><p>Hello</p></div></section>' > "$tmp_dir/broken.html"
if python3 benchmark/scripts/check-tag-coverage.py "$tmp_dir/broken.html" benchmark/resources/html_tags.json > "$tmp_dir/broken_report.txt"; then
  echo "Expected check-tag-coverage.py to fail on a structurally mismatched fixture" >&2
  exit 1
fi
grep -q 'UNMATCHED\|structural mismatch' "$tmp_dir/broken_report.txt"

# Dry run must work without a token, and must never package generated artifacts.
mkdir -p "$root/scripts/__pycache__"
echo "bogus" > "$root/scripts/__pycache__/decoy.pyc"
trap 'rm -rf "$tmp_dir" "$root/scripts/__pycache__"' EXIT
python3 scripts/publish-web.py --dry-run > "$tmp_dir/publish_dry_run.txt"
# Version is auto-bumped by scripts/bump-skill-version.py before every real
# publish (see publish-web.yml / publish-to-clawhub.yml), so assert on the
# MAJOR.MINOR.PATCH shape rather than a specific pinned value.
grep -Eq '"version": "[0-9]+\.[0-9]+\.[0-9]+"' "$tmp_dir/publish_dry_run.txt"
grep -q '"path": "SKILL.md"' "$tmp_dir/publish_dry_run.txt"
grep -q '"path": "benchmark/README.md"' "$tmp_dir/publish_dry_run.txt"
! grep -q '"path": "README.md"' "$tmp_dir/publish_dry_run.txt"
! grep -q '"path": "skill-card.md"' "$tmp_dir/publish_dry_run.txt"
! grep -q '"path": "tests/' "$tmp_dir/publish_dry_run.txt"
! grep -q '__pycache__\|\.pyc"' "$tmp_dir/publish_dry_run.txt"
! grep -q '"path": "scripts/publish-web.py"' "$tmp_dir/publish_dry_run.txt"
! grep -q '"path": "scripts/bump-skill-version.py"' "$tmp_dir/publish_dry_run.txt"

echo "WCAG skill smoke tests passed."
