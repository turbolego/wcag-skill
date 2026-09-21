#!/bin/bash
# Wrapper for a11y-audit.sh with RAM guardrails
# Sets memory limits for low-RAM environments (e.g., <2GB)

set -e

# Get available memory in MB from /proc/meminfo (MemAvailable)
if [ -r /proc/meminfo ]; then
    AVAILABLE_MEM=$(awk '/^MemAvailable:/ {print int($2/1024)}' /proc/meminfo)
else
    # Fallback to free -m (4th column is available memory)
    AVAILABLE_MEM=$(free -m | awk '/^Mem: / {print $4}')
fi
if [ -z "$AVAILABLE_MEM" ] || [ "$AVAILABLE_MEM" -le 0 ]; then
    echo "ERROR: Could not determine available memory"
    exit 1
fi
# Limit to 50% of available memory (safe margin) for ulimit (virtual memory)
# Ensure at least 512 MB to avoid overly low limits on small systems
LIMIT_MEM=$(( AVAILABLE_MEM * 50 / 100 ))
if [ "$LIMIT_MEM" -lt 512 ]; then
    LIMIT_MEM=512
fi
# Convert to bytes for ulimit (ulimit takes KB)
LIMIT_KB=$(( LIMIT_MEM * 1024 ))

# Set memory limits for the process (affects children)
ulimit -v "$LIMIT_KB" || true

# Node memory limit (10% of available memory, in MB)
NODE_MEM_MB=$(( AVAILABLE_MEM * 10 / 100 ))
# Ensure at least 64 MB for Node
if [ "$NODE_MEM_MB" -lt 64 ]; then
    NODE_MEM_MB=64
fi
NODE_OPTIONS="--max-old-space-size=${NODE_MEM_MB}"
export NODE_OPTIONS

# Run the audit script with the guardrails
export PATH="$(dirname "$0"):$PATH"
cd "$(dirname "$0")/.."
bash scripts/a11y-audit.sh "$@"
