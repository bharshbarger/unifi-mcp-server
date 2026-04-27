"""Unit tests for Site Manager tools (cloud Site Manager API v1.0.0)."""

from unittest.mock import AsyncMock, patch

import pytest

from src.tools.site_manager import (
    get_host,
    get_isp_metrics,
    get_sdwan_config,
    get_sdwan_config_status,
    get_site_inventory,
    list_all_sites_aggregated,
    list_devices,
    list_hosts,
    list_sdwan_configs,
    query_isp_metrics,
    search_across_sites,
)


@pytest.fixture
def mock_settings():
    """Settings with Site Manager API enabled."""

    class MockSettings:
        log_level = "INFO"
        site_manager_enabled = True
        api_key = "test-key"
        request_timeout = 30.0

        def get_headers(self):
            return {"X-API-KEY": "test-key"}

        def get_site_manager_headers(self):
            return {"X-API-KEY": "test-key"}

    return MockSettings()


@pytest.fixture
def mock_settings_disabled():
    """Settings with Site Manager API disabled."""

    class MockSettings:
        log_level = "INFO"
        site_manager_enabled = False
        api_key = "test-key"
        request_timeout = 30.0

        def get_headers(self):
            return {"X-API-KEY": "test-key"}

        def get_site_manager_headers(self):
            return {"X-API-KEY": "test-key"}

    return MockSettings()


def _patch_client(method_name: str, return_value):
    """Build a context manager that patches SiteManagerClient with one method mocked."""
    patcher = patch("src.tools.site_manager.SiteManagerClient")
    mock_class = patcher.start()
    mock_client = AsyncMock()
    setattr(mock_client, method_name, AsyncMock(return_value=return_value))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()
    mock_class.return_value = mock_client
    return patcher, mock_client


# ---------------------------------------------------------------------------
# list_all_sites_aggregated
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_all_sites_aggregated_success(mock_settings):
    response = {
        "data": [
            {"site_id": "site-1", "name": "Main Office"},
            {"site_id": "site-2", "name": "Branch"},
        ],
        "nextToken": "abc123",
        "httpStatusCode": 200,
        "traceId": "t-1",
    }
    patcher, mock_client = _patch_client("list_sites", response)
    try:
        result = await list_all_sites_aggregated(mock_settings, page_size=50)
        assert result["sites"][0]["site_id"] == "site-1"
        assert result["next_token"] == "abc123"
        mock_client.list_sites.assert_awaited_once_with(page_size=50, next_token=None)
    finally:
        patcher.stop()


@pytest.mark.asyncio
async def test_list_all_sites_aggregated_no_next_token(mock_settings):
    response = {"data": [], "httpStatusCode": 200}
    patcher, _ = _patch_client("list_sites", response)
    try:
        result = await list_all_sites_aggregated(mock_settings)
        assert result == {"sites": [], "next_token": None}
    finally:
        patcher.stop()


@pytest.mark.asyncio
async def test_list_all_sites_aggregated_disabled(mock_settings_disabled):
    with pytest.raises(ValueError, match="Site Manager API is not enabled"):
        await list_all_sites_aggregated(mock_settings_disabled)


# ---------------------------------------------------------------------------
# list_hosts / get_host
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_hosts_paginated(mock_settings):
    response = {
        "data": [{"host_id": "host-1", "hostname": "udm-pro"}],
        "nextToken": "page2",
    }
    patcher, mock_client = _patch_client("list_hosts", response)
    try:
        result = await list_hosts(mock_settings, page_size=10, next_token="cur")
        assert result["hosts"][0]["host_id"] == "host-1"
        assert result["next_token"] == "page2"
        mock_client.list_hosts.assert_awaited_once_with(page_size=10, next_token="cur")
    finally:
        patcher.stop()


@pytest.mark.asyncio
async def test_get_host_unwraps_envelope(mock_settings):
    response = {"data": {"host_id": "h1", "hostname": "ctrl-1"}, "httpStatusCode": 200}
    patcher, mock_client = _patch_client("get_host", response)
    try:
        result = await get_host(mock_settings, "h1")
        assert result["host_id"] == "h1"
        mock_client.get_host.assert_awaited_once_with("h1")
    finally:
        patcher.stop()


# ---------------------------------------------------------------------------
# list_devices
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_devices_with_filters(mock_settings):
    response = {
        "data": [{"id": "d1", "name": "ap-1"}],
        "nextToken": None,
    }
    patcher, mock_client = _patch_client("list_devices", response)
    try:
        result = await list_devices(
            mock_settings,
            host_ids=["h1", "h2"],
            time="2026-04-26T00:00:00Z",
            page_size=25,
        )
        assert result["devices"][0]["id"] == "d1"
        assert result["next_token"] is None
        mock_client.list_devices.assert_awaited_once_with(
            host_ids=["h1", "h2"],
            time="2026-04-26T00:00:00Z",
            page_size=25,
            next_token=None,
        )
    finally:
        patcher.stop()


@pytest.mark.asyncio
async def test_list_devices_disabled(mock_settings_disabled):
    with pytest.raises(ValueError, match="Site Manager API is not enabled"):
        await list_devices(mock_settings_disabled)


# ---------------------------------------------------------------------------
# SD-WAN
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_sdwan_configs(mock_settings):
    response = {
        "data": [
            {
                "config_id": "c1",
                "name": "hub-spoke-1",
                "topology_type": "hub-spoke",
                "hub_site_ids": ["s1"],
                "spoke_site_ids": ["s2"],
                "failover_enabled": True,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-02-01T00:00:00Z",
                "status": "active",
            }
        ]
    }
    patcher, mock_client = _patch_client("list_sdwan_configs", response)
    try:
        result = await list_sdwan_configs(mock_settings)
        assert result[0]["config_id"] == "c1"
        mock_client.list_sdwan_configs.assert_awaited_once_with()
    finally:
        patcher.stop()


@pytest.mark.asyncio
async def test_get_sdwan_config(mock_settings):
    response = {
        "data": {
            "config_id": "c1",
            "name": "hub-spoke-1",
            "topology_type": "hub-spoke",
            "hub_site_ids": [],
            "spoke_site_ids": [],
            "failover_enabled": False,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-02-01T00:00:00Z",
            "status": "pending",
        }
    }
    patcher, mock_client = _patch_client("get_sdwan_config", response)
    try:
        result = await get_sdwan_config(mock_settings, "c1")
        assert result["config_id"] == "c1"
        mock_client.get_sdwan_config.assert_awaited_once_with("c1")
    finally:
        patcher.stop()


@pytest.mark.asyncio
async def test_get_sdwan_config_status(mock_settings):
    response = {
        "data": {
            "config_id": "c1",
            "deployment_status": "deployed",
            "sites_deployed": 2,
            "sites_total": 2,
            "last_deployment_at": "2026-04-25T00:00:00Z",
            "error_message": None,
        }
    }
    patcher, mock_client = _patch_client("get_sdwan_config_status", response)
    try:
        result = await get_sdwan_config_status(mock_settings, "c1")
        assert result["deployment_status"] == "deployed"
        mock_client.get_sdwan_config_status.assert_awaited_once_with("c1")
    finally:
        patcher.stop()


# ---------------------------------------------------------------------------
# ISP metrics
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_isp_metrics_passes_params(mock_settings):
    response = {"data": [{"sample": 1}], "nextToken": "n2"}
    patcher, mock_client = _patch_client("get_isp_metrics", response)
    try:
        result = await get_isp_metrics(
            mock_settings,
            metric_type="5m",
            begin_timestamp="2026-04-01T00:00:00Z",
            end_timestamp="2026-04-02T00:00:00Z",
        )
        assert result["metrics"] == [{"sample": 1}]
        assert result["next_token"] == "n2"
        mock_client.get_isp_metrics.assert_awaited_once_with(
            metric_type="5m",
            begin_timestamp="2026-04-01T00:00:00Z",
            end_timestamp="2026-04-02T00:00:00Z",
            duration=None,
        )
    finally:
        patcher.stop()


@pytest.mark.asyncio
async def test_query_isp_metrics_post_body(mock_settings):
    response = {"data": {"buckets": []}}
    patcher, mock_client = _patch_client("query_isp_metrics", response)
    try:
        body = {"sites": ["s1"], "duration": "24h"}
        result = await query_isp_metrics(mock_settings, metric_type="1h", body=body)
        assert result["metrics"] == {"buckets": []}
        mock_client.query_isp_metrics.assert_awaited_once_with(metric_type="1h", body=body)
    finally:
        patcher.stop()


# ---------------------------------------------------------------------------
# get_site_inventory (no longer hits a per-site endpoint)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_site_inventory_filters_from_list(mock_settings):
    response = {
        "data": [
            {"site_id": "site-1", "name": "Main", "device_count": 10},
            {"site_id": "site-2", "name": "Branch", "device_count": 3},
        ]
    }
    patcher, mock_client = _patch_client("list_sites", response)
    try:
        result = await get_site_inventory(mock_settings, site_id="site-2")
        assert result["site_id"] == "site-2"
        assert result["device_count"] == 3
        mock_client.list_sites.assert_awaited_once_with()
    finally:
        patcher.stop()


@pytest.mark.asyncio
async def test_get_site_inventory_missing_site(mock_settings):
    response = {"data": [{"site_id": "site-1", "name": "Main"}]}
    patcher, _ = _patch_client("list_sites", response)
    try:
        result = await get_site_inventory(mock_settings, site_id="nope")
        assert result["site_id"] == "nope"
        assert "not present" in result["error"]
    finally:
        patcher.stop()


@pytest.mark.asyncio
async def test_get_site_inventory_all_sites(mock_settings):
    response = {
        "data": [
            {"site_id": "s1", "name": "A", "device_count": 4},
            {"site_id": "s2", "name": "B", "device_count": 7},
        ]
    }
    patcher, _ = _patch_client("list_sites", response)
    try:
        result = await get_site_inventory(mock_settings)
        assert isinstance(result, list)
        assert {item["site_id"] for item in result} == {"s1", "s2"}
    finally:
        patcher.stop()


# ---------------------------------------------------------------------------
# search_across_sites — degrades gracefully when nested fields absent
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_search_across_sites_with_nested_devices(mock_settings):
    response = {
        "data": [
            {
                "site_id": "s1",
                "name": "Main",
                "devices": [{"name": "AP-Living", "mac": "aa:bb:cc:dd:ee:01"}],
            }
        ]
    }
    patcher, _ = _patch_client("list_sites", response)
    try:
        result = await search_across_sites(mock_settings, query="living", search_type="device")
        assert result["total_results"] == 1
        assert result["results"][0]["resource"]["mac"] == "aa:bb:cc:dd:ee:01"
    finally:
        patcher.stop()


@pytest.mark.asyncio
async def test_search_across_sites_no_nested_data(mock_settings):
    response = {"data": [{"site_id": "s1", "name": "Main"}]}
    patcher, _ = _patch_client("list_sites", response)
    try:
        result = await search_across_sites(mock_settings, query="anything")
        assert result["total_results"] == 0
    finally:
        patcher.stop()


@pytest.mark.asyncio
async def test_search_across_sites_invalid_type(mock_settings):
    with pytest.raises(ValueError, match="search_type must be one of"):
        await search_across_sites(mock_settings, query="x", search_type="invalid")
