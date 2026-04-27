"""Tests for keychain helpers and Settings keychain integration."""

from unittest.mock import patch

import pytest

from src.config import keychain
from src.config.config import (
    KEYCHAIN_ACCOUNT_API_KEY,
    KEYCHAIN_ACCOUNT_SITE_MANAGER_API_KEY,
    Settings,
)


class _Result:
    """Stand-in for ``subprocess.CompletedProcess``."""

    def __init__(self, returncode: int, stdout: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout


# ---------------------------------------------------------------------------
# keychain.get_secret
# ---------------------------------------------------------------------------
def test_get_secret_returns_none_when_unsupported():
    with patch("src.config.keychain.is_supported", return_value=False):
        assert keychain.get_secret("api_key") is None


def test_get_secret_returns_value_on_success():
    with (
        patch("src.config.keychain.is_supported", return_value=True),
        patch("src.config.keychain.subprocess.run", return_value=_Result(0, "secret-123\n")),
    ):
        assert keychain.get_secret("api_key") == "secret-123"


def test_get_secret_returns_none_when_missing():
    with (
        patch("src.config.keychain.is_supported", return_value=True),
        patch("src.config.keychain.subprocess.run", return_value=_Result(44, "")),
    ):
        assert keychain.get_secret("api_key") is None


def test_get_secret_returns_none_on_oserror():
    with (
        patch("src.config.keychain.is_supported", return_value=True),
        patch("src.config.keychain.subprocess.run", side_effect=OSError("boom")),
    ):
        assert keychain.get_secret("api_key") is None


def test_add_command_includes_account_and_service():
    cmd = keychain.add_command("api_key", service="custom-service")
    assert "custom-service" in cmd
    assert "api_key" in cmd


# ---------------------------------------------------------------------------
# Settings keychain fallback
# ---------------------------------------------------------------------------
def test_settings_uses_env_var_when_present(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("UNIFI_API_KEY", "env-key")
    monkeypatch.setenv("UNIFI_SITE_MANAGER_API_KEY", "env-sm-key")
    with patch("src.config.config.keychain.get_secret") as mock_lookup:
        settings = Settings()
        assert settings.api_key == "env-key"
        assert settings.site_manager_api_key == "env-sm-key"
        # Keychain should not have been consulted when both env vars are set.
        mock_lookup.assert_not_called()


def test_settings_falls_back_to_keychain(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("UNIFI_API_KEY", raising=False)
    monkeypatch.delenv("UNIFI_SITE_MANAGER_API_KEY", raising=False)

    def fake_lookup(account: str, service: str = keychain.DEFAULT_SERVICE) -> str | None:
        if account == KEYCHAIN_ACCOUNT_API_KEY:
            return "keychain-key"
        return None

    with patch("src.config.config.keychain.get_secret", side_effect=fake_lookup):
        settings = Settings()

    assert settings.api_key == "keychain-key"
    assert settings.site_manager_api_key == ""
    assert settings.resolved_site_manager_api_key() == "keychain-key"


def test_settings_loads_separate_site_manager_key_from_keychain(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("UNIFI_API_KEY", raising=False)
    monkeypatch.delenv("UNIFI_SITE_MANAGER_API_KEY", raising=False)

    def fake_lookup(account: str, service: str = keychain.DEFAULT_SERVICE) -> str | None:
        if account == KEYCHAIN_ACCOUNT_API_KEY:
            return "primary-key"
        if account == KEYCHAIN_ACCOUNT_SITE_MANAGER_API_KEY:
            return "site-manager-key"
        return None

    with patch("src.config.config.keychain.get_secret", side_effect=fake_lookup):
        settings = Settings()

    assert settings.api_key == "primary-key"
    assert settings.site_manager_api_key == "site-manager-key"
    assert settings.resolved_site_manager_api_key() == "site-manager-key"
    assert settings.get_site_manager_headers()["X-API-KEY"] == "site-manager-key"
    assert settings.get_headers()["X-API-KEY"] == "primary-key"


def test_settings_raises_when_no_key_anywhere(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("UNIFI_API_KEY", raising=False)
    monkeypatch.delenv("UNIFI_SITE_MANAGER_API_KEY", raising=False)
    with (
        patch("src.config.config.keychain.get_secret", return_value=None),
        pytest.raises(ValueError, match="UniFi API key not configured"),
    ):
        Settings()


# ---------------------------------------------------------------------------
# describe_secret_sources
# ---------------------------------------------------------------------------
def test_describe_secret_sources_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("UNIFI_API_KEY", "env-key")
    monkeypatch.setenv("UNIFI_SITE_MANAGER_API_KEY", "env-sm")
    sources = Settings().describe_secret_sources()
    assert sources == {"api_key": "env", "site_manager_api_key": "env"}


def test_describe_secret_sources_keychain_for_both(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("UNIFI_API_KEY", raising=False)
    monkeypatch.delenv("UNIFI_SITE_MANAGER_API_KEY", raising=False)

    def fake_lookup(account: str, service: str = keychain.DEFAULT_SERVICE) -> str | None:
        return {
            KEYCHAIN_ACCOUNT_API_KEY: "k1",
            KEYCHAIN_ACCOUNT_SITE_MANAGER_API_KEY: "k2",
        }.get(account)

    with patch("src.config.config.keychain.get_secret", side_effect=fake_lookup):
        sources = Settings().describe_secret_sources()

    assert sources == {"api_key": "keychain", "site_manager_api_key": "keychain"}


def test_describe_secret_sources_fallback_when_only_primary_set(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("UNIFI_API_KEY", "env-key")
    monkeypatch.delenv("UNIFI_SITE_MANAGER_API_KEY", raising=False)
    with patch("src.config.config.keychain.get_secret", return_value=None):
        sources = Settings().describe_secret_sources()
    assert sources == {"api_key": "env", "site_manager_api_key": "fallback:api_key"}
