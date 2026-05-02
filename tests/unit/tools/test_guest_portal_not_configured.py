"""Regression: list_vouchers, list_hotspot_packages, and
get_guest_portal_config map controller 404s on their collection /
config endpoints to NotConfiguredError(feature="guest_portal").

The integration API returns 404 for these endpoints when the user
hasn't enabled guest portal / hotspot on the controller. The API
client raises ResourceNotFoundError; the tools re-raise as a typed
NotConfiguredError so callers can branch on it.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.utils.exceptions import NotConfiguredError, ResourceNotFoundError


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.log_level = "INFO"
    settings.api_type = MagicMock()
    settings.api_type.value = "local"
    return settings


def _build_client(*, get_raises=None, get_returns=None):
    client = AsyncMock()
    client.is_authenticated = False
    client.authenticate = AsyncMock()
    client.resolve_site_id = AsyncMock(side_effect=lambda x: x)
    if get_raises is not None:
        client.get = AsyncMock(side_effect=get_raises)
    else:
        client.get = AsyncMock(return_value=get_returns)
    return client


# --- list_vouchers --------------------------------------------------------


@pytest.mark.asyncio
async def test_list_vouchers_404_raises_not_configured(mock_settings):
    from src.tools.vouchers import list_vouchers

    err = ResourceNotFoundError("resource", "/integration/v1/sites/x/vouchers")

    with patch("src.tools.vouchers.UniFiClient") as mock_cls:
        client = _build_client(get_raises=err)
        mock_cls.return_value.__aenter__.return_value = client

        with pytest.raises(NotConfiguredError) as exc_info:
            await list_vouchers("default", mock_settings)

        assert exc_info.value.feature == "guest_portal"
        assert "guest portal" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_list_vouchers_success_still_works(mock_settings):
    from src.tools.vouchers import list_vouchers

    with patch("src.tools.vouchers.UniFiClient") as mock_cls:
        client = _build_client(get_returns={"data": []})
        mock_cls.return_value.__aenter__.return_value = client

        result = await list_vouchers("default", mock_settings)
        assert result == []


# --- list_hotspot_packages ------------------------------------------------


@pytest.mark.asyncio
async def test_list_hotspot_packages_404_raises_not_configured(mock_settings):
    from src.tools.radius import list_hotspot_packages

    err = ResourceNotFoundError("resource", "/integration/v1/sites/x/hotspot/packages")

    with patch("src.tools.radius.UniFiClient") as mock_cls:
        client = _build_client(get_raises=err)
        mock_cls.return_value.__aenter__.return_value = client

        with pytest.raises(NotConfiguredError) as exc_info:
            await list_hotspot_packages("default", mock_settings)

        assert exc_info.value.feature == "guest_portal"


@pytest.mark.asyncio
async def test_list_hotspot_packages_success_still_works(mock_settings):
    from src.tools.radius import list_hotspot_packages

    with patch("src.tools.radius.UniFiClient") as mock_cls:
        client = _build_client(get_returns={"data": []})
        mock_cls.return_value.__aenter__.return_value = client

        result = await list_hotspot_packages("default", mock_settings)
        assert result == []


# --- get_guest_portal_config ----------------------------------------------


@pytest.mark.asyncio
async def test_get_guest_portal_config_404_raises_not_configured(mock_settings):
    from src.tools.radius import get_guest_portal_config

    err = ResourceNotFoundError("resource", "/integration/v1/sites/x/guest-portal/config")

    with patch("src.tools.radius.UniFiClient") as mock_cls:
        client = _build_client(get_raises=err)
        mock_cls.return_value.__aenter__.return_value = client

        with pytest.raises(NotConfiguredError) as exc_info:
            await get_guest_portal_config("default", mock_settings)

        assert exc_info.value.feature == "guest_portal"


@pytest.mark.asyncio
async def test_get_guest_portal_config_success_still_works(mock_settings):
    from src.tools.radius import get_guest_portal_config

    minimal_portal = {
        "site_id": "default",
        "auth_method": "none",
        "expiration_duration": 480,
        "enabled": False,
    }

    with patch("src.tools.radius.UniFiClient") as mock_cls:
        client = _build_client(get_returns={"data": minimal_portal})
        mock_cls.return_value.__aenter__.return_value = client

        result = await get_guest_portal_config("default", mock_settings)
        assert result["enabled"] is False
