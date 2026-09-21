#!/bin/bash
# Wrapper for a11y-audit.sh with RAM guardrails
# Sets memory limits and points to the installed Chrome/Chromedriver

set -e

# Get available memory in MB
AVAILABLE_MEM=$(free -m | awk '/^Mem: / {print $3}')
if [ -z "$AVAILABLE_MEM" ]; then
    echo "ERROR: Could not determine available memory"
    exit 1
fi
# Limit to 20% of available memory (safe margin) for ulimit (virtual memory)
LIMIT_MEM=$(( AVAILABLE_MEM * 20 / 100 ))
# Convert to bytes for ulimit (ulimit takes KB)
LIMIT_KB=$(( LIMIT_MEM * 1024 ))

# Set memory limits for the process (affects children)
ulimit -v "$LIMIT_KB" || true

# Node memory limit (10% of available, rounded)
NODE_MEM_KB=$(( AVAILABLE_MEM * 10 / 100 ))
NODE_OPTIONS="--max-old-space-size=${NODE_MEM_KB}"

# Point to the installed Chrome headless shell and Chromedriver
export AXE_CHROME_PATH="/var/lib/hermes/.cache/puppeteer/chrome-headless-shell/linux-148.0.7778.97/chrome-linux64/chrome"
export AXE_CHROMEDRIVER_PATH="/var/lib/hermes/.hermes/skills/wcag-skill/node_modules/chromedriver/lib/chromedriver/chromedriver"
# Set Chrome extra args to reduce memory usage
export AXE_CHROME_EXTRA_ARGS="--no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage --disable-gpu --disable-software-rasterizer --memory-pressure-off --max_old_space_size=128 --disable-features=VizDisplayCompositor"

# Run the audit script with the guardrails
export PATH="$PATH:/var/lib/hermes/.hermes/skills/wcag-skill/scripts"
cd /var/lib/hermes/.hermes/skills/wcag-skill
bash scripts/a11y-audit.sh "http://localhost:8000" 2>&1 | tee audit.log