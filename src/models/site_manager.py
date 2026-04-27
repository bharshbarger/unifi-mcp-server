"""Site Manager API models.

Pydantic models for the cloud UniFi Site Manager API v1.0.0. Only the shapes
actively used by the tool layer are kept; previous health/vantage-point/
version-control models were removed because the underlying endpoints don't
exist in the spec.
"""

from typing import Literal

from pydantic import BaseModel, Field


class SiteInventory(BaseModel):
    """Best-effort inventory projection for a single site.

    The cloud Site Manager API only guarantees a sites listing; richer fields
    here are populated when the upstream payload includes them and default to
    zero/empty otherwise.
    """

    site_id: str = Field(..., description="Site identifier")
    site_name: str = Field(..., description="Site name")
    device_count: int = Field(0, description="Total devices")
    device_types: dict[str, int] = Field(default_factory=dict, description="Count by device type")
    client_count: int = Field(0, description="Total active clients")
    network_count: int = Field(0, description="Total networks/VLANs")
    ssid_count: int = Field(0, description="Total SSIDs")
    uplink_count: int = Field(0, description="Total WAN uplinks")
    vpn_tunnel_count: int = Field(0, description="Total VPN tunnels")
    firewall_rule_count: int = Field(0, description="Total firewall rules")
    last_updated: str = Field("", description="Inventory timestamp (ISO)")


class CrossSiteSearchResult(BaseModel):
    """Result of a cross-site keyword search."""

    total_results: int = Field(0, description="Total number of results found")
    search_query: str = Field(..., description="Original search query")
    result_type: Literal["device", "client", "network", "all"] = Field(
        ..., description="Type of results"
    )
    results: list[dict] = Field(
        default_factory=list, description="Search results with site context"
    )


class SDWANConfig(BaseModel):
    """SD-WAN configuration record from ``/v1/sd-wan-configs``."""

    config_id: str = Field(..., description="Configuration identifier")
    name: str = Field(..., description="Configuration name")
    topology_type: Literal["hub-spoke", "mesh", "point-to-point"] = Field(
        ..., description="SD-WAN topology type"
    )
    hub_site_ids: list[str] = Field(default_factory=list, description="Hub site identifiers")
    spoke_site_ids: list[str] = Field(default_factory=list, description="Spoke site identifiers")
    failover_enabled: bool = Field(False, description="Failover configuration enabled")
    created_at: str = Field(..., description="Creation timestamp (ISO)")
    updated_at: str = Field(..., description="Last update timestamp (ISO)")
    status: Literal["active", "inactive", "pending"] = Field(
        ..., description="Configuration status"
    )


class SDWANConfigStatus(BaseModel):
    """Deployment status returned by ``/v1/sd-wan-configs/{id}/status``."""

    config_id: str = Field(..., description="Configuration identifier")
    deployment_status: Literal["deployed", "deploying", "failed", "pending"] = Field(
        ..., description="Deployment status"
    )
    sites_deployed: int = Field(0, description="Number of sites successfully deployed")
    sites_total: int = Field(0, description="Total number of sites in configuration")
    last_deployment_at: str | None = Field(None, description="Last deployment timestamp (ISO)")
    error_message: str | None = Field(None, description="Error message if deployment failed")


class Host(BaseModel):
    """Managed host/console record from ``/v1/hosts``."""

    host_id: str = Field(..., description="Host identifier")
    hostname: str = Field(..., description="Hostname")
    ip_address: str | None = Field(None, description="IP address")
    mac_address: str | None = Field(None, description="MAC address")
    model: str | None = Field(None, description="Device model")
    version: str | None = Field(None, description="Firmware/software version")
    site_count: int = Field(0, description="Number of associated sites")
    status: Literal["online", "offline", "unreachable"] = Field(..., description="Host status")
    last_seen: str = Field(..., description="Last seen timestamp (ISO)")
