"""macOS Keychain helpers for loading secrets via the ``security`` CLI.

We deliberately avoid taking on a third-party dependency (e.g. ``keyring``):
``security`` ships with macOS, and this stays aligned with the global rule of
storing auth material exclusively in the system Keychain.

All functions return ``None`` (rather than raising) when:
  * the platform is not macOS, or
  * the requested item is not present in the user's Keychain, or
  * the ``security`` binary is unavailable.

That way callers can transparently fall back to other config sources without
having to special-case Linux or CI environments.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

DEFAULT_SERVICE = "unifi-mcp-server"


def is_supported() -> bool:
    """Return True when the host can load secrets from macOS Keychain."""
    return sys.platform == "darwin" and shutil.which("security") is not None


def get_secret(account: str, service: str = DEFAULT_SERVICE) -> str | None:
    """Look up a generic password from the user's login Keychain.

    Args:
        account: Account name passed to ``security -a``.
        service: Service name passed to ``security -s``. Defaults to
            :data:`DEFAULT_SERVICE`.

    Returns:
        The stored secret, or ``None`` if the entry is missing or the platform
        does not support Keychain lookups.
    """
    if not is_supported():
        return None

    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
            check=False,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return None

    if result.returncode != 0:
        return None

    secret = result.stdout.rstrip("\n")
    return secret or None


def add_command(account: str, service: str = DEFAULT_SERVICE) -> str:
    """Return the one-liner a user can paste to seed an entry in their Keychain.

    Kept here (rather than in docs) so the canonical command stays next to the
    code that consumes it.
    """
    return (
        f"security add-generic-password -U -s {service} -a {account} "
        '-w "$(read -s -p \'API key: \' k && echo \\"$k\\")"'
    )
