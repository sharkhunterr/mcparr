"""RomM ROM management adapter.

RomM uses Basic Auth or OAuth2 tokens - no static API keys available.
This adapter supports both Basic Auth (username/password) and Bearer tokens.
"""

import base64
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from .base import (
    ConnectionTestResult,
    ServiceCapability,
    TokenAuthAdapter,
)


class RommAdapter(TokenAuthAdapter):
    """Adapter for RomM ROM management system.

    Supports both Basic Auth (username/password) and Bearer tokens.
    Basic Auth is preferred as RomM doesn't have static API keys.
    """

    @property
    def service_type(self) -> str:
        return "romm"

    def _get_rom_url(self, rom_id: int) -> str:
        """Generate RomM web UI URL for a ROM."""
        if rom_id:
            return f"{self.public_url}/rom/{rom_id}"
        return ""

    def _get_platform_url(self, platform_slug: str) -> str:
        """Generate RomM web UI URL for a platform."""
        if platform_slug:
            return f"{self.public_url}/platform/{platform_slug}"
        return ""

    def _get_collection_url(self, collection_id: int) -> str:
        """Generate RomM web UI URL for a collection."""
        if collection_id:
            return f"{self.public_url}/collection/{collection_id}"
        return ""

    @property
    def supported_capabilities(self) -> List[ServiceCapability]:
        return [ServiceCapability.MEDIA_CONTENT, ServiceCapability.USER_MANAGEMENT, ServiceCapability.API_ACCESS]

    @property
    def token_config_key(self) -> str:
        return "romm_api_key"

    def _format_token_header(self, token: str) -> Dict[str, str]:
        """Format RomM auth header (Bearer token)."""
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}

    def _get_auth_header(self) -> Dict[str, str]:
        """Get auth header - tries Bearer token first, then falls back to Basic Auth."""
        # Try Bearer token first (from api_key field)
        api_key = self.service_config.api_key or self.get_config_value("api_key")
        if api_key:
            return self._format_token_header(api_key)

        # Fall back to Basic Auth
        username = getattr(self.service_config, "username", None) or self.get_config_value("username") or ""
        password = getattr(self.service_config, "password", None) or self.get_config_value("password") or ""

        if username and password:
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            return {
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

        # No auth configured
        return {"Content-Type": "application/json", "Accept": "application/json"}

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ):
        """Make HTTP request to RomM API."""
        url = f"{self.base_url.rstrip('/')}{endpoint}"
        headers = self._get_auth_header()

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, params=params, json=json, headers=headers)
            response.raise_for_status()
            return response

    async def test_connection(self) -> ConnectionTestResult:
        """Test connection to RomM."""
        start_time = datetime.utcnow()

        try:
            response = await self._make_request("GET", "/api/heartbeat")
            end_time = datetime.utcnow()
            response_time = int((end_time - start_time).total_seconds() * 1000)

            data = response.json()

            return ConnectionTestResult(
                success=True,
                message="Successfully connected to RomM",
                response_time_ms=response_time,
                details={"status": "connected", "response": data},
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return ConnectionTestResult(
                    success=False,
                    message="Authentication failed - check API key",
                    details={"status": "auth_failed", "status_code": 401},
                )
            return ConnectionTestResult(
                success=False,
                message=f"HTTP error: {e.response.status_code}",
                details={"status": "http_error", "status_code": e.response.status_code},
            )
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                details={"status": "connection_failed", "error": str(e)},
            )

    async def get_service_info(self) -> Dict[str, Any]:
        """Get RomM service information."""
        try:
            response = await self._make_request("GET", "/api/heartbeat")
            data = response.json()

            return {"service": "romm", "status": "online", "heartbeat": data}
        except Exception as e:
            return {"service": "romm", "version": "unknown", "status": "error", "error": str(e)}

    async def get_platforms(self) -> List[Dict[str, Any]]:
        """Get list of gaming platforms."""
        try:
            response = await self._make_request("GET", "/api/platforms")
            platforms = response.json()

            return [
                {
                    "id": platform.get("id"),
                    "slug": platform.get("slug"),
                    "name": platform.get("name"),
                    "igdb_id": platform.get("igdb_id"),
                    "rom_count": platform.get("rom_count", 0),
                    "logo_path": platform.get("logo_path"),
                    "url": self._get_platform_url(platform.get("slug")),
                }
                for platform in platforms
            ]
        except Exception as e:
            self.logger.error(f"Failed to get platforms: {e}")
            return []

    async def get_roms(self, platform_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of ROMs."""
        try:
            endpoint = f"/api/platforms/{platform_id}/roms" if platform_id else "/api/roms"
            params = {"limit": limit}

            response = await self._make_request("GET", endpoint, params=params)
            roms = response.json()

            return [
                {
                    "id": rom.get("id"),
                    "name": rom.get("name"),
                    "file_name": rom.get("file_name"),
                    "file_size": rom.get("file_size", 0),
                    "platform_id": rom.get("platform_id"),
                    "platform_slug": rom.get("platform_slug"),
                    "igdb_id": rom.get("igdb_id"),
                    "summary": rom.get("summary", "")[:200] if rom.get("summary") else None,
                    "path": rom.get("path"),
                    "url": self._get_rom_url(rom.get("id")),
                }
                for rom in (roms if isinstance(roms, list) else roms.get("items", []))[:limit]
            ]
        except Exception as e:
            self.logger.error(f"Failed to get ROMs: {e}")
            return []

    async def search_roms(
        self, query: str, platform_slug: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search for ROMs.

        Args:
            query: Search term for game title
            platform_slug: Optional platform filter (e.g., 'psx', 'n64', 'snes')
            limit: Maximum results to return

        RomM API uses 'search_term' parameter for server-side search.
        Platform filtering is done client-side as the API doesn't support it.
        """
        try:
            # Request more results if filtering by platform (to ensure enough after filtering)
            request_limit = min(limit * 3, 100) if platform_slug else min(limit * 2, 100)
            params = {"search_term": query, "limit": request_limit}

            response = await self._make_request("GET", "/api/roms", params=params)
            roms = response.json()

            # RomM returns paginated response with 'items' key
            rom_list = roms.get("items", []) if isinstance(roms, dict) else roms

            # Apply client-side platform filtering (API doesn't support platform_slug filter)
            if platform_slug:
                rom_list = [r for r in rom_list if r.get("platform_slug") == platform_slug]

            return [
                {
                    "id": rom.get("id"),
                    "name": rom.get("name"),
                    "platform_slug": rom.get("platform_slug"),
                    "file_size": rom.get("file_size", 0),
                    "url": self._get_rom_url(rom.get("id")),
                }
                for rom in rom_list[:limit]
            ]
        except Exception as e:
            self.logger.error(f"Failed to search ROMs: {e}")
            return []

    async def get_collections(
        self, name_filter: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get list of ROM collections.

        Args:
            name_filter: Optional filter by collection name (partial match)
            limit: Maximum collections to return
        """
        try:
            response = await self._make_request("GET", "/api/collections")
            collections = response.json()

            # Handle different response formats
            if isinstance(collections, dict):
                # Could be paginated with 'items' or direct list
                collection_list = collections.get("items", collections.get("data", []))
            elif isinstance(collections, list):
                collection_list = collections
            else:
                collection_list = []

            # Apply name filter if provided
            if name_filter:
                name_lower = name_filter.lower()
                collection_list = [c for c in collection_list if name_lower in c.get("name", "").lower()]

            return [
                {
                    "id": col.get("id"),
                    "name": col.get("name"),
                    "description": col.get("description"),
                    "rom_count": col.get("rom_count", 0),
                    "is_public": col.get("is_public", False),
                    "url": self._get_collection_url(col.get("id")),
                }
                for col in collection_list[:limit]
            ]
        except Exception as e:
            self.logger.error(f"Failed to get collections: {e}")
            return []

    async def get_users(self) -> List[Dict[str, Any]]:
        """Get list of users."""
        try:
            response = await self._make_request("GET", "/api/users")
            users = response.json()

            return [
                {
                    "id": user.get("id"),
                    "username": user.get("username"),
                    "email": user.get("email"),
                    "name": user.get("username"),
                    "role": user.get("role"),
                    "enabled": user.get("enabled", True),
                }
                for user in users
            ]
        except Exception as e:
            self.logger.error(f"Failed to get users: {e}")
            return []

    async def get_statistics(self) -> Dict[str, Any]:
        """Get RomM statistics."""
        try:
            platforms = await self.get_platforms()

            total_roms = sum(p.get("rom_count", 0) for p in platforms)

            return {
                "total_platforms": len(platforms),
                "total_roms": total_roms,
                "platforms": [
                    {"name": p.get("name"), "roms": p.get("rom_count", 0)}
                    for p in sorted(platforms, key=lambda x: x.get("rom_count", 0), reverse=True)[:10]
                ],
            }
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {"total_platforms": 0, "total_roms": 0, "platforms": []}
