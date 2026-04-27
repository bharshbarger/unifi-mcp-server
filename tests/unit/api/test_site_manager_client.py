"""Unit tests for the cloud Site Manager API client.

Verifies that requests hit the documented paths/methods (per the OpenAPI spec
at https://developer.ui.com/site-manager/v1.0.0/) and that HTTP error
responses are mapped to the right exception types.
"""

import json

import httpx
import pytest

from src.api.site_manager_client import MAX_PAGE_SIZE, SiteManagerClient
from src.utils import APIError, AuthenticationError, RateLimitError, ResourceNotFoundError


class _Settings:
    log_level = "INFO"
    site_manager_enabled = True
    api_key = "test-key"
    request_timeout = 30.0

    def get_headers(self) -> dict[str, str]:
        return {"X-API-KEY": self.api_key}

    def get_site_manager_headers(self) -> dict[str, str]:
        return {"X-API-KEY": self.api_key}


def _install_transport(client: SiteManagerClient, handler) -> list[httpx.Request]:
    """Replace the client's transport with a recording mock."""
    captured: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return handler(request)

    client.client._transport = httpx.MockTransport(record)
    return captured


def _ok(payload: dict) -> httpx.Response:
    return httpx.Response(
        200, content=json.dumps(payload), headers={"content-type": "application/json"}
    )


def _err(status: int, body: dict | None = None, headers: dict | None = None) -> httpx.Response:
    return httpx.Response(
        status,
        content=json.dumps(body or {}),
        headers={"content-type": "application/json", **(headers or {})},
    )


@pytest.fixture
async def client():
    sm = SiteManagerClient(_Settings())
    try:
        yield sm
    finally:
        await sm.close()


# ---------------------------------------------------------------------------
# Path / method assertions
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_sites_paginated_path(client):
    captured = _install_transport(client, lambda req: _ok({"data": [], "nextToken": "tok"}))
    await client.list_sites(page_size=100, next_token="cur")
    req = captured[0]
    assert req.method == "GET"
    assert req.url.path == "/v1/sites"
    assert req.url.params["pageSize"] == "100"
    assert req.url.params["nextToken"] == "cur"


@pytest.mark.asyncio
async def test_list_sites_omits_pagination_when_unset(client):
    captured = _install_transport(client, lambda req: _ok({"data": []}))
    await client.list_sites()
    req = captured[0]
    assert req.url.params.get("pageSize") is None
    assert req.url.params.get("nextToken") is None


@pytest.mark.asyncio
async def test_list_sites_rejects_invalid_page_size(client):
    with pytest.raises(ValueError, match="page_size must be between"):
        await client.list_sites(page_size=MAX_PAGE_SIZE + 1)


@pytest.mark.asyncio
async def test_list_hosts_path(client):
    captured = _install_transport(client, lambda req: _ok({"data": []}))
    await client.list_hosts(page_size=10)
    assert captured[0].url.path == "/v1/hosts"
    assert captured[0].url.params["pageSize"] == "10"


@pytest.mark.asyncio
async def test_get_host_path(client):
    captured = _install_transport(client, lambda req: _ok({"data": {}}))
    await client.get_host("h-123")
    assert captured[0].url.path == "/v1/hosts/h-123"


@pytest.mark.asyncio
async def test_list_devices_path_and_filters(client):
    captured = _install_transport(client, lambda req: _ok({"data": []}))
    await client.list_devices(host_ids=["h1", "h2"], time="2026-04-26T00:00:00Z", page_size=50)
    req = captured[0]
    assert req.url.path == "/v1/devices"
    assert req.url.params["pageSize"] == "50"
    assert req.url.params["time"] == "2026-04-26T00:00:00Z"
    # httpx encodes list params as repeated keys
    assert req.url.params.get_list("hostIds[]") == ["h1", "h2"]


@pytest.mark.asyncio
async def test_sdwan_paths_use_hyphens(client):
    captured = _install_transport(client, lambda req: _ok({"data": {}}))
    await client.list_sdwan_configs()
    await client.get_sdwan_config("c-1")
    await client.get_sdwan_config_status("c-1")
    paths = [r.url.path for r in captured]
    assert paths == [
        "/v1/sd-wan-configs",
        "/v1/sd-wan-configs/c-1",
        "/v1/sd-wan-configs/c-1/status",
    ]


@pytest.mark.asyncio
async def test_get_isp_metrics_path_and_validation(client):
    captured = _install_transport(client, lambda req: _ok({"data": []}))
    await client.get_isp_metrics(metric_type="5m", duration="1h")
    req = captured[0]
    assert req.method == "GET"
    assert req.url.path == "/v1/isp-metrics/5m"
    assert req.url.params["duration"] == "1h"

    with pytest.raises(ValueError, match="metric_type must be one of"):
        await client.get_isp_metrics(metric_type="10m")


@pytest.mark.asyncio
async def test_query_isp_metrics_posts_body(client):
    captured = _install_transport(client, lambda req: _ok({"data": []}))
    body = {"sites": ["s1"], "duration": "24h"}
    await client.query_isp_metrics(metric_type="1h", body=body)
    req = captured[0]
    assert req.method == "POST"
    assert req.url.path == "/v1/isp-metrics/1h/query"
    assert json.loads(req.content) == body


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_400_maps_to_api_error(client):
    _install_transport(client, lambda req: _err(400, {"code": "BAD_REQUEST", "message": "bad"}))
    with pytest.raises(APIError) as excinfo:
        await client.list_sites()
    assert excinfo.value.status_code == 400


@pytest.mark.asyncio
async def test_401_maps_to_authentication_error(client):
    _install_transport(client, lambda req: _err(401, {"code": "UNAUTHORIZED", "message": "no"}))
    with pytest.raises(AuthenticationError):
        await client.list_sites()


@pytest.mark.asyncio
async def test_403_maps_to_api_error(client):
    _install_transport(client, lambda req: _err(403, {"code": "FORBIDDEN", "message": "denied"}))
    with pytest.raises(APIError) as excinfo:
        await client.list_sites()
    assert excinfo.value.status_code == 403


@pytest.mark.asyncio
async def test_404_maps_to_resource_not_found(client):
    _install_transport(client, lambda req: _err(404, {"code": "NOT_FOUND", "message": "missing"}))
    with pytest.raises(ResourceNotFoundError):
        await client.get_host("missing")


@pytest.mark.asyncio
async def test_429_maps_to_rate_limit_with_retry_after(client):
    _install_transport(
        client,
        lambda req: _err(
            429,
            {"code": "RATE_LIMIT", "message": "slow down"},
            headers={"Retry-After": "12"},
        ),
    )
    with pytest.raises(RateLimitError) as excinfo:
        await client.list_sites()
    assert excinfo.value.retry_after == 12


@pytest.mark.asyncio
async def test_500_maps_to_api_error(client):
    _install_transport(client, lambda req: _err(500, {"code": "SERVER_ERROR", "message": "boom"}))
    with pytest.raises(APIError) as excinfo:
        await client.list_sites()
    assert excinfo.value.status_code == 500


@pytest.mark.asyncio
async def test_502_maps_to_api_error(client):
    _install_transport(client, lambda req: _err(502, {"code": "BAD_GATEWAY", "message": "gw"}))
    with pytest.raises(APIError) as excinfo:
        await client.list_sites()
    assert excinfo.value.status_code == 502
