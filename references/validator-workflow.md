# Reproducible validator workflow

Use this workflow after the page is reachable over HTTP. It intentionally uses
wrapper scripts because package CLIs differ by version; do not copy obsolete
flags from blog posts or old reports.

## Prerequisites

Install the declared Node tools and a Chromium-family browser plus matching
Chromedriver. `vnu-jar` needs Java.

```bash
npm i -g @axe-core/cli pa11y @qualweb/cli vnu-jar chromedriver
# Install or provide Chrome/Chromium separately.
```

If the browser or driver is not detected, set both paths explicitly:

```bash
export AXE_CHROME_PATH="$(command -v chromium)"
export AXE_CHROMEDRIVER_PATH="$(command -v chromedriver)"
```

## Run all automated checks

From the skill root, serve the target application separately, then run:

```bash
bash scripts/a11y-audit.sh http://localhost:8000 ./a11y-reports
```

The wrapper writes `axe_report.json`, `pa11y_report.json`,
`qualweb_report.json`, and `w3c_report.json`. It resolves QualWeb's actual
installed entry point instead of assuming a `qualweb` executable, uses axe's
supported `--stdout` option, and validates fetched HTML with the Nu checker.

## Read results

Treat every `violations`, `incomplete`, `cantTell`, warning, and markup message
as a review item. A clean automated report means only that the executed rules
found no violations; it does not establish WCAG conformance.

For AAA work, continue with the evidence matrix and manual protocol. For a
production conformance claim, assess the complete set of pages and process
steps, including responsive variations and third-party content in scope.
