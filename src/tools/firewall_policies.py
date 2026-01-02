"""Firewall policies management tools for UniFi v2 API."""

from typing import Any

from ..api.client import UniFiClient
from ..config import APIType, Settings
from ..models.firewall_policy import FirewallPolicy
from ..utils import ResourceNotFoundError, get_logger

logger = get_logger(__name__)


def _ensure_local_api(settings: Settings) -> None:
    """Ensure the UniFi controller is accessed via the local API for v2 endpoints."""
    if settings.api_type != APIType.LOCAL:
        raise NotImplementedError(
            "Firewall policies (v2 API) are only available when UNIFI_API_TYPE='local'. "
            "Please configure a local UniFi gateway connection to use these tools."
        )


async def list_firewall_policies(
    site_id: str,
    settings: Settings,
) -> list[dict[str, Any]]:
    """List all firewall policies (Traffic & Firewall Rules) for a site.

    This tool fetches firewall policies from the UniFi v2 API endpoint.
    Only available with local gateway API (api_type="local").

    Args:
        site_id: Site identifier (default: "default")
        settings: Application settings

    Returns:
        List of firewall policy objects

    Raises:
        NotImplementedError: When using cloud API (v2 endpoints require local access)
        APIError: When API request fails

    Note:
        Cloud API does not support v2 endpoints. Configure UNIFI_API_TYPE=local
        and UNIFI_LOCAL_HOST to use this tool.
    """
    _ensure_local_api(settings)

    async with UniFiClient(settings) as client:
        logger.info(f"Listing firewall policies for site {site_id}")

        if not client.is_authenticated:
            await client.authenticate()

        endpoint = f"{settings.get_v2_api_path(site_id)}/firewall-policies"
        response = await client.get(endpoint)

        policies_data = response if isinstance(response, list) else response.get("data", [])

        return [FirewallPolicy(**policy).model_dump() for policy in policies_data]


async def get_firewall_policy(
    policy_id: str,
    site_id: str,
    settings: Settings,
) -> dict[str, Any]:
    """Get a specific firewall policy by ID.

    Retrieves detailed information about a single firewall policy
    from the v2 API endpoint.

    Args:
        policy_id: The firewall policy ID
        site_id: Site identifier (default: "default")
        settings: Application settings

    Returns:
        Firewall policy object

    Raises:
        NotImplementedError: When using cloud API (v2 endpoints require local access)
        ResourceNotFoundError: If policy not found
        APIError: When API request fails

    Note:
        Cloud API does not support v2 endpoints. Configure UNIFI_API_TYPE=local
        and UNIFI_LOCAL_HOST to use this tool.

    Example:
        >>> policy = await get_firewall_policy(
        ...     "682a0e42220317278bb0b2cb",
        ...     "default",
        ...     settings
        ... )
        >>> print(f"{policy['name']}: {policy['action']}")
    """
    _ensure_local_api(settings)

    async with UniFiClient(settings) as client:
        logger.info(f"Getting firewall policy {policy_id} for site {site_id}")

        if not client.is_authenticated:
            await client.authenticate()

        endpoint = f"{settings.get_v2_api_path(site_id)}/firewall-policies/{policy_id}"

        try:
            response = await client.get(endpoint)
        except ResourceNotFoundError:
            raise ResourceNotFoundError("firewall_policy", policy_id)

        # Handle both wrapped and unwrapped responses
        if isinstance(response, dict) and "data" in response:
            data = response["data"]
        else:
            data = response

        if not data:
            raise ResourceNotFoundError("firewall_policy", policy_id)

        return FirewallPolicy(**data).model_dump()
