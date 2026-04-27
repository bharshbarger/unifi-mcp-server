"""Site Manager API tools.

Wraps the cloud UniFi Site Manager API v1.0.0 (https://api.ui.com/v1). Only
endpoints documented in the official OpenAPI spec are exposed.
"""

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar

from ..api.site_manager_client import SiteManagerClient
from ..config import Settings
from ..models.site_manager import (
    CrossSiteSearchResult,
    SDWANConfig,
    SDWANConfigStatus,
    SiteInventory,
)
from ..utils import get_logger, sanitize_log_message

logger = get_logger(__name__)

_R = TypeVar("_R")


def require_site_manager(
    func: Callable[..., Awaitable[_R]],
) -> Callable[..., Awaitable[_R]]:
    """Ensure the Site Manager API is enabled before executing the wrapped tool."""

    @wraps(func)
    async def wrapper(settings: Settings, *args: Any, **kwargs: Any) -> _R:
        if not settings.site_manager_enabled:
            raise ValueError("Site Manager API is not enabled. Set UNIFI_SITE_MANAGER_ENABLED=true")
        return await func(settings, *args, **kwargs)

    return wrapper


def _envelope_data(response: Any) -> Any:
    """Unwrap a Site Manager response envelope to its ``data`` payload."""
    if isinstance(response, dict) and "data" in response:
        return response["data"]
    return response


def _envelope_next_token(response: Any) -> str | None:
    if isinstance(response, dict):
        token = response.get("nextToken")
        if isinstance(token, str) and token:
            return token
    return None


# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------
@require_site_manager
async def list_all_sites_aggregated(
    settings: Settings,
    page_size: int | None = None,
    next_token: str | None = None,
) -> dict[str, Any]:
    """List all sites visible to the Site Manager API key.

    Returns the raw envelope: ``{"sites": [...], "next_token": "..."}``. When
    ``next_token`` is non-null, pass it back to fetch the next page (max 500
    items per page per the spec).
    """
    async with SiteManagerClient(settings) as client:
        logger.info(
            sanitize_log_message(
                f"Listing sites (page_size={page_size}, next_token={next_token!r})"
            )
        )
        response = await client.list_sites(page_size=page_size, next_token=next_token)
        data = _envelope_data(response)
        sites = data if isinstance(data, list) else []
        return {"sites": sites, "next_token": _envelope_next_token(response)}


@require_site_manager
async def get_site_inventory(
    settings: Settings, site_id: str | None = None
) -> dict[str, Any] | list[dict[str, Any]]:
    """Build site inventory by aggregating ``/v1/sites``.

    The cloud Site Manager API does not expose a per-site detail endpoint, so
    this tool projects whatever fields ``/v1/sites`` returns into the
    ``SiteInventory`` shape. When ``site_id`` is provided, the matching site is
    filtered from the list.
    """
    async with SiteManagerClient(settings) as client:
        logger.info(sanitize_log_message(f"Building site inventory (site_id={site_id})"))

        sites_response = await client.list_sites()
        sites_data = _envelope_data(sites_response)
        sites_data = sites_data if isinstance(sites_data, list) else []

        def to_inventory(site: dict[str, Any]) -> dict[str, Any]:
            sid = site.get("site_id") or site.get("id") or site.get("siteId") or ""
            return SiteInventory(
                site_id=str(sid),
                site_name=site.get("name", str(sid)),
                device_count=site.get("device_count", 0),
                device_types=site.get("device_types", {}),
                client_count=site.get("client_count", 0),
                network_count=site.get("network_count", 0),
                ssid_count=site.get("ssid_count", 0),
                uplink_count=site.get("uplink_count", 0),
                vpn_tunnel_count=site.get("vpn_tunnel_count", 0),
                firewall_rule_count=site.get("firewall_rule_count", 0),
                last_updated=site.get("last_updated", ""),
            ).model_dump()

        if site_id:
            for site in sites_data:
                if site_id in {
                    site.get("site_id"),
                    site.get("id"),
                    site.get("siteId"),
                    site.get("name"),
                }:
                    return to_inventory(site)
            return {
                "site_id": site_id,
                "error": f"site '{site_id}' not present in /v1/sites response",
            }

        return [to_inventory(site) for site in sites_data]


@require_site_manager
async def search_across_sites(
    settings: Settings,
    query: str,
    search_type: str = "all",
) -> dict[str, Any]:
    """Best-effort search across whatever fields ``/v1/sites`` returns.

    The cloud spec only guarantees a sites listing — nested device/client/
    network arrays may or may not appear depending on UniFi OS version. This
    tool degrades gracefully to empty results when those arrays are absent.
    """
    valid_types = ["device", "client", "network", "all"]
    if search_type not in valid_types:
        raise ValueError(f"search_type must be one of {valid_types}, got '{search_type}'")

    async with SiteManagerClient(settings) as client:
        logger.info(
            sanitize_log_message(f"Searching across sites: query='{query}', type={search_type}")
        )

        sites_response = await client.list_sites()
        sites_data = _envelope_data(sites_response)
        sites_data = sites_data if isinstance(sites_data, list) else []

        results: list[dict[str, Any]] = []
        query_lower = query.lower()

        for site in sites_data:
            site_id = site.get("site_id") or site.get("id") or ""
            site_name = site.get("name", site_id)

            if search_type in ("device", "all"):
                for device in site.get("devices", []) or []:
                    name = device.get("name", "").lower()
                    mac = device.get("mac", "").lower()
                    if query_lower in name or query_lower in mac:
                        results.append(
                            {
                                "type": "device",
                                "site_id": site_id,
                                "site_name": site_name,
                                "resource": device,
                            }
                        )

            if search_type in ("client", "all"):
                for client_obj in site.get("clients", []) or []:
                    name = client_obj.get("name", "").lower()
                    mac = client_obj.get("mac", "").lower()
                    ip = client_obj.get("ip", "").lower()
                    if query_lower in name or query_lower in mac or query_lower in ip:
                        results.append(
                            {
                                "type": "client",
                                "site_id": site_id,
                                "site_name": site_name,
                                "resource": client_obj,
                            }
                        )

            if search_type in ("network", "all"):
                for network in site.get("networks", []) or []:
                    name = network.get("name", "").lower()
                    if query_lower in name:
                        results.append(
                            {
                                "type": "network",
                                "site_id": site_id,
                                "site_name": site_name,
                                "resource": network,
                            }
                        )

        return CrossSiteSearchResult(
            total_results=len(results),
            search_query=query,
            result_type=search_type,  # type: ignore[arg-type]
            results=results,
        ).model_dump()


# ---------------------------------------------------------------------------
# Hosts
# ---------------------------------------------------------------------------
@require_site_manager
async def list_hosts(
    settings: Settings,
    page_size: int | None = None,
    next_token: str | None = None,
) -> dict[str, Any]:
    """List managed hosts/consoles. Returns ``{"hosts": [...], "next_token": ...}``."""
    async with SiteManagerClient(settings) as client:
        logger.info(
            sanitize_log_message(
                f"Listing hosts (page_size={page_size}, next_token={next_token!r})"
            )
        )
        response = await client.list_hosts(page_size=page_size, next_token=next_token)
        data = _envelope_data(response)
        hosts = data if isinstance(data, list) else []
        return {"hosts": hosts, "next_token": _envelope_next_token(response)}


@require_site_manager
async def get_host(settings: Settings, host_id: str) -> dict[str, Any]:
    """Get a host by ID via ``GET /v1/hosts/{id}``."""
    async with SiteManagerClient(settings) as client:
        logger.info(sanitize_log_message(f"Retrieving host details: {host_id}"))
        response = await client.get_host(host_id)
        data = _envelope_data(response)
        if isinstance(data, list):
            return data[0] if data else {}
        return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------
@require_site_manager
async def list_devices(
    settings: Settings,
    host_ids: list[str] | None = None,
    time: str | None = None,
    page_size: int | None = None,
    next_token: str | None = None,
) -> dict[str, Any]:
    """List devices via ``GET /v1/devices``.

    Args:
        host_ids: Optional list of host IDs to filter by.
        time: Optional RFC3339 timestamp to filter by last processed time.
        page_size: Items per page (≤500).
        next_token: Cursor from a prior response.

    Returns:
        ``{"devices": [...], "next_token": "..."}``.
    """
    async with SiteManagerClient(settings) as client:
        logger.info(
            sanitize_log_message(
                "Listing devices "
                f"(host_ids={host_ids!r}, time={time!r}, page_size={page_size}, "
                f"next_token={next_token!r})"
            )
        )
        response = await client.list_devices(
            host_ids=host_ids,
            time=time,
            page_size=page_size,
            next_token=next_token,
        )
        data = _envelope_data(response)
        devices = data if isinstance(data, list) else []
        return {"devices": devices, "next_token": _envelope_next_token(response)}


# ---------------------------------------------------------------------------
# SD-WAN
# ---------------------------------------------------------------------------
@require_site_manager
async def list_sdwan_configs(settings: Settings) -> list[dict[str, Any]]:
    """List SD-WAN configurations via ``GET /v1/sd-wan-configs``."""
    async with SiteManagerClient(settings) as client:
        logger.info("Listing SD-WAN configurations")
        response = await client.list_sdwan_configs()
        data = _envelope_data(response)
        if not isinstance(data, list):
            return []
        return [SDWANConfig(**config).model_dump() for config in data]


@require_site_manager
async def get_sdwan_config(settings: Settings, config_id: str) -> dict[str, Any]:
    """Get an SD-WAN configuration by ID."""
    async with SiteManagerClient(settings) as client:
        logger.info(sanitize_log_message(f"Retrieving SD-WAN configuration: {config_id}"))
        response = await client.get_sdwan_config(config_id)
        data = _envelope_data(response)
        if isinstance(data, list):
            data = data[0] if data else {}
        return SDWANConfig(**(data or {})).model_dump()


@require_site_manager
async def get_sdwan_config_status(settings: Settings, config_id: str) -> dict[str, Any]:
    """Get an SD-WAN configuration's deployment status."""
    async with SiteManagerClient(settings) as client:
        logger.info(sanitize_log_message(f"Retrieving SD-WAN config status: {config_id}"))
        response = await client.get_sdwan_config_status(config_id)
        data = _envelope_data(response)
        if isinstance(data, list):
            data = data[0] if data else {}
        return SDWANConfigStatus(**(data or {})).model_dump()


# ---------------------------------------------------------------------------
# ISP metrics
# ---------------------------------------------------------------------------
@require_site_manager
async def get_isp_metrics(
    settings: Settings,
    metric_type: str,
    begin_timestamp: str | None = None,
    end_timestamp: str | None = None,
    duration: str | None = None,
) -> dict[str, Any]:
    """Get ISP metrics via ``GET /v1/isp-metrics/{type}``.

    Args:
        metric_type: ``"5m"`` (≥24h retention) or ``"1h"`` (≥30d retention).
        begin_timestamp: RFC3339 inclusive lower bound.
        end_timestamp: RFC3339 exclusive upper bound.
        duration: Relative window (e.g. ``"24h"``); mutually exclusive with
            explicit timestamps.
    """
    async with SiteManagerClient(settings) as client:
        logger.info(
            sanitize_log_message(
                f"Fetching ISP metrics (type={metric_type}, begin={begin_timestamp!r}, "
                f"end={end_timestamp!r}, duration={duration!r})"
            )
        )
        response = await client.get_isp_metrics(
            metric_type=metric_type,
            begin_timestamp=begin_timestamp,
            end_timestamp=end_timestamp,
            duration=duration,
        )
        data = _envelope_data(response)
        return {"metrics": data, "next_token": _envelope_next_token(response)}


@require_site_manager
async def query_isp_metrics(
    settings: Settings,
    metric_type: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    """Query ISP metrics via ``POST /v1/isp-metrics/{type}/query``.

    The request body is forwarded verbatim — refer to the spec for accepted
    fields (``sites``, ``beginTimestamp``, ``endTimestamp``, ``duration``).
    """
    async with SiteManagerClient(settings) as client:
        logger.info(
            sanitize_log_message(
                f"Querying ISP metrics (type={metric_type}, body_keys={list(body.keys())})"
            )
        )
        response = await client.query_isp_metrics(metric_type=metric_type, body=body)
        data = _envelope_data(response)
        return {"metrics": data, "next_token": _envelope_next_token(response)}
