"""Site Manager API resources."""

import json

from ..api.site_manager_client import SiteManagerClient
from ..config import Settings
from ..utils import get_logger

logger = get_logger(__name__)


class SiteManagerResource:
    """Resource handler for the cloud Site Manager API."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = get_logger(__name__, settings.log_level)

    async def get_all_sites(self) -> str:
        """List all sites visible to the configured Site Manager API key."""
        if not self.settings.site_manager_enabled:
            return "Site Manager API is not enabled. Set UNIFI_SITE_MANAGER_ENABLED=true"

        async with SiteManagerClient(self.settings) as client:
            response = await client.list_sites()
            data = response.get("data", []) if isinstance(response, dict) else response
            sites = data if isinstance(data, list) else []
            next_token = response.get("nextToken") if isinstance(response, dict) else None
            return json.dumps(
                {"sites": sites, "next_token": next_token},
                indent=2,
                default=str,
            )
