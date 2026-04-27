"""Site Manager API client for the UniFi cloud Site Manager API v1.0.0.

Implements the endpoints defined by the official OpenAPI spec at
https://developer.ui.com/site-manager/v1.0.0/. Only the documented surface is
exposed; previous helpers that hit non-existent paths have been removed.
"""

from typing import Any

import httpx

from ..config import Settings
from ..utils import (
    APIError,
    AuthenticationError,
    NetworkError,
    RateLimitError,
    ResourceNotFoundError,
    get_logger,
)

logger = get_logger(__name__)

# Spec: pageSize is bounded at 500 items per request.
MAX_PAGE_SIZE = 500

# Spec: ISP metrics interval is constrained to two values.
ISP_METRIC_INTERVALS: tuple[str, ...] = ("5m", "1h")


class SiteManagerClient:
    """Client for the UniFi Site Manager API (https://api.ui.com/v1/)."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = get_logger(__name__, settings.log_level)

        self.client = httpx.AsyncClient(
            base_url="https://api.ui.com/v1/",
            headers=settings.get_site_manager_headers(),
            timeout=settings.request_timeout,
            verify=True,
        )

        self._authenticated = False

    async def __aenter__(self) -> "SiteManagerClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def close(self) -> None:
        await self.client.aclose()

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    async def authenticate(self) -> None:
        """Mark the client as authenticated.

        The Site Manager API uses bearer-token-style auth via ``X-API-Key`` and
        validates the key on every request. There is no login round trip; we
        defer validation to the first real call.
        """
        self._authenticated = True

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self._authenticated:
            await self.authenticate()

        endpoint = endpoint.lstrip("/")
        try:
            response = await self.client.request(
                method,
                endpoint,
                params=params,
                json=json_body,
            )
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
        except httpx.HTTPStatusError as e:
            self._raise_for_status(e)
            raise  # pragma: no cover - _raise_for_status always raises
        except httpx.NetworkError as e:
            raise NetworkError(f"Network communication failed: {e}") from e

    @staticmethod
    def _raise_for_status(error: httpx.HTTPStatusError) -> None:
        status = error.response.status_code
        body_text = error.response.text

        try:
            payload = error.response.json()
        except ValueError:
            payload = None

        api_message = (payload or {}).get("message") if isinstance(payload, dict) else None
        api_code = (payload or {}).get("code") if isinstance(payload, dict) else None
        message = api_message or body_text or error.response.reason_phrase

        if status == 400:
            raise APIError(
                f"Site Manager API bad request: {message}",
                status_code=400,
                response_data=payload,
            ) from error
        if status == 401:
            raise AuthenticationError(
                "Site Manager API authentication failed (check X-API-Key)"
            ) from error
        if status == 403:
            raise APIError(
                f"Site Manager API forbidden: {message}",
                status_code=403,
                response_data=payload,
            ) from error
        if status == 404:
            raise ResourceNotFoundError("resource", str(error.request.url.path)) from error
        if status == 429:
            retry_after_raw = error.response.headers.get("Retry-After")
            retry_after: int | None = None
            if retry_after_raw is not None:
                try:
                    retry_after = int(float(retry_after_raw))
                except ValueError:
                    retry_after = None
            raise RateLimitError(
                message=f"Site Manager API rate limit exceeded: {message}",
                retry_after=retry_after,
            ) from error
        if status in (500, 502, 503, 504):
            raise APIError(
                f"Site Manager API upstream error ({status}, code={api_code}): {message}",
                status_code=status,
                response_data=payload,
            ) from error

        raise APIError(
            f"Site Manager API error ({status}, code={api_code}): {message}",
            status_code=status,
            response_data=payload,
        ) from error

    async def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Issue a GET against the Site Manager API.

        Returns the raw response envelope (``{data, httpStatusCode, traceId,
        nextToken}``) so callers can propagate ``nextToken`` for pagination.
        """
        return await self._request("GET", endpoint, params=params)

    async def post(
        self,
        endpoint: str,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._request("POST", endpoint, params=params, json_body=json_body)

    @staticmethod
    def _paginate_params(page_size: int | None, next_token: str | None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if page_size is not None:
            if page_size < 1 or page_size > MAX_PAGE_SIZE:
                raise ValueError(
                    f"page_size must be between 1 and {MAX_PAGE_SIZE} (got {page_size})"
                )
            params["pageSize"] = page_size
        if next_token is not None:
            params["nextToken"] = next_token
        return params

    # ------------------------------------------------------------------
    # Sites
    # ------------------------------------------------------------------
    async def list_sites(
        self,
        page_size: int | None = None,
        next_token: str | None = None,
    ) -> dict[str, Any]:
        """``GET /v1/sites`` — list all sites for the account."""
        return await self.get("sites", params=self._paginate_params(page_size, next_token))

    # ------------------------------------------------------------------
    # Hosts
    # ------------------------------------------------------------------
    async def list_hosts(
        self,
        page_size: int | None = None,
        next_token: str | None = None,
    ) -> dict[str, Any]:
        """``GET /v1/hosts`` — list all managed hosts/consoles."""
        return await self.get("hosts", params=self._paginate_params(page_size, next_token))

    async def get_host(self, host_id: str) -> dict[str, Any]:
        """``GET /v1/hosts/{id}`` — get a host by ID."""
        return await self.get(f"hosts/{host_id}")

    # ------------------------------------------------------------------
    # Devices
    # ------------------------------------------------------------------
    async def list_devices(
        self,
        host_ids: list[str] | None = None,
        time: str | None = None,
        page_size: int | None = None,
        next_token: str | None = None,
    ) -> dict[str, Any]:
        """``GET /v1/devices`` — list devices across hosts.

        Args:
            host_ids: Filter results to these host IDs (becomes ``hostIds[]``).
            time: RFC3339 timestamp marking the last processed change.
            page_size: Items per page (≤500 per spec).
            next_token: Pagination cursor returned by the previous response.
        """
        params: dict[str, Any] = self._paginate_params(page_size, next_token)
        if host_ids:
            params["hostIds[]"] = list(host_ids)
        if time is not None:
            params["time"] = time
        return await self.get("devices", params=params)

    # ------------------------------------------------------------------
    # SD-WAN
    # ------------------------------------------------------------------
    async def list_sdwan_configs(self) -> dict[str, Any]:
        """``GET /v1/sd-wan-configs`` — list SD-WAN configurations."""
        return await self.get("sd-wan-configs")

    async def get_sdwan_config(self, config_id: str) -> dict[str, Any]:
        """``GET /v1/sd-wan-configs/{id}`` — get an SD-WAN config by ID."""
        return await self.get(f"sd-wan-configs/{config_id}")

    async def get_sdwan_config_status(self, config_id: str) -> dict[str, Any]:
        """``GET /v1/sd-wan-configs/{id}/status`` — get deployment status."""
        return await self.get(f"sd-wan-configs/{config_id}/status")

    # ------------------------------------------------------------------
    # ISP metrics
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_isp_metric_type(metric_type: str) -> None:
        if metric_type not in ISP_METRIC_INTERVALS:
            raise ValueError(
                f"metric_type must be one of {ISP_METRIC_INTERVALS} (got {metric_type!r})"
            )

    async def get_isp_metrics(
        self,
        metric_type: str,
        begin_timestamp: str | None = None,
        end_timestamp: str | None = None,
        duration: str | None = None,
    ) -> dict[str, Any]:
        """``GET /v1/isp-metrics/{type}`` — bulk ISP metrics for the account.

        Args:
            metric_type: ``"5m"`` (24h+ retention) or ``"1h"`` (30d+ retention).
            begin_timestamp: RFC3339 inclusive lower bound.
            end_timestamp: RFC3339 exclusive upper bound.
            duration: Relative window (e.g. ``"24h"``); mutually exclusive with
                explicit timestamps per the spec.
        """
        self._validate_isp_metric_type(metric_type)
        params: dict[str, Any] = {}
        if begin_timestamp is not None:
            params["beginTimestamp"] = begin_timestamp
        if end_timestamp is not None:
            params["endTimestamp"] = end_timestamp
        if duration is not None:
            params["duration"] = duration
        return await self.get(f"isp-metrics/{metric_type}", params=params)

    async def query_isp_metrics(
        self,
        metric_type: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        """``POST /v1/isp-metrics/{type}/query`` — filtered ISP metrics query."""
        self._validate_isp_metric_type(metric_type)
        return await self.post(f"isp-metrics/{metric_type}/query", json_body=body)
