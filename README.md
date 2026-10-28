# wcag-skill

## install from Clawhub.ai: https://clawhub.ai/turbolego/skills/wcag-skill

[![Version](https://img.shields.io/badge/version-2.0.22-blue)](https://clawhub.ai/turbolego/skills/wcag-skill)
[![License](https://img.shields.io/badge/license-MIT--0-green)](LICENSE)

An agent skill for building, auditing, and repairing WCAG 2.2 web content.
It provides a reproducible automated audit wrapper, an explicit WCAG 2.2 AAA
evidence matrix, and a mandatory human-test protocol. Automated results are
evidence, not proof of conformance.

## Contents

| Path | Description |
|------|-------------|
| `SKILL.md` | Production workflow and accessible-by-default rules |
| `skill-card.md` | Release record covering purpose, dependencies, risks, outputs, evidence, and ethical considerations |
| `scripts/a11y-audit.sh` | Tested wrapper for axe, Pa11y, QualWeb, and Nu reports |
| `scripts/check-wcag-412.py` | Static source-markup inventory of likely interactive and stateful WCAG 4.1.2 components |
| `references/aaa-evidence-matrix.md` | WCAG 2.2 AAA evidence template and applicability prompts |
| `references/manual-test-protocol.md` | Required keyboard, reflow, focus, state, media, and assistive-technology checks |
| `references/dynamic-state-test-protocol.md` | WCAG 4.1.2 inventory, interaction evidence, and assistive-technology review |
| `templates/playwright-state.spec.ts` | Playwright example for testing programmatic and application state together |
| `docs/index.html` | GitHub Pages site with interactive before-and-after WCAG 2.2 demos |
| `docs/wcag-skill-demo.html` | Side-by-side AI-generated page comparison with and without the WCAG skill, including axe-core tests |
| `benchmark/` | Optional AI-WCAG-Gauntlet extension; not a production conformance gate |
| `tests/` | Fixture and CI smoke test for documented bundled commands |

`scripts/publish-web.py` is repository release tooling for maintainers only. It
reads `CLAWHUB_TOKEN`    and is excluded from the published skill bundle via
`.clawhubignore`, so an installed copy of this skill never contains it.

## Install

```bash
# From ClawHub
openclaw skills install turbolego/wcag-skill

# From GitHub
openclaw skills install git:turbolego/wcag-skill@main

# Local
openclaw skills install ./path/to/wcag-skill --as wcag-skill
```

## Who this is for

- **Developers** who want their AI agent to produce accessible code from the start
- **Accessibility auditors** running WCAG validation loops
- **Benchmark maintainers** scoring AI models on HTML accessibility compliance

## Prerequisites

Tool versions are pinned in [`package.json`](package.json) and
[`package-lock.json`](package-lock.json) for reproducible installs:

```bash
npm ci
# Install Chrome or Chromium separately, matching the chromedriver
# major version pinned in package.json.
```

Until `extract-zip` releases a fix for its
[symlink path traversal vulnerability](https://github.com/advisories/GHSA-jmr9-qjv8-65gv),
`package.json` overrides Puppeteer's browser-management dependency to
`@puppeteer/browsers` 3.2.6, removing `extract-zip` from the lockfile.

The transitive `deepmerge` dependency is overridden to 4.1.2 to avoid
[GHSA-gcqx-w48m-w2h4](https://github.com/advisories/GHSA-gcqx-w48m-w2h4),
which affects versions 4.2.0 through 4.3.1. This is a downgrade mitigation,
not an upstream patched release. Renovate excludes the affected range;
review compatibility and the advisory before upgrading the override.

The audit wrapper looks for CLIs installed locally (`./node_modules/.bin`) or
globally. Prefix commands with `npx` or add `./node_modules/.bin` to `PATH`
if you installed locally.

The standard-library WCAG 4.1.2 source inventory can be tested independently:

```bash
python3 tests/test-wcag-412-checker.py
```

Open [`tests/fixtures/wcag-412-stateful-page.html`](tests/fixtures/wcag-412-stateful-page.html)
in a browser to try the dark-theme toggle with missing state and the corrected
`aria-pressed` version side by side.

## GitHub Pages demos

The interactive demo site lives in [`docs/index.html`](docs/index.html), with
the [AI side-by-side comparison](docs/wcag-skill-demo.html) alongside it. To
preview both locally, run:

```bash
python3 -m http.server 8000 --directory docs
```

Then open `http://localhost:8000`. To publish it from GitHub Pages, select
**Settings → Pages → Deploy from a branch**, choose the `main` branch and
`/docs` as the folder. That publishes both pages and any other site assets in
`docs/`; no separate Pages workflow is required. The site includes
intentionally flawed examples; they are labelled and paired with improved
implementations. The docs folder is excluded from the installable skill
package.

## Audit a page

Serve the target page over HTTP, then run the packaged wrapper:

```bash
bash scripts/a11y-audit.sh http://localhost:8000 ./a11y-reports
```

For WCAG 2.2 AAA work, complete the matrix and manual-test protocol referenced
from `SKILL.md` before making any conformance statement.

## Optional benchmark

The AI-WCAG-Gauntlet experiment is intentionally separated from production
accessibility guidance. Read [`benchmark/README.md`](benchmark/README.md) only
when benchmark scoring is explicitly requested.

## Publishing

`SKILL.md`'s `metadata.version` is the release source of truth. Its mirrors in
this README, `skill-card.md`, `package.json`, and both root version fields in
`package-lock.json` must agree. Dependency versions and historical test fixtures
are independent of the skill release.

```bash
python3 scripts/read-version.py --check  # CI and upload consistency gate
# After intentionally editing metadata.version in SKILL.md:
python3 scripts/read-version.py --sync
# Or select a patch newer than both the repository and all registry versions:
python3 scripts/bump-skill-version.py --write
python3 scripts/publish-web.py --dry-run
```

Release-related pushes to `main` automatically create and commit a synchronized
patch version newer than all recorded ClawHub versions, then upload that exact
checkout through the multipart API using the `CLAWHUB_TOKEN` Actions secret.
Changes to the dependency manifests, templates, and publishing workflows also
trigger releases. The workflow token needs permission to write repository
contents; branch rules must allow the release commit.

Both **Publish to ClawHub** workflows use the same publisher and concurrency
group. A manual run creates a new release by default; disable `bump_version`
to retry the currently declared version. Re-running a failed workflow also
reuses the declared version. `dry_run` never commits or uploads.

An accepted upload is not proof of publication. The workflow uses the owner's
authenticated publication-status endpoint (pending versions are hidden from
public version reads), waits for pre-publication checks, updates `latest`, and
verifies both ClawHub's public live version and its `latest` tag. Failed checks,
blocked publication, timeouts, and version mismatches fail the job rather than
reporting success. Retry the retained version without bumping; for stalled or
failed checks, contact ClawHub support with the exact version and reported
check statuses.

`scripts/clawhub-force-sync.py --rescan` optionally requests a scan with
write-back for an **already published** version. A separate on-demand scan
cannot replace pre-publication checks or unstick ClawHub's publish workers.

## Related

- [AI-WCAG-Gauntlet leaderboards](https://turbolego.github.io/AI-WCAG-Gauntlet/) - benchmarks used to make this skill
- [AI-WCAG-Gauntlet](https://github.com/turbolego/AI-WCAG-Gauntlet) — benchmark harness
- [ClawHub — wcag-skill](https://clawhub.ai/turbolego/skills/wcag-skill) — skill registry
