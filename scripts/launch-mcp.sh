#!/usr/bin/env bash
# Launch unifi-mcp-server for Claude Code over stdio.
#
# Sets the working directory so .env is picked up, then execs the venv's
# entry point. The API key is read from macOS Keychain at server startup
# (no secrets in JSON config or env vars), per project policy.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [[ ! -x ".venv/bin/unifi-mcp-server" ]]; then
  echo "error: .venv/bin/unifi-mcp-server not found in $PROJECT_DIR" >&2
  echo "       Run \`uv sync\` from $PROJECT_DIR to create the venv." >&2
  exit 1
fi

exec .venv/bin/unifi-mcp-server
