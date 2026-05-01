"""Sweep regression: every tool that builds an /integration/v1/sites/{site_id}/...
URL must call ``client.resolve_site_id(site_id)`` first. The integration API
rejects friendly names like "default" with 400 api.request.argument-type-mismatch
and requires the controller's site UUID.

This module tests one representative function per affected file. The
canonical Switching coverage lives in tests/unit/test_switching.py
(TestSwitchingSiteUuidResolution); this file covers the rest of the sweep.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.log_level = "INFO"
    settings.api_type = MagicMock()
    settings.api_type.value = "local"
    settings.base_url = "https://192.168.2.1"
    return settings


def _build_resolving_client(get_response):
    client = AsyncMock()
    client.is_authenticated = False
    client.authenticate = AsyncMock()
    client.resolve_site_id = AsyncMock(return_value="resolved-uuid-abc")
    client.get = AsyncMock(return_value=get_response)
    client.post = AsyncMock(return_value=get_response)
    client.put = AsyncMock(return_value=get_response)
    client.delete = AsyncMock(return_value=get_response)
    return client


def _assert_resolved_into_url(client, *, verb="get"):
    client.resolve_site_id.assert_awaited_once_with("default")
    method = getattr(client, verb)
    called_url = method.call_args.args[0]
    assert "resolved-uuid-abc" in called_url
    assert "/sites/default/" not in called_url


@pytest.mark.asyncio
async def test_list_wan_connections_resolves_default(mock_settings):
    from src.tools.wans import list_wan_connections

    with patch("src.tools.wans.UniFiClient") as mock_client_class:
        client = _build_resolving_client({"data": []})
        mock_client_class.return_value.__aenter__.return_value = client
        await list_wan_connections("default", mock_settings)
        _assert_resolved_into_url(client)


@pytest.mark.asyncio
async def test_list_vpn_servers_resolves_default(mock_settings):
    from src.tools.vpn import list_vpn_servers

    with patch("src.tools.vpn.UniFiClient") as mock_client_class:
        client = _build_resolving_client({"data": []})
        mock_client_class.return_value.__aenter__.return_value = client
        await list_vpn_servers("default", mock_settings)
        _assert_resolved_into_url(client)


@pytest.mark.asyncio
async def test_list_radius_profiles_resolves_default(mock_settings):
    # The integration-API list_radius_profiles lives in reference_data.py
    # (not radius.py — radius.py's same-named tool uses the /ea/ path).
    from src.tools.reference_data import list_radius_profiles

    with patch("src.tools.reference_data.UniFiClient") as mock_client_class:
        client = _build_resolving_client({"data": []})
        mock_client_class.return_value.__aenter__.return_value = client
        await list_radius_profiles("default", mock_settings)
        _assert_resolved_into_url(client)


@pytest.mark.asyncio
async def test_list_vouchers_resolves_default(mock_settings):
    from src.tools.vouchers import list_vouchers

    with patch("src.tools.vouchers.UniFiClient") as mock_client_class:
        client = _build_resolving_client({"data": []})
        mock_client_class.return_value.__aenter__.return_value = client
        await list_vouchers("default", mock_settings)
        _assert_resolved_into_url(client)


@pytest.mark.asyncio
async def test_list_pending_devices_resolves_default(mock_settings):
    from src.tools.devices import list_pending_devices

    with patch("src.tools.devices.UniFiClient") as mock_client_class:
        client = _build_resolving_client({"data": []})
        mock_client_class.return_value.__aenter__.return_value = client
        await list_pending_devices("default", mock_settings)
        _assert_resolved_into_url(client)


@pytest.mark.asyncio
async def test_get_guest_portal_config_resolves_default(mock_settings):
    from src.tools.radius import get_guest_portal_config

    minimal_portal = {
        "site_id": "resolved-uuid-abc",
        "auth_method": "none",
        "expiration_duration": 480,
        "enabled": False,
    }

    with patch("src.tools.radius.UniFiClient") as mock_client_class:
        client = _build_resolving_client({"data": minimal_portal})
        mock_client_class.return_value.__aenter__.return_value = client
        await get_guest_portal_config("default", mock_settings)
        _assert_resolved_into_url(client)


@pytest.mark.asyncio
async def test_authorize_guest_resolves_default(mock_settings):
    from src.tools.client_management import authorize_guest

    with patch("src.tools.client_management.UniFiClient") as mock_client_class:
        client = _build_resolving_client({"data": {}})
        mock_client_class.return_value.__aenter__.return_value = client
        await authorize_guest(
            "default",
            "00:11:22:33:44:55",
            settings=mock_settings,
            duration=60,
            confirm=True,
        )
        _assert_resolved_into_url(client, verb="post")
