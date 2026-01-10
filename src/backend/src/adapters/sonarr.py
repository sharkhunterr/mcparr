"""Sonarr TV series management adapter."""

from datetime import datetime
from typing import Any, Dict, List

import httpx

from .base import ConnectionTestResult, ServiceCapability, TokenAuthAdapter


class SonarrAdapter(TokenAuthAdapter):
    """Adapter for Sonarr TV series download management."""

    @property
    def service_type(self) -> str:
        return "sonarr"

    def _get_series_url(self, series_id: int) -> str:
        """Generate Sonarr web UI URL for a series."""
        if series_id:
            return f"{self.public_url}/series/{series_id}"
        return ""

    def _get_tvdb_url(self, tvdb_id: int) -> str:
        """Generate TVDB external URL."""
        if tvdb_id:
            return f"https://thetvdb.com/?id={tvdb_id}&tab=series"
        return ""

    def _get_imdb_url(self, imdb_id: str) -> str:
        """Generate IMDB external URL."""
        if imdb_id:
            return f"https://www.imdb.com/title/{imdb_id}"
        return ""

    @property
    def supported_capabilities(self) -> List[ServiceCapability]:
        return [ServiceCapability.MEDIA_CONTENT, ServiceCapability.API_ACCESS]

    @property
    def token_config_key(self) -> str:
        return "sonarr_api_key"

    def _format_token_header(self, token: str) -> Dict[str, str]:
        """Format Sonarr API key header."""
        return {"X-Api-Key": token, "Content-Type": "application/json", "Accept": "application/json"}

    async def test_connection(self) -> ConnectionTestResult:
        """Test connection to Sonarr."""
        start_time = datetime.utcnow()

        try:
            response = await self._make_request("GET", "/api/v3/system/status")
            end_time = datetime.utcnow()
            response_time = int((end_time - start_time).total_seconds() * 1000)

            data = response.json()

            if "version" in data:
                return ConnectionTestResult(
                    success=True,
                    message="Successfully connected to Sonarr",
                    response_time_ms=response_time,
                    details={
                        "status": "connected",
                        "version": data.get("version"),
                        "app_name": data.get("appName", "Sonarr"),
                        "branch": data.get("branch"),
                    },
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message="Connected but response doesn't appear to be from Sonarr",
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
        """Get Sonarr service information."""
        try:
            response = await self._make_request("GET", "/api/v3/system/status")
            data = response.json()

            return {
                "service": "sonarr",
                "version": data.get("version"),
                "app_name": data.get("appName", "Sonarr"),
                "branch": data.get("branch"),
                "build_time": data.get("buildTime"),
                "runtime_version": data.get("runtimeVersion"),
                "status": "online",
            }
        except Exception as e:
            return {"service": "sonarr", "version": "unknown", "status": "error", "error": str(e)}

    async def get_series(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of TV series in Sonarr."""
        try:
            response = await self._make_request("GET", "/api/v3/series")
            series_list = response.json()

            return [
                {
                    "id": series.get("id"),
                    "title": series.get("title"),
                    "year": series.get("year"),
                    "tvdb_id": series.get("tvdbId"),
                    "imdb_id": series.get("imdbId"),
                    "status": series.get("status"),
                    "monitored": series.get("monitored", False),
                    "season_count": series.get("seasonCount", 0),
                    "episode_count": series.get("episodeCount", 0),
                    "episode_file_count": series.get("episodeFileCount", 0),
                    "path": series.get("path"),
                    "size_on_disk": series.get("sizeOnDisk", 0),
                    "network": series.get("network"),
                    "url": self._get_series_url(series.get("id")),
                    "tvdb_url": self._get_tvdb_url(series.get("tvdbId")),
                    "imdb_url": self._get_imdb_url(series.get("imdbId")),
                }
                for series in series_list[:limit]
            ]
        except Exception as e:
            self.logger.error(f"Failed to get series: {e}")
            return []

    async def search_series(self, query: str) -> List[Dict[str, Any]]:
        """Search for series to add."""
        try:
            response = await self._make_request("GET", "/api/v3/series/lookup", params={"term": query})
            results = response.json()

            return [
                {
                    "title": series.get("title"),
                    "year": series.get("year"),
                    "tvdb_id": series.get("tvdbId"),
                    "imdb_id": series.get("imdbId"),
                    "overview": series.get("overview", "")[:200],
                    "network": series.get("network"),
                    "season_count": series.get("seasonCount", 0),
                    "in_library": series.get("id") is not None,
                    "tvdb_url": self._get_tvdb_url(series.get("tvdbId")),
                    "imdb_url": self._get_imdb_url(series.get("imdbId")),
                }
                for series in results[:20]
            ]
        except Exception as e:
            self.logger.error(f"Failed to search series: {e}")
            return []

    async def get_queue(self) -> List[Dict[str, Any]]:
        """Get download queue."""
        try:
            response = await self._make_request("GET", "/api/v3/queue")
            data = response.json()

            return [
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "series_title": item.get("series", {}).get("title"),
                    "episode_title": item.get("episode", {}).get("title"),
                    "season": item.get("episode", {}).get("seasonNumber"),
                    "episode": item.get("episode", {}).get("episodeNumber"),
                    "status": item.get("status"),
                    "progress": (1 - item.get("sizeleft", 0) / item.get("size", 1)) * 100 if item.get("size") else 0,
                    "download_client": item.get("downloadClient"),
                    "estimated_completion": item.get("estimatedCompletionTime"),
                }
                for item in data.get("records", [])
            ]
        except Exception as e:
            self.logger.error(f"Failed to get queue: {e}")
            return []

    async def get_calendar(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming episodes."""
        try:
            from datetime import timedelta

            start = datetime.utcnow()
            end = start + timedelta(days=days)

            response = await self._make_request(
                "GET",
                "/api/v3/calendar",
                params={"start": start.isoformat(), "end": end.isoformat(), "includeSeries": "true"},
            )
            episodes = response.json()

            return [
                {
                    "id": ep.get("id"),
                    "series_id": ep.get("seriesId"),
                    "series_title": ep.get("series", {}).get("title"),
                    "title": ep.get("title"),
                    "season": ep.get("seasonNumber"),
                    "episode": ep.get("episodeNumber"),
                    "air_date": ep.get("airDateUtc"),
                    "has_file": ep.get("hasFile", False),
                    "url": self._get_series_url(ep.get("seriesId")),
                }
                for ep in episodes
            ]
        except Exception as e:
            self.logger.error(f"Failed to get calendar: {e}")
            return []

    async def get_statistics(self) -> Dict[str, Any]:
        """Get Sonarr statistics."""
        try:
            series = await self.get_series(limit=10000)
            queue = await self.get_queue()

            total_series = len(series)
            monitored = sum(1 for s in series if s.get("monitored"))
            total_episodes = sum(s.get("episode_count", 0) for s in series)
            total_files = sum(s.get("episode_file_count", 0) for s in series)
            total_size = sum(s.get("size_on_disk", 0) for s in series)

            return {
                "total_series": total_series,
                "monitored_series": monitored,
                "total_episodes": total_episodes,
                "episodes_with_files": total_files,
                "missing_episodes": total_episodes - total_files,
                "queue_count": len(queue),
                "total_size_gb": round(total_size / (1024**3), 2),
            }
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                "total_series": 0,
                "monitored_series": 0,
                "total_episodes": 0,
                "episodes_with_files": 0,
                "missing_episodes": 0,
                "queue_count": 0,
                "total_size_gb": 0,
            }

    async def get_indexers(self) -> List[Dict[str, Any]]:
        """Get list of configured indexers in Sonarr."""
        try:
            response = await self._make_request("GET", "/api/v3/indexer")
            indexers = response.json()

            return [
                {
                    "id": indexer.get("id"),
                    "name": indexer.get("name"),
                    "protocol": indexer.get("protocol"),
                    # Support both old 'enable' and newer 'enableRss'/'enableAutomaticSearch' fields
                    "enable": indexer.get("enable", False)
                    or indexer.get("enableRss", False)
                    or indexer.get("enableAutomaticSearch", False),
                    "enableRss": indexer.get("enableRss", False),
                    "enableAutomaticSearch": indexer.get("enableAutomaticSearch", False),
                    "enableInteractiveSearch": indexer.get("enableInteractiveSearch", False),
                    "priority": indexer.get("priority", 25),
                    "supports_rss": indexer.get("supportsRss", False),
                    "supports_search": indexer.get("supportsSearch", False),
                    "implementation": indexer.get("implementation"),
                    "config_contract": indexer.get("configContract"),
                }
                for indexer in indexers
            ]
        except Exception as e:
            self.logger.error(f"Failed to get indexers: {e}")
            return []

    async def test_indexer(self, indexer_id: int) -> Dict[str, Any]:
        """Test a specific indexer by ID."""
        try:
            # First get the indexer config
            response = await self._make_request("GET", f"/api/v3/indexer/{indexer_id}")
            indexer_config = response.json()
            indexer_name = indexer_config.get("name", f"Indexer {indexer_id}")

            # Then test it
            await self._make_request("POST", "/api/v3/indexer/test", json=indexer_config, timeout=60.0)

            return {
                "success": True,
                "indexer_id": indexer_id,
                "indexer_name": indexer_name,
                "message": "Indexer test passed",
            }
        except httpx.HTTPStatusError as e:
            error_msg = "Test failed"
            try:
                error_data = e.response.json()
                if isinstance(error_data, list) and error_data:
                    error_msg = error_data[0].get("errorMessage", str(e))
                elif isinstance(error_data, dict):
                    error_msg = error_data.get("message", str(e))
            except Exception:
                error_msg = str(e)

            return {"success": False, "indexer_id": indexer_id, "error": error_msg}
        except Exception as e:
            return {"success": False, "indexer_id": indexer_id, "error": str(e)}

    async def test_all_indexers(self) -> Dict[str, Any]:
        """Test all enabled indexers."""
        indexers = await self.get_indexers()
        # Filter enabled indexers - check both 'enable' (v3) and 'enableRss'/'enableAutomaticSearch' fields
        enabled_indexers = [
            i for i in indexers
            if i.get("enable") or i.get("enableRss") or i.get("enableAutomaticSearch")
        ]

        # If no enabled indexers but we have indexers, test all of them
        if not enabled_indexers and indexers:
            enabled_indexers = indexers

        results = []
        for indexer in enabled_indexers:
            result = await self.test_indexer(indexer["id"])
            result["indexer_name"] = indexer.get("name")
            results.append(result)

        success_count = sum(1 for r in results if r.get("success"))
        return {
            "total_tested": len(results),
            "success_count": success_count,
            "failed_count": len(results) - success_count,
            "total_indexers": len(indexers),
            "results": results,
        }
