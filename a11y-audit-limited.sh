#!/bin/bash
# Wrapper for a11y-audit.sh with RAM guardrails
# Sets memory limits for low-RAM environments (e.g., <2GB)

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
export NODE_OPTIONS

# Run the audit script with the guardrails
export PATH="$(dirname "$0"):$PATH"
cd "$(dirname "$0")/.."
bash scripts/a11y-audit.sh "$@"
