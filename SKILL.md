---
name: wcag-skill
description: "Build, audit, and repair web content against WCAG 2.2. Use when: (1) creating accessible HTML/CSS/JS, (2) remediating accessibility defects, (3) running reproducible automated audits, (4) preparing WCAG 2.2 AAA evidence and human-test records, or (5) running the optional AI-WCAG-Gauntlet benchmark."
metadata:
  version: 2.0.3
  openclaw:
    requires:
      bins:
        - node
        - npm
        - python3
        - curl
        - java
    envVars:
      - name: AXE_CHROME_PATH
        required: false
        description: Explicit Chrome/Chromium binary path for scripts/a11y-audit.sh when auto-detection fails.
      - name: AXE_CHROMEDRIVER_PATH
        required: false
        description: Explicit Chromedriver binary path for scripts/a11y-audit.sh when auto-detection fails.
    install:
      - kind: node
        package: "@axe-core/cli"
        bins: [axe]
      - kind: node
        package: pa11y
        bins: [pa11y]
      - kind: node
        package: "@qualweb/cli"
        bins: [qw]
      - kind: node
        package: vnu-jar
        bins: [vnu]
      - kind: node
        package: chromedriver
        bins: [chromedriver]
    homepage: https://github.com/turbolego/wcag-skill
---

# WCAG 2.2 Accessibility

Use this skill to build or audit web content. Prefer native HTML, test through
HTTP, and treat automated output as evidence—not proof of conformance.

## Choose the scope first

1. Inventory every route, breakpoint, interactive state, overlay, error path,
   media item, authentication step, and third-party component in scope.
2. Set the target: `baseline`, `AA`, or `AAA`.
3. For an AAA target, read **all three** references before implementation:
   - [`references/validator-workflow.md`](references/validator-workflow.md)
   - [`references/aaa-evidence-matrix.md`](references/aaa-evidence-matrix.md)
   - [`references/manual-test-protocol.md`](references/manual-test-protocol.md)

> Do not say “WCAG AAA compliant” from automated results. Level AAA requires
> every applicable A, AA, and AAA success criterion for the full page and any
> complete process. Record an explicit evidence row or non-applicability
> rationale for each criterion.

## Build accessible by default

- Use one `<main>`, a meaningful `<title>`, one clear `<h1>`, and landmarks
  only where their semantics help orientation. Use `<section>` for a meaningful
  thematic grouping; give it an accessible heading when that improves its name.
  Use `<div>` for visual grouping alone.
- Use real `<a>`, `<button>`, `<input>`, `<select>`, `<textarea>`, and native
  disclosure/dialog patterns before inventing ARIA widgets. Never put a
  focusable element inside `aria-hidden="true"` content.
- Give informative images equivalent text; use `alt=""` only for decorative
  images. Provide the relevant captions, transcript, audio description, or
  media alternative for media.
- Label every form control, group related controls with `<fieldset><legend>`,
  use appropriate input types and `autocomplete`, preserve entered data after
  recoverable errors, and identify errors in text as well as colour.
- Keep DOM order aligned with reading and Tab order. Provide a skip link,
  visible focus, keyboard operation, and no keyboard trap.
- Do not communicate status, errors, required fields, or instructions by colour,
  position, shape, or sound alone. Respect `prefers-reduced-motion`.

## Use the right numeric target

| Requirement | Baseline / AA minimum | AAA target |
|---|---:|---:|
| Normal text contrast | 4.5:1 | 7:1 |
| Large text contrast | 3:1 | 4.5:1 |
| UI component / focus contrast | 3:1 | 3:1 plus AAA focus-area rule |
| Pointer target | 24×24 CSS px | 44×44 CSS px unless a documented exception applies |

For AAA, make the keyboard focus indicator at least as large as a two-CSS-pixel
perimeter of the unfocused component and give changed pixels at least 3:1
contrast. Ensure no part of a focused component is obscured by author-created
content.

## Audit → triage → fix → verify

1. Install the tools listed in the frontmatter and make Chrome/Chromium plus a
   matching Chromedriver available. Set `AXE_CHROME_PATH` and
   `AXE_CHROMEDRIVER_PATH` when auto-detection is insufficient.
2. Serve the site over HTTP. Run the reproducible wrapper in
   [`references/validator-workflow.md`](references/validator-workflow.md).
3. Triage structural and markup errors first, then semantic, visual, operable,
   and understandable issues. Deduplicate findings across tools; retain raw
   JSON reports.
4. Fix one coherent group of issues, rerun the audit, and record the result.
   Review every `incomplete`, `cantTell`, warning, and false-positive decision.
5. For AAA, complete the mandatory manual protocol and evidence matrix before
   any conformance statement.

## Report precisely

For each finding, report the route/state, relevant success criterion, affected
selector or component, user impact, exact change, validation method, and retest
result. Say “no automated findings” when that is all the tools establish.

## Optional benchmark extension

The AI-WCAG-Gauntlet tag-coverage experiment is **not** a production
accessibility gate. Use it only when the task explicitly requests benchmark
scoring. Read [`benchmark/README.md`](benchmark/README.md) then; never copy its
reference template into a benchmark submission.
