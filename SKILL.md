---
name: wcag-accessibility
description: "Test, fix, and build WCAG-accessible pages (axe, pa11y, W3C, QualWeb)."
---

# WCAG Accessibility — Testing, Fixing, and Building Accessible Pages

Detect, fix, and prevent WCAG violations in web pages (universal design). Covers the full
accessibility workflow: audit with automated validators, diagnose violations, repair
`index.html`/`style.css`, verify, and write accessible markup from the start. Includes the
AI-WCAG-Gauntlet benchmark loop as a structured scoring mode.

## Trigger conditions
- Making an existing page pass axe/pa11y/W3C/QualWeb validation
- Auditing a page or app for accessibility before shipping
- Fixing specific WCAG violations (missing landmarks, target-size, contrast, alt text…)
- Writing or reviewing HTML/CSS with accessibility in mind
- Running the AI-WCAG-Gauntlet benchmark loop (setup.sh → test-suite.sh)

## Tools & installation
Global toolchain (install once):
```bash
npm i -g pa11y @axe-core/cli @qualweb/cli serve   # validators
npx -y puppeteer@24 browsers install chrome@stable  # headless Chrome for Testing
npm i -g chromedriver@<system-chrome-major>         # match your system Chrome version
```
- **axe-core** (`axe <url|file>`) — most thorough rule set; WCAG 2.0/2.1/2.2 + best practices
- **pa11y** (`pa11y <url>`) — quick audit, good for CI smoke tests
- **QualWeb** (`qualweb --act-rules ...`) — ACT rule implementations (W3C standardized)
- **W3C Nu validator** (`npx w3c-html-validator` via `w3c-html-validator` pkg) — markup validity
- Verify: `pa11y --version`, `axe --version`, `chromedriver --version`

## The accessibility workflow

### 1. Audit
Run all four validators against the page (over HTTP when possible — file:// misses
base-href/CSS-loading bugs that only show over a server):
```bash
python3 -m http.server 28763 &   # serve from the PARENT dir of the site root
axe http://localhost:PORT/page.html --format json > axe_report.json
pa11y http://localhost:PORT/page.html --json > pa11y_report.json
node scripts/run-w3c-validator.mjs page.html w3c_report.json   # or npx w3c-html-validator
qualweb --act-rules -o qualweb_report.json http://localhost:PORT/page.html
```

### 2. Triage violations from the reports
Read reports programmatically, not by eyeballing huge JSON:
```bash
python3 -c "
import json
r = json.load(open('axe_report.json'))
for v in r.get('violations', []):
    print(v['id'], '—', v['help'])
    for n in v.get('nodes', []): print('  ', n['target'], n.get('failureSummary','')[:200])
"
```
Prioritize by severity and by how many nodes are affected:
1. **HTML validity errors** (W3C) — these can cascade into many axe/pa11y failures
2. **Landmark/structure** — landmark-one-main, region, frame-title
3. **Perceivable** — color-contrast, image-alt, aria-hidden-focus
4. **Operable** — target-size, link-name, keyboard, tabindex
5. **Robust** — aria-*, duplicate-id, label

### 3. Fix — common violations and their fixes

**Landmarks & structure**
- Every page needs exactly one `<main>`. Wrap page content in `<main>`, header in
  `<header>`, footer in `<footer>`, nav in `<nav aria-label>`. Missing `<main>` triggers
  axe `landmark-one-main` + `region` (content outside any landmark).
- `<section>` needs a heading; use `aria-labelledby` pointing at the heading.
- Landmarks should be keyboard-accessible; avoid `role="main"` on non-main content.

**Images & media**
- Every `<img>` needs `alt`. Decorative: `alt=""` (empty, not missing). Informative:
  describe the content. Complex images (charts): long description via `longdesc` or
  adjacent text. `input type="image"` needs `alt` too.
- `<audio controls>` / `<video controls>`: provide a transcript/captions
  (`<track kind="captions">` for video). Don't autoplay.
- `<canvas>`: provide fallback text content inside the element + `aria-label`.

**Links & buttons**
- Link text must be descriptive without "click here" (`link-name` rule).
- Touch targets ≥ 24×24px (axe `target-size`, WCAG 2.2):
  `a, button { min-height: 24px; display: inline-block; }` plus spacing — neighbors too
  close fail even with size ("safe clickable space has a diameter of 12px instead of 24px").
  Fix with `padding` and `margin` on the targets.
- Don't wrap interactive elements (`button`, `input`, `select`, `textarea`, `iframe`,
  `audio[controls]`, `video[controls]`, `details`, `dialog`, `embed`) in `<a>` — invalid
  HTML and an axe/W3C error.

**Forms**
- Every input/select/textarea needs an associated `<label for>` (or `aria-label`).
- Group related fields in `<fieldset><legend>`; every `<select>` needs a label.
- Use semantic `type`s (email, url, date, search) + `autocomplete` attributes.
- Errors must be announced: `aria-describedby` + `aria-invalid` on the failing control.

**Color & contrast**
- Text contrast ≥ 4.5:1 (large text ≥ 3:1); UI component contrast ≥ 3:1.
- Don't use color alone to convey meaning — pair with icons/text/patterns.
- Test with `axe color-contrast` and re-check with a contrast calculator.

**ARIA (use sparingly)**
- Prefer native HTML semantics over ARIA. First rule: don't use ARIA if a native
  element works (`<button>` not `role="button"` on a div).
- `aria-hidden="true"` must not contain focusable elements.
- Dynamic content: `role="alert"`/`aria-live` regions; manage focus on modals
  (focus trap + return focus on close).

### 4. Verify — rerun every validator
- Iterate: fix → rerun → read the remaining violations → fix again. Never batch a fix
  and skip the rerun; cascading errors hide what's actually broken.
- A page "looks fine" is not a pass — the validators are the source of truth.

### 5. Prevent — accessible-by-default checklist for new pages
- Landmark structure first: `<header>`, `<nav>`, `<main>`, `<footer>`, one `<h1>`.
- Heading levels descend in order (h1 → h2 → h3), never skip for styling.
- All interactive elements are real `<a>`/`<button>`/`<input>`.
- `alt` text on every image; captions/transcripts for media.
- Contrast-check the palette before writing CSS.
- Test keyboard-only navigation (Tab order = DOM order, visible focus ring).
- Zoom test at 200% — layout must not break or clip.
- Screen-reader pass: landmarks, headings, form labels, link names read sensibly.

## AI-WCAG-Gauntlet benchmark loop (structured scoring mode)
1. `bash setup.sh` — creates `benchmarks/<MODEL_NAME>/<MODEL_NAME>-<timestamp>/`.
2. Find the newest run folder: `ls -t benchmarks/<MODEL_NAME>/ | head -1`.
3. `bash test-suite.sh "./benchmarks/<MODEL_NAME>/<folder>"` — runs all validators over HTTP.
4. Read the `STATUS:` line:
   - `PASS` → STOP, do not rerun.
   - `FAIL — Maximum iterations` → STOP, report final results.
   - `FAIL — Fix the errors` → fix index.html/style.css, rerun, repeat (max 20 iterations).
5. Log every iteration (scores, error counts, reasoning) in `benchmark_log.md`.
6. Reports: `test_results.json` (summary), `w3c_report.json`, `axe_report.json`,
   `html5_tags_report.json` + `resources/html_tags.json` (113 expected tags).

## Pitfalls (hard-won)
1. **`<base href>` silently breaks relative CSS/JS URLs.** When a page has
   `<base href="/repo/">`, `href="style.css"` resolves against the base → 404 → CSS never
   applies → target-size/contrast violations persist no matter what you put in the CSS.
   Fix: absolute URL in `<link>`/`<script src>` (URL-encode spaces as %20). Verify with
   `curl -s -o /dev/null -w "%{http_code}" <url>` before rerunning validators.
2. **HTML validity errors cascade.** One unclosed `<section>` or stray `</fieldset>` can
   produce 40+ W3C errors and phantom axe failures. Fix structure first, then semantics.
3. **"Unclosed section" line numbers lie.** "End tag main seen, but there were open
   elements" + "Unclosed element section" points at the FIRST section, not the offender.
   Check nesting with the bundled balance script rather than eyeballing.
4. **Head-only tags in `<body>` cause W3C errors** — `<title>`, `<base>`, `<link>`,
   `<style>`, `<col>`, `<param>`, `<area>` (without `<map>`). Keep them in legitimate
   contexts (col in colgroup, param in object).
5. **axe target-size** needs BOTH size and spacing: `min-height: 24px` AND
   `padding`/`margin` between neighbors. Inline `<style>` in `<head>` works if external
   CSS loading is suspect.
6. **`<selectedcontent>`** (newer HTML element) fails W3C validation inside `<select>`
   but passes in a plain `<div>` — a validator-version quirk, not a real problem.
7. **Optional-end-tag elements** (`option`, `li`, `p`, `dt`, `dd`, `tr`, `td`, `th`) show
   as "unclosed" in strict balance checkers but are valid — treat section/div/main/table
   mismatches as the real errors.
8. **Validators disagree** — a page can pass axe and fail QualWeb (or vice versa). Pass
   means passing ALL of them; triage by union of failures, not by one tool.
9. **Missing `<main>`** → axe `landmark-one-main` + `region`. Always wrap content in
   `<main>` plus header/footer/nav landmarks.
10. **Screenshots lie about accessibility.** Visual "fixes" (larger fonts, colors) without
    semantic markup don't move validator scores. Fix the DOM, not the pixels.

## Verification
- Fast pre-check (tag coverage + balance) before the full audit:
  `python3 scripts/check-tag-coverage.py <index.html> [html_tags.json]`
  (exit 1 if required tags are missing).
- Then run the full validator set and read the reports. Only a full pass of every
  validator counts as done.

## Support files
- `scripts/check-tag-coverage.py` — HTML5 tag coverage + tag-balance checker.
- `references/ai-wcag-gauntlet-iteration-log.md` — exact error strings and fix history
  from a passing 6-iteration benchmark run (deepseek-v4-pro via nvidia, label "Hermes").

## User preferences
- Editing config variable sections (setup.sh etc.): comment out the old value, add a new
  active line — never delete history.
- Benchmark loops run autonomously: no confirmation check-ins; iterate until PASS or max
  iterations; log changes in benchmark_log.md as you go.
