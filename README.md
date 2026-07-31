# wcag-skill

Skill for AI Agents like Hermes, OpenClaw etc. for detecting and fixing WCAG violations (universal design).

## Contents
- `SKILL.md` — the main skill: audit → triage → fix → verify → prevent workflow for
  accessibility (WCAG 2.2), plus the AI-WCAG-Gauntlet benchmark loop as a scoring mode.
- `scripts/check-tag-coverage.py` — HTML5 tag coverage + tag-balance pre-check.
- `references/ai-wcag-gauntlet-iteration-log.md` — exact validator error strings and
  fix history from a passing benchmark run.

## Usage
Load the skill in your agent (e.g. `skill_view(name='wcag-accessibility')` for Hermes)
and follow the workflow. The skill works for any page: audit with axe, pa11y, QualWeb and
the W3C Nu validator, fix violations, and verify until all validators pass.
