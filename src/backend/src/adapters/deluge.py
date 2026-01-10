"""Deluge torrent client adapter."""

from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from .base import (
    AdapterError,
    AuthenticationError,
    BaseServiceAdapter,
    ConnectionTestResult,
    ServiceCapability,
)


class DelugeAdapter(BaseServiceAdapter):
    """Adapter for Deluge BitTorrent client."""

    def __init__(self, service_config):
        super().__init__(service_config)
        self._request_id = 0
        self._session_cookie = None

    @property
    def service_type(self) -> str:
        return "deluge"

    @property
    def supported_capabilities(self) -> List[ServiceCapability]:
        return [ServiceCapability.API_ACCESS]

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers.

        Deluge uses session cookies for authentication, not headers.
        This method returns empty headers as auth is handled via _auth().
        """
        return {"Content-Type": "application/json"}

    def _get_next_request_id(self) -> int:
        """Get next JSON-RPC request ID."""
        self._request_id += 1
        return self._request_id

    async def _auth(self) -> bool:
        """Authenticate with Deluge Web API."""
        try:
            # Try password field first, then api_key as fallback
            password = (
                self.get_config_value("password")
                or getattr(self.service_config, "password", None)
                or self.get_config_value("api_key")
                or getattr(self.service_config, "api_key", None)
                or ""
            )

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/json",
                    json={"method": "auth.login", "params": [password], "id": self._get_next_request_id()},
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("result"):
                        # Store session cookie
                        self._session_cookie = response.cookies.get("_session_id")
                        return True
                return False
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False

    async def _rpc_call(self, method: str, params: Optional[List] = None) -> Any:
        """Make a JSON-RPC call to Deluge."""
        if params is None:
            params = []

        # Ensure we're authenticated
        if not self._session_cookie:
            if not await self._auth():
                raise AuthenticationError("Failed to authenticate with Deluge")

        cookies = {"_session_id": self._session_cookie} if self._session_cookie else {}

        async with httpx.AsyncClient(timeout=30.0, cookies=cookies) as client:
            response = await client.post(
                f"{self.base_url}/json",
                json={"method": method, "params": params, "id": self._get_next_request_id()},
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("error"):
                    raise AdapterError(f"RPC error: {data['error']}")
                return data.get("result")
            else:
                raise AdapterError(f"HTTP error: {response.status_code}")

    async def test_connection(self) -> ConnectionTestResult:
        """Test connection to Deluge."""
        start_time = datetime.utcnow()

        try:
            if await self._auth():
                # Check if connected to daemon
                connected = await self._rpc_call("web.connected")

                end_time = datetime.utcnow()
                response_time = int((end_time - start_time).total_seconds() * 1000)

                return ConnectionTestResult(
                    success=True,
                    message="Successfully connected to Deluge",
                    response_time_ms=response_time,
                    details={"status": "connected", "daemon_connected": connected},
                )
            else:
                return ConnectionTestResult(
                    success=False, message="Authentication failed - check password", details={"status": "auth_failed"}
                )

        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                details={"status": "connection_failed", "error": str(e)},
            )

    async def get_service_info(self) -> Dict[str, Any]:
        """Get Deluge service information."""
        try:
            version = await self._rpc_call("daemon.info")
            config = await self._rpc_call("core.get_config")

            return {
                "service": "deluge",
                "version": version,
                "download_location": config.get("download_location") if config else None,
                "max_download_speed": config.get("max_download_speed") if config else None,
                "max_upload_speed": config.get("max_upload_speed") if config else None,
                "status": "online",
            }
        except Exception as e:
            return {"service": "deluge", "version": "unknown", "status": "error", "error": str(e)}

    async def get_torrents(self) -> List[Dict[str, Any]]:
        """Get list of torrents."""
        try:
            # Get torrent list with specific fields
            fields = [
                "name",
                "state",
                "progress",
                "download_payload_rate",
                "upload_payload_rate",
                "eta",
                "total_size",
                "total_done",
                "ratio",
                "num_seeds",
                "num_peers",
                "time_added",
            ]

            torrents = await self._rpc_call("core.get_torrents_status", [{}, fields])

            result = []
            for torrent_id, data in (torrents or {}).items():
                result.append(
                    {
                        "id": torrent_id,
                        "name": data.get("name"),
                        "state": data.get("state"),
                        "progress": round(data.get("progress", 0), 2),
                        "download_speed": data.get("download_payload_rate", 0),
                        "upload_speed": data.get("upload_payload_rate", 0),
                        "eta": data.get("eta"),
                        "total_size": data.get("total_size", 0),
                        "total_done": data.get("total_done", 0),
                        "ratio": round(data.get("ratio", 0), 2),
                        "seeds": data.get("num_seeds", 0),
                        "peers": data.get("num_peers", 0),
                        "added": data.get("time_added"),
                    }
                )

            return result
        except Exception as e:
            self.logger.error(f"Failed to get torrents: {e}")
            return []

    async def add_torrent(self, magnet_or_url: str, options: Optional[Dict] = None) -> Dict[str, Any]:
        """Add a torrent by magnet link or URL."""
        try:
            if options is None:
                options = {}

            if magnet_or_url.startswith("magnet:"):
                result = await self._rpc_call("core.add_torrent_magnet", [magnet_or_url, options])
            else:
                result = await self._rpc_call("core.add_torrent_url", [magnet_or_url, options])

            return {"success": True, "torrent_id": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def pause_torrent(self, torrent_id: str) -> bool:
        """Pause a torrent."""
        try:
            await self._rpc_call("core.pause_torrent", [[torrent_id]])
            return True
        except Exception as e:
            self.logger.error(f"Failed to pause torrent: {e}")
            return False

    async def resume_torrent(self, torrent_id: str) -> bool:
        """Resume a torrent."""
        try:
            await self._rpc_call("core.resume_torrent", [[torrent_id]])
            return True
        except Exception as e:
            self.logger.error(f"Failed to resume torrent: {e}")
            return False

    async def remove_torrent(self, torrent_id: str, remove_data: bool = False) -> bool:
        """Remove a torrent."""
        try:
            await self._rpc_call("core.remove_torrent", [torrent_id, remove_data])
            return True
        except Exception as e:
            self.logger.error(f"Failed to remove torrent: {e}")
            return False

    async def search_torrents(
        self, query: str, status_filter: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search torrents by name with fuzzy matching.

        Args:
            query: Search term for torrent name (supports partial/fuzzy matching)
            status_filter: Optional filter by state (Downloading, Seeding, Paused, etc.)
            limit: Maximum results to return

        Returns:
            List of matching torrents sorted by relevance
        """
        try:
            # Get all torrents first
            all_torrents = await self.get_torrents()

            if not all_torrents:
                return []

            # Normalize query for matching
            query_lower = query.lower()
            query_words = query_lower.split()

            results = []
            for torrent in all_torrents:
                name = torrent.get("name", "")
                name_lower = name.lower()

                # Check status filter first
                if status_filter:
                    torrent_state = torrent.get("state", "").lower()
                    if status_filter.lower() != torrent_state:
                        continue

                # Calculate match score
                score = 0

                # Exact match (highest priority)
                if query_lower in name_lower:
                    score = 100

                    # Bonus for exact match at start
                    if name_lower.startswith(query_lower):
                        score += 50

                    # Bonus for exact word match
                    if query_lower == name_lower:
                        score += 100
                else:
                    # Check individual words for partial matching
                    matched_words = 0
                    for word in query_words:
                        if len(word) >= 2 and word in name_lower:
                            matched_words += 1
                            score += 20

                    # Require at least one word to match
                    if matched_words == 0:
                        continue

                    # Bonus if all words match
                    if matched_words == len(query_words) and len(query_words) > 1:
                        score += 30

                if score > 0:
                    results.append({**torrent, "_score": score})

            # Sort by score (highest first), then by name
            results.sort(key=lambda x: (-x.get("_score", 0), x.get("name", "").lower()))

            # Remove score from results and apply limit
            return [{k: v for k, v in t.items() if k != "_score"} for t in results[:limit]]

        except Exception as e:
            self.logger.error(f"Failed to search torrents: {e}")
            return []

    async def get_statistics(self) -> Dict[str, Any]:
        """Get Deluge statistics."""
        try:
            torrents = await self.get_torrents()
            session_status = await self._rpc_call(
                "core.get_session_status", [["download_rate", "upload_rate", "dht_nodes"]]
            )

            downloading = sum(1 for t in torrents if t.get("state") == "Downloading")
            seeding = sum(1 for t in torrents if t.get("state") == "Seeding")
            paused = sum(1 for t in torrents if t.get("state") == "Paused")
            total_size = sum(t.get("total_size", 0) for t in torrents)

            return {
                "total_torrents": len(torrents),
                "downloading": downloading,
                "seeding": seeding,
                "paused": paused,
                "download_rate": session_status.get("download_rate", 0) if session_status else 0,
                "upload_rate": session_status.get("upload_rate", 0) if session_status else 0,
                "dht_nodes": session_status.get("dht_nodes", 0) if session_status else 0,
                "total_size_gb": round(total_size / (1024**3), 2),
            }
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                "total_torrents": 0,
                "downloading": 0,
                "seeding": 0,
                "paused": 0,
                "download_rate": 0,
                "upload_rate": 0,
                "dht_nodes": 0,
                "total_size_gb": 0,
            }
