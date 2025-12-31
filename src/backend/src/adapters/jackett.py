"""Jackett indexer management adapter."""

from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from .base import (
    ConnectionTestResult,
    ServiceCapability,
    TokenAuthAdapter,
)


class JackettAdapter(TokenAuthAdapter):
    """Adapter for Jackett torrent indexer proxy."""

    @property
    def service_type(self) -> str:
        return "jackett"

    @property
    def supported_capabilities(self) -> List[ServiceCapability]:
        return [ServiceCapability.API_ACCESS]

    @property
    def token_config_key(self) -> str:
        return "jackett_api_key"

    def _format_token_header(self, token: str) -> Dict[str, str]:
        """Format Jackett API key - uses query parameter instead of header."""
        return {"Content-Type": "application/json", "Accept": "application/json"}

    async def _ensure_client(self):
        """Ensure HTTP client is initialized with cookie support for Jackett."""
        if self._client is None:
            headers = self.get_auth_headers()
            # Jackett requires cookies for its anti-bot protection
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
                follow_redirects=True,
                cookies=httpx.Cookies(),  # Enable cookie jar
            )

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ):
        """Override to add API key to query params for Jackett."""
        if params is None:
            params = {}

        # Get API key from config
        api_key = self.get_config_value("api_key") or self.service_config.api_key
        if api_key:
            params["apikey"] = api_key

        return await super()._make_request(method, endpoint, params=params, json=json, timeout=timeout)

    async def test_connection(self) -> ConnectionTestResult:
        """Test connection to Jackett using Torznab API (more reliable than management API)."""
        start_time = datetime.utcnow()

        try:
            # Use Torznab API which doesn't require cookie auth
            # t=caps returns capabilities of all indexers
            response = await self._make_request(
                "GET", "/api/v2.0/indexers/all/results/torznab/api", params={"t": "caps"}
            )
            end_time = datetime.utcnow()
            response_time = int((end_time - start_time).total_seconds() * 1000)

            # Response is XML, check if it contains Jackett server info
            content = response.text
            if '<server title="Jackett"' in content or "<caps>" in content:
                return ConnectionTestResult(
                    success=True,
                    message="Successfully connected to Jackett (Torznab API)",
                    response_time_ms=response_time,
                    details={"status": "connected", "api_type": "torznab"},
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message="Connected but response doesn't appear to be from Jackett",
                    response_time_ms=response_time,
                    details={"status": "invalid_response"},
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return ConnectionTestResult(
                    success=False,
                    message="Authentication failed - check API key",
                    details={"status": "auth_failed", "status_code": 401},
                )
            # Check if response contains "Cookies required"
            if "Cookies required" in e.response.text:
                return ConnectionTestResult(
                    success=False,
                    message="Jackett requires cookie authentication - management API not accessible",
                    details={"status": "cookies_required", "status_code": e.response.status_code},
                )
            return ConnectionTestResult(
                success=False,
                message=f"HTTP error: {e.response.status_code}",
                details={"status": "http_error", "status_code": e.response.status_code},
            )
        except Exception as e:
            error_str = str(e)
            # Check for cookies error in exception message
            if "Cookies required" in error_str:
                return ConnectionTestResult(
                    success=False,
                    message="Jackett requires cookie authentication - try using Torznab API directly",
                    details={"status": "cookies_required", "error": error_str},
                )
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {error_str}",
                details={"status": "connection_failed", "error": error_str},
            )

    async def get_service_info(self) -> Dict[str, Any]:
        """Get Jackett service information."""
        try:
            response = await self._make_request("GET", "/api/v2.0/server/config")
            data = response.json()

            return {
                "service": "jackett",
                "version": data.get("app_version"),
                "port": data.get("port"),
                "blackhole_dir": data.get("blackholedir"),
                "status": "online",
            }
        except Exception as e:
            return {"service": "jackett", "version": "unknown", "status": "error", "error": str(e)}

    async def get_indexers(self) -> List[Dict[str, Any]]:
        """Get list of configured indexers.

        Note: The management API (/api/v2.0/indexers) requires cookie authentication.
        Instead, we use a search query to discover which indexers are configured
        by extracting tracker info from results.
        """
        try:
            # Try management API first (works if cookies are properly handled)
            response = await self._make_request("GET", "/api/v2.0/indexers")

            # Check if we got redirected (302) or got HTML instead of JSON
            content_type = response.headers.get("content-type", "")
            if "application/json" not in content_type:
                raise Exception("Management API requires cookie auth, falling back to search")

            indexers = response.json()

            # Filter to only configured indexers
            return [
                {
                    "id": indexer.get("id"),
                    "name": indexer.get("name"),
                    "type": indexer.get("type"),
                    "configured": indexer.get("configured", False),
                    "site_link": indexer.get("site_link"),
                    "language": indexer.get("language"),
                    "last_error": indexer.get("last_error"),
                    "potatoenabled": indexer.get("potatoenabled", False),
                    "caps": indexer.get("caps", []),
                }
                for indexer in indexers
                if indexer.get("configured", False)
            ]
        except Exception as e:
            self.logger.warning(f"Management API failed ({e}), using search fallback")
            return await self._get_indexers_from_search()

    async def _get_indexers_from_search(self) -> List[Dict[str, Any]]:
        """Get indexers by performing a search and extracting tracker info from results."""
        try:
            # Perform a broad search to discover configured indexers
            response = await self._make_request(
                "GET",
                "/api/v2.0/indexers/all/results",
                params={"Query": "test"},  # Simple query to trigger all indexers
            )
            data = response.json()

            # Extract unique trackers from results
            trackers = {}
            for result in data.get("Results", []):
                tracker_id = result.get("TrackerId")
                tracker_name = result.get("Tracker")
                tracker_type = result.get("TrackerType", "unknown")

                if tracker_id and tracker_id not in trackers:
                    trackers[tracker_id] = {
                        "id": tracker_id,
                        "name": tracker_name,
                        "type": tracker_type,
                        "configured": True,
                        "site_link": None,
                        "language": None,
                        "last_error": None,
                        "potatoenabled": False,
                        "caps": [],
                    }

            return list(trackers.values())
        except Exception as e:
            self.logger.error(f"Failed to get indexers from search: {e}")
            return []

    async def get_configured_indexers(self) -> List[Dict[str, Any]]:
        """Get only configured/enabled indexers."""
        indexers = await self.get_indexers()
        return [i for i in indexers if i.get("configured")]

    async def search(
        self, query: str, indexers: Optional[List[str]] = None, categories: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """Search across indexers."""
        try:
            params = {"Query": query}

            if indexers:
                params["Tracker[]"] = indexers

            if categories:
                params["Category[]"] = categories

            response = await self._make_request("GET", "/api/v2.0/indexers/all/results", params=params)
            data = response.json()

            return [
                {
                    "title": result.get("Title"),
                    "guid": result.get("Guid"),
                    "link": result.get("Link"),
                    "category": result.get("CategoryDesc"),
                    "size": result.get("Size", 0),
                    "publish_date": result.get("PublishDate"),
                    "tracker": result.get("Tracker"),
                    "seeders": result.get("Seeders"),
                    "peers": result.get("Peers"),
                    "gain": result.get("Gain"),
                    "minimum_ratio": result.get("MinimumRatio"),
                    "minimum_seed_time": result.get("MinimumSeedTime"),
                }
                for result in data.get("Results", [])[:50]
            ]
        except Exception as e:
            self.logger.error(f"Failed to search: {e}")
            return []

    async def test_indexer(self, indexer_id: str) -> Dict[str, Any]:
        """Test a specific indexer."""
        try:
            await self._make_request("GET", f"/api/v2.0/indexers/{indexer_id}/test", timeout=60.0)
            return {"success": True, "indexer_id": indexer_id, "message": "Indexer test passed"}
        except Exception as e:
            return {"success": False, "indexer_id": indexer_id, "error": str(e)}

    async def test_all_indexers(self) -> Dict[str, Any]:
        """Test all configured indexers."""
        indexers = await self.get_configured_indexers()

        results = []
        for indexer in indexers:
            result = await self.test_indexer(indexer["id"])
            result["indexer_name"] = indexer.get("name")
            results.append(result)

        success_count = sum(1 for r in results if r.get("success"))
        return {
            "total_tested": len(results),
            "success_count": success_count,
            "failed_count": len(results) - success_count,
            "results": results,
        }

    async def get_statistics(self) -> Dict[str, Any]:
        """Get Jackett statistics."""
        try:
            indexers = await self.get_indexers()
            configured = [i for i in indexers if i.get("configured")]

            return {
                "total_indexers": len(indexers),
                "configured_indexers": len(configured),
                "indexers_with_errors": sum(1 for i in configured if i.get("last_error")),
                "public_indexers": sum(1 for i in configured if i.get("type") == "public"),
                "private_indexers": sum(1 for i in configured if i.get("type") == "private"),
            }
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                "total_indexers": 0,
                "configured_indexers": 0,
                "indexers_with_errors": 0,
                "public_indexers": 0,
                "private_indexers": 0,
            }
