#!/bin/bash
# Wrapper for a11y-audit.sh with RAM guardrails
# Sets memory limits for low-RAM environments (e.g., <2GB)

set -e

# Get available memory in MB from /proc/meminfo (MemAvailable)
if [ -r /proc/meminfo ]; then
    AVAILABLE_MEM=$(awk '/^MemAvailable:/ {print int($2/1024)}' /proc/meminfo)
else
    # Fallback to free -m (6th column is available memory)
    AVAILABLE_MEM=$(free -m | awk '/^Mem: / {print $6}')
fi
if [ -z "$AVAILABLE_MEM" ] || [ "$AVAILABLE_MEM" -le 0 ]; then
    echo "ERROR: Could not determine available memory"
    exit 1
fi

# Configurable limits via environment variables (with sensible defaults)
# ULIMIT_PERCENT: percentage of available memory to use for ulimit -v (virtual memory ceiling)
# ULIMIT_MIN_MB: minimum virtual memory limit in MB
# NODE_PERCENT: percentage of available memory for Node's old space (--max-old-space-size)
# NODE_MIN_MB: minimum Node old space in MB
ULIMIT_PERCENT=${ULIMIT_PERCENT:-90}
ULIMIT_MIN_MB=${ULIMIT_MIN_MB:-1536}
NODE_PERCENT=${NODE_PERCENT:-30}
NODE_MIN_MB=${NODE_MIN_MB:-256}

# Compute ulimit virtual memory limit (in MB)
LIMIT_MEM=$(( AVAILABLE_MEM * ULIMIT_PERCENT / 100 ))
# Cap to available budget; minimum applies only when budget supports it
if [ "$LIMIT_MEM" -gt "$AVAILABLE_MEM" ]; then
    LIMIT_MEM=$AVAILABLE_MEM
fi
if [ "$LIMIT_MEM" -lt "$ULIMIT_MIN_MB" ] && [ "$AVAILABLE_MEM" -ge "$ULIMIT_MIN_MB" ]; then
    LIMIT_MEM=$ULIMIT_MIN_MB
fi
# Convert to bytes for ulimit (ulimit takes KB)
LIMIT_KB=$(( LIMIT_MEM * 1024 ))

# Set memory limits for the process (affects children)
ulimit -v "$LIMIT_KB" || { echo "ERROR: Failed to set virtual memory limit to ${LIMIT_KB} KB" >&2; exit 1; }

# Node memory limit (in MB)
NODE_MEM_MB=$(( AVAILABLE_MEM * NODE_PERCENT / 100 ))
# Cap to available budget; minimum applies only when budget supports it
if [ "$NODE_MEM_MB" -gt "$AVAILABLE_MEM" ]; then
    NODE_MEM_MB=$AVAILABLE_MEM
fi
if [ "$NODE_MEM_MB" -lt "$NODE_MIN_MB" ] && [ "$AVAILABLE_MEM" -ge "$NODE_MIN_MB" ]; then
    NODE_MEM_MB=$NODE_MIN_MB
fi
NODE_OPTIONS="--max-old-space-size=${NODE_MEM_MB}"
export NODE_OPTIONS

# Run the audit script with the guardrails
export PATH="$(dirname "$0"):$PATH"
cd "$(dirname "$0")/.."
bash scripts/a11y-audit.sh "$@"
