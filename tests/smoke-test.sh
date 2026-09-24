#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

# Add locally installed npm binaries to PATH
export PATH="$PWD/node_modules/.bin:$PATH"

# Prefer the Java 17 we installed locally (if it exists)
if [ -x "/var/lib/hermes/jdk-17.0.13+11-jre/bin/java" ]; then
    export JAVA_HOME="/var/lib/hermes/jdk-17.0.13+11-jre"
    export PATH="${JAVA_HOME}/bin:${PATH}"
fi

# If JAVA_HOME is set by the environment and points to a valid java, use it.
if [ -n "${JAVA_HOME:-}" ] && [ -x "${JAVA_HOME}/bin/java" ]; then
    export PATH="${JAVA_HOME}/bin:${PATH}"
fi

# Debug: show what java we are using
echo "Using java: $(which java)"
java -version 2>&1 | head -3

# Set Java options to avoid shared memory issues in containerized environments.
export _JAVA_OPTIONS="-Xmx256m -Xshare:off -Djava.io.tmpdir=/tmp"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

python3 -m py_compile benchmark/scripts/check-tag-coverage.py
python3 tests/test-publish-web.py
python3 tests/test-bump-skill-version.py
node --check scripts/run-w3c-validator.mjs
bash scripts/a11y-audit.sh --help >/dev/null

node scripts/run-w3c-validator.mjs tests/fixtures/valid-page.html "$tmp_dir/w3c_source_html_report.json" http://localhost:8000/valid-page.html
grep -q '\"scope\":\"source-html\"' "$tmp_dir/w3c_source_html_report.json"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get("messages")==[] else 1)' "$tmp_dir/w3c_source_html_report.json"

# vnu (like Pa11y) exits non-zero when it finds markup errors, not just on a
# technical fault. run-w3c-validator.mjs must always exit 0 once it has
# successfully written a report, even when that report contains errors,
# otherwise scripts/a11y-audit.sh's `set -e` aborts before QualWeb/Nu ever run.
node scripts/run-w3c-validator.mjs tests/fixtures/inaccessible-page.html "$tmp_dir/w3c_bad_report.json" http://localhost:8000/inaccessible-page.html
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if any(m.get("type")=="error" for m in d.get("messages", [])) else 1)' "$tmp_dir/w3c_bad_report.json"

python3 benchmark/scripts/check-tag-coverage.py benchmark/templates/index.html > "$tmp_dir/tag_report.txt"
grep -q 'Missing: 0' "$tmp_dir/tag_report.txt"
grep -q 'Balance: OK' "$tmp_dir/tag_report.txt"
! grep -q 'UNMATCHED\|structural mismatch' "$tmp_dir/tag_report.txt"

# A genuinely mismatched fixture must still be reported as a real error.
printf '<div><section><p>Hello</p></div></section>' > "$tmp_dir/broken.html"
if python3 benchmark/scripts/check-tag-coverage.py "$tmp_dir/broken.html" benchmark/resources/html_tags.json > "$tmp_dir/broken_report.txt" 2>&1; then
  echo "Expected check-tag-coverage.py to fail on a structurally mismatched fixture" >&2
  exit 1
fi
grep -E -q 'UNMATCHED|structural mismatch' "$tmp_dir/broken_report.txt"

# Dry run must work without a token, and must never package generated artifacts.
# Create a temporary __pycache__ directory under scripts/ to verify that
# publish-web.py excludes __pycache__ directories.
tmp_pycache_dir="scripts/tmp_pycache_test_$$"
mkdir -p "$tmp_pycache_dir/__pycache__"
echo "bogus" > "$tmp_pycache_dir/__pycache__/decoy.pyc"
trap 'rm -rf "$tmp_dir" "$tmp_pycache_dir"' EXIT
python3 scripts/publish-web.py --dry-run > "$tmp_dir/publish_dry_run.txt" 2>&1
cat "$tmp_dir/publish_dry_run.txt" | head -5
# Version is auto-bumped by scripts/bump-skill-version.py before every real
# publish (see publish-web.yml / publish-to-clawhub.yml), so assert on the
# MAJOR.MINOR.PATCH shape rather than a specific pinned value.
grep -E -q 'Version: [0-9]+\\.[0-9]+\\.[0-9]+' "$tmp_dir/publish_dry_run.txt"
grep -q '\"path\": \"SKILL.md\"' "$tmp_dir/publish_dry_run.txt"
grep -q '\"path\": \"benchmark/README.md\"' "$tmp_dir/publish_dry_run.txt"
! grep -q '\"path\": \"README.md\"' "$tmp_dir/publish_dry_run.txt"
! grep -q '\"path\": \"skill-card.md\"' "$tmp_dir/publish_dry_run.txt"
! grep -q '\"path\": \"tests/'\" "$tmp_dir/publish_dry_run.txt"
! grep -q '__pycache__\\|\.pyc\"' "$tmp_dir/publish_dry_run.txt"
! grep -q '\"path\": \"scripts/publish-web.py\"' "$tmp_dir/publish_dry_run.txt"
! grep -q '\"path\": \"scripts/bump-skill-version.py\"' "$tmp_dir/publish_dry_run.txt"

echo "WCAG skill smoke tests passed."
