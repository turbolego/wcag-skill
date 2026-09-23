# wcag-skill

[![Version](https://img.shields.io/badge/version-2.0.9-blue)](https://clawhub.ai/turbolego/skills/wcag-skill)
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
| `references/aaa-evidence-matrix.md` | WCAG 2.2 AAA evidence template and applicability prompts |
| `references/manual-test-protocol.md` | Required keyboard, reflow, focus, state, media, and assistive-technology checks |
| `benchmark/` | Optional AI-WCAG-Gauntlet extension; not a production conformance gate |
| `tests/` | Fixture and CI smoke test for documented bundled commands |

`scripts/publish-web.py` is repository release tooling for maintainers only. It
reads `CLAWHUB_TOKEN` and is excluded from the published skill bundle via
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

The audit wrapper looks for CLIs installed locally (`./node_modules/.bin`) or
globally. Prefix commands with `npx` or add `./node_modules/.bin` to `PATH`
if you installed locally.

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

Publish to ClawHub with:

```bash
clawhub login
clawhub skill publish .   # initial publish
clawhub sync              # update all changed skills
```

## Related

- [AI-WCAG-Gauntlet leaderboards](https://turbolego.github.io/AI-WCAG-Gauntlet/) - benchmarks used to make this skill
- [AI-WCAG-Gauntlet](https://github.com/turbolego/AI-WCAG-Gauntlet) — benchmark harness
- [ClawHub — wcag-skill](https://clawhub.ai/turbolego/skills/wcag-skill) — skill registry
