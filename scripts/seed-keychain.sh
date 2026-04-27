#!/usr/bin/env bash
# Seed UniFi MCP Server API keys into the macOS login Keychain.
#
# Stores secrets under service "unifi-mcp-server" with two accounts:
#   - api_key                 (required — primary UniFi key)
#   - site_manager_api_key    (optional — falls back to api_key when absent)
#
# Reads keys interactively without echoing or leaving them in shell history.
# Re-running the script overwrites the existing entry (security -U).
#
# Verify with:
#   security find-generic-password -s unifi-mcp-server -a api_key -w
#
# Remove with:
#   security delete-generic-password -s unifi-mcp-server -a api_key

set -euo pipefail

SERVICE="unifi-mcp-server"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: this script targets macOS Keychain. On Linux/CI, set UNIFI_API_KEY in the environment instead." >&2
  exit 1
fi

if ! command -v security >/dev/null 2>&1; then
  echo "error: 'security' CLI not found on PATH." >&2
  exit 1
fi

read_secret() {
  # $1 = prompt, $2 = varname to assign into
  local prompt="$1" varname="$2" value=""
  printf '%s' "$prompt" >&2
  IFS= read -rs value
  printf '\n' >&2
  printf -v "$varname" '%s' "$value"
}

store_secret() {
  # $1 = account, $2 = secret value
  local account="$1" value="$2"
  security add-generic-password -U -s "$SERVICE" -a "$account" -w "$value"
  echo "  stored: service=$SERVICE account=$account"
}

echo "Seeding UniFi MCP Server keys into the login Keychain (service: $SERVICE)."
echo

read_secret "Primary UniFi API key (required, hidden): " API_KEY
if [[ -z "$API_KEY" ]]; then
  echo "error: primary API key cannot be empty." >&2
  exit 1
fi
store_secret "api_key" "$API_KEY"
unset API_KEY

echo
read -r -p "Add a separate Site Manager API key? [y/N] " ANSWER
case "${ANSWER:-N}" in
  [yY]|[yY][eE][sS])
    read_secret "Site Manager API key (hidden): " SM_KEY
    if [[ -n "$SM_KEY" ]]; then
      store_secret "site_manager_api_key" "$SM_KEY"
    else
      echo "  skipped: empty value provided."
    fi
    unset SM_KEY
    ;;
  *)
    echo "  skipped: server will fall back to api_key for Site Manager calls."
    ;;
esac

echo
echo "Done. The server resolves keys at startup in this order: env var -> Keychain."
