# wcag-skill

[![Version](https://img.shields.io/badge/version-1.0.2-blue)](https://clawhub.ai/turbolego/skills/wcag-skill)
[![License](https://img.shields.io/badge/license-MIT--0-green)](LICENSE)

An agent skill for detecting, fixing, and preventing WCAG 2.2 violations in
web pages. Covers the full accessibility workflow: audit with automated
validators (axe-core, pa11y, QualWeb, W3C), diagnose violations, repair
HTML/CSS, verify, and write accessible markup from the start.

## Contents

| Path | Description |
|------|-------------|
| `SKILL.md` | Main skill: workflow, common violations, pitfalls, benchmark loop |
| `templates/` | Reference-only example of a passing accessible page (107 WHATWG tags, landmarks) — study, don't copy into benchmark runs |
| `scripts/check-tag-coverage.py` | HTML5 tag coverage + tag-balance pre-check |
| `references/ai-wcag-gauntlet-iteration-log.md` | Error strings & fix history from passing runs |

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

```bash
npm i -g pa11y @axe-core/cli @qualweb/cli
npx puppeteer browsers install chrome@stable
npm i -g chromedriver  # match your system Chrome major version
```

## Publishing

Publish to ClawHub with:

```bash
clawhub login
clawhub skill publish .   # initial publish
clawhub sync              # update all changed skills
```

## Related

- [AI-WCAG-Gauntlet](https://github.com/turbolego/AI-WCAG-Gauntlet) — benchmark harness
- [ClawHub — wcag-skill](https://clawhub.ai/turbolego/skills/wcag-skill) — skill registry
