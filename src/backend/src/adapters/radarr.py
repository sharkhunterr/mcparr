"""Radarr movie management adapter."""

from datetime import datetime
from typing import Any, Dict, List

import httpx

from .base import ConnectionTestResult, ServiceCapability, TokenAuthAdapter


class RadarrAdapter(TokenAuthAdapter):
    """Adapter for Radarr movie download management."""

    @property
    def service_type(self) -> str:
        return "radarr"

    @property
    def supported_capabilities(self) -> List[ServiceCapability]:
        return [ServiceCapability.MEDIA_CONTENT, ServiceCapability.API_ACCESS]

    @property
    def token_config_key(self) -> str:
        return "radarr_api_key"

    def _format_token_header(self, token: str) -> Dict[str, str]:
        """Format Radarr API key header."""
        return {"X-Api-Key": token, "Content-Type": "application/json", "Accept": "application/json"}

    async def test_connection(self) -> ConnectionTestResult:
        """Test connection to Radarr."""
        start_time = datetime.utcnow()

        try:
            response = await self._make_request("GET", "/api/v3/system/status")
            end_time = datetime.utcnow()
            response_time = int((end_time - start_time).total_seconds() * 1000)

            data = response.json()

            if "version" in data:
                return ConnectionTestResult(
                    success=True,
                    message="Successfully connected to Radarr",
                    response_time_ms=response_time,
                    details={
                        "status": "connected",
                        "version": data.get("version"),
                        "app_name": data.get("appName", "Radarr"),
                        "branch": data.get("branch"),
                    },
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message="Connected but response doesn't appear to be from Radarr",
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
        """Get Radarr service information."""
        try:
            response = await self._make_request("GET", "/api/v3/system/status")
            data = response.json()

            return {
                "service": "radarr",
                "version": data.get("version"),
                "app_name": data.get("appName", "Radarr"),
                "branch": data.get("branch"),
                "build_time": data.get("buildTime"),
                "runtime_version": data.get("runtimeVersion"),
                "status": "online",
            }
        except Exception as e:
            return {"service": "radarr", "version": "unknown", "status": "error", "error": str(e)}

    async def get_movies(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of movies in Radarr."""
        try:
            response = await self._make_request("GET", "/api/v3/movie")
            movies = response.json()

            return [
                {
                    "id": movie.get("id"),
                    "title": movie.get("title"),
                    "year": movie.get("year"),
                    "tmdb_id": movie.get("tmdbId"),
                    "imdb_id": movie.get("imdbId"),
                    "has_file": movie.get("hasFile", False),
                    "monitored": movie.get("monitored", False),
                    "status": movie.get("status"),
                    "quality_profile_id": movie.get("qualityProfileId"),
                    "path": movie.get("path"),
                    "size_on_disk": movie.get("sizeOnDisk", 0),
                }
                for movie in movies[:limit]
            ]
        except Exception as e:
            self.logger.error(f"Failed to get movies: {e}")
            return []

    async def search_movie(self, query: str) -> List[Dict[str, Any]]:
        """Search for movies to add."""
        try:
            response = await self._make_request("GET", "/api/v3/movie/lookup", params={"term": query})
            results = response.json()

            return [
                {
                    "title": movie.get("title"),
                    "year": movie.get("year"),
                    "tmdb_id": movie.get("tmdbId"),
                    "imdb_id": movie.get("imdbId"),
                    "overview": movie.get("overview", "")[:200],
                    "in_library": movie.get("id") is not None,
                }
                for movie in results[:20]
            ]
        except Exception as e:
            self.logger.error(f"Failed to search movies: {e}")
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
                    "status": item.get("status"),
                    "progress": item.get("sizeleft", 0) / item.get("size", 1) * 100 if item.get("size") else 0,
                    "download_client": item.get("downloadClient"),
                    "estimated_completion": item.get("estimatedCompletionTime"),
                }
                for item in data.get("records", [])
            ]
        except Exception as e:
            self.logger.error(f"Failed to get queue: {e}")
            return []

    async def get_calendar(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming movies."""
        try:
            from datetime import timedelta

            start = datetime.utcnow()
            end = start + timedelta(days=days)

            response = await self._make_request(
                "GET", "/api/v3/calendar", params={"start": start.isoformat(), "end": end.isoformat()}
            )
            movies = response.json()

            return [
                {
                    "id": movie.get("id"),
                    "title": movie.get("title"),
                    "year": movie.get("year"),
                    "release_date": movie.get("inCinemas") or movie.get("physicalRelease"),
                    "has_file": movie.get("hasFile", False),
                }
                for movie in movies
            ]
        except Exception as e:
            self.logger.error(f"Failed to get calendar: {e}")
            return []

    async def get_statistics(self) -> Dict[str, Any]:
        """Get Radarr statistics."""
        try:
            movies = await self.get_movies(limit=10000)
            queue = await self.get_queue()

            total_movies = len(movies)
            movies_with_files = sum(1 for m in movies if m.get("has_file"))
            monitored = sum(1 for m in movies if m.get("monitored"))
            total_size = sum(m.get("size_on_disk", 0) for m in movies)

            return {
                "total_movies": total_movies,
                "movies_with_files": movies_with_files,
                "monitored_movies": monitored,
                "missing_movies": monitored - movies_with_files,
                "queue_count": len(queue),
                "total_size_gb": round(total_size / (1024**3), 2),
            }
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                "total_movies": 0,
                "movies_with_files": 0,
                "monitored_movies": 0,
                "missing_movies": 0,
                "queue_count": 0,
                "total_size_gb": 0,
            }

    async def get_indexers(self) -> List[Dict[str, Any]]:
        """Get list of configured indexers in Radarr."""
        try:
            response = await self._make_request("GET", "/api/v3/indexer")
            indexers = response.json()

            return [
                {
                    "id": indexer.get("id"),
                    "name": indexer.get("name"),
                    "protocol": indexer.get("protocol"),
                    "enable": indexer.get("enable", False),
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
        enabled_indexers = [i for i in indexers if i.get("enable")]

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
            "results": results,
        }
