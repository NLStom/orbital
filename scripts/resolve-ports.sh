#!/bin/bash

# resolve-ports.sh - Generic multi-worktree port resolution
# Works with any git worktree setup (Conductor, manual, etc.)
#
# Usage: source this script to get environment variables:
#   ORBITAL_API_PORT    - Port for the API server (default: 8787)
#   ORBITAL_WEB_PORT    - Port for the web server (default: 3737)
#   ORBITAL_INSTANCE_SUFFIX - Suffix for PM2 process names (e.g., "-yangon")

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Detect if we're in a linked git worktree
GIT_DIR=$(git -C "$REPO_ROOT" rev-parse --git-dir 2>/dev/null)

if [[ "$GIT_DIR" == *".git/worktrees/"* ]]; then
    # Linked worktree - extract name from git internal path
    # GIT_DIR looks like: /path/to/main/.git/worktrees/<worktree-name>
    WORKSPACE_NAME=$(basename "$GIT_DIR")

    # Hash workspace name for port offset (0-99)
    hash_sum=0
    for (( i=0; i<${#WORKSPACE_NAME}; i++ )); do
        char="${WORKSPACE_NAME:$i:1}"
        ascii=$(printf '%d' "'$char")
        hash_sum=$((hash_sum + ascii))
    done
    port_offset=$((hash_sum % 100))

    export ORBITAL_API_PORT=$((8700 + port_offset))
    export ORBITAL_WEB_PORT=$((3700 + port_offset))
    export ORBITAL_INSTANCE_SUFFIX="-${WORKSPACE_NAME}"
else
    # Main worktree - default ports
    export ORBITAL_API_PORT=8787
    export ORBITAL_WEB_PORT=3737
    export ORBITAL_INSTANCE_SUFFIX=""
fi

# Allow environment variable overrides
ORBITAL_API_PORT="${ORBITAL_API_PORT_OVERRIDE:-$ORBITAL_API_PORT}"
ORBITAL_WEB_PORT="${ORBITAL_WEB_PORT_OVERRIDE:-$ORBITAL_WEB_PORT}"

# If called directly (not sourced), print the configuration
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "ORBITAL_API_PORT=$ORBITAL_API_PORT"
    echo "ORBITAL_WEB_PORT=$ORBITAL_WEB_PORT"
    echo "ORBITAL_INSTANCE_SUFFIX=$ORBITAL_INSTANCE_SUFFIX"
fi
