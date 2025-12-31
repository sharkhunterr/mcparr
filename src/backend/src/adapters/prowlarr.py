"""Prowlarr indexer management adapter."""

from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from .base import (
    ConnectionTestResult,
    ServiceCapability,
    TokenAuthAdapter,
)


class ProwlarrAdapter(TokenAuthAdapter):
    """Adapter for Prowlarr indexer management."""

    @property
    def service_type(self) -> str:
        return "prowlarr"

    @property
    def supported_capabilities(self) -> List[ServiceCapability]:
        return [ServiceCapability.API_ACCESS]

    @property
    def token_config_key(self) -> str:
        return "prowlarr_api_key"

    def _format_token_header(self, token: str) -> Dict[str, str]:
        """Format Prowlarr API key header."""
        return {"X-Api-Key": token, "Content-Type": "application/json", "Accept": "application/json"}

    async def test_connection(self) -> ConnectionTestResult:
        """Test connection to Prowlarr."""
        start_time = datetime.utcnow()

        try:
            response = await self._make_request("GET", "/api/v1/system/status")
            end_time = datetime.utcnow()
            response_time = int((end_time - start_time).total_seconds() * 1000)

            data = response.json()

            if "version" in data:
                return ConnectionTestResult(
                    success=True,
                    message="Successfully connected to Prowlarr",
                    response_time_ms=response_time,
                    details={
                        "status": "connected",
                        "version": data.get("version"),
                        "app_name": data.get("appName", "Prowlarr"),
                        "branch": data.get("branch"),
                    },
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message="Connected but response doesn't appear to be from Prowlarr",
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
        """Get Prowlarr service information."""
        try:
            response = await self._make_request("GET", "/api/v1/system/status")
            data = response.json()

            return {
                "service": "prowlarr",
                "version": data.get("version"),
                "app_name": data.get("appName", "Prowlarr"),
                "branch": data.get("branch"),
                "build_time": data.get("buildTime"),
                "status": "online",
            }
        except Exception as e:
            return {"service": "prowlarr", "version": "unknown", "status": "error", "error": str(e)}

    async def get_indexers(self) -> List[Dict[str, Any]]:
        """Get list of configured indexers."""
        try:
            response = await self._make_request("GET", "/api/v1/indexer")
            indexers = response.json()

            return [
                {
                    "id": indexer.get("id"),
                    "name": indexer.get("name"),
                    "protocol": indexer.get("protocol"),
                    "privacy": indexer.get("privacy"),
                    "enable": indexer.get("enable", False),
                    "priority": indexer.get("priority", 25),
                    "supports_rss": indexer.get("supportsRss", False),
                    "supports_search": indexer.get("supportsSearch", False),
                }
                for indexer in indexers
            ]
        except Exception as e:
            self.logger.error(f"Failed to get indexers: {e}")
            return []

    async def get_indexer_stats(self) -> List[Dict[str, Any]]:
        """Get indexer statistics."""
        try:
            response = await self._make_request("GET", "/api/v1/indexerstats")
            stats = response.json()

            return [
                {
                    "indexer_id": stat.get("indexerId"),
                    "indexer_name": stat.get("indexerName"),
                    "average_response_time": stat.get("averageResponseTime"),
                    "number_of_queries": stat.get("numberOfQueries"),
                    "number_of_grabs": stat.get("numberOfGrabs"),
                    "number_of_failures": stat.get("numberOfFailures"),
                }
                for stat in stats.get("indexers", [])
            ]
        except Exception as e:
            self.logger.error(f"Failed to get indexer stats: {e}")
            return []

    async def search(self, query: str, categories: Optional[List[int]] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Search across all indexers."""
        try:
            params = {"query": query}
            if categories:
                params["categories"] = ",".join(map(str, categories))

            response = await self._make_request("GET", "/api/v1/search", params=params)
            results = response.json()

            return [
                {
                    "guid": result.get("guid"),
                    "title": result.get("title"),
                    "indexer": result.get("indexer"),
                    "size": result.get("size", 0),
                    "age_days": result.get("age", 0),
                    "seeders": result.get("seeders"),
                    "leechers": result.get("leechers"),
                    "categories": result.get("categories", []),
                    "download_url": result.get("downloadUrl"),
                }
                for result in results[:limit]
            ]
        except Exception as e:
            self.logger.error(f"Failed to search: {e}")
            return []

    async def get_applications(self) -> List[Dict[str, Any]]:
        """Get connected applications (Radarr, Sonarr, etc.)."""
        try:
            response = await self._make_request("GET", "/api/v1/applications")
            apps = response.json()

            return [
                {
                    "id": app.get("id"),
                    "name": app.get("name"),
                    "sync_level": app.get("syncLevel"),
                    "implementation": app.get("implementation"),
                    "config_contract": app.get("configContract"),
                }
                for app in apps
            ]
        except Exception as e:
            self.logger.error(f"Failed to get applications: {e}")
            return []

    async def get_statistics(self) -> Dict[str, Any]:
        """Get Prowlarr statistics."""
        try:
            indexers = await self.get_indexers()
            stats = await self.get_indexer_stats()
            apps = await self.get_applications()

            enabled_indexers = sum(1 for i in indexers if i.get("enable"))
            total_queries = sum(s.get("number_of_queries", 0) for s in stats)
            total_grabs = sum(s.get("number_of_grabs", 0) for s in stats)
            total_failures = sum(s.get("number_of_failures", 0) for s in stats)

            return {
                "total_indexers": len(indexers),
                "enabled_indexers": enabled_indexers,
                "connected_apps": len(apps),
                "total_queries": total_queries,
                "total_grabs": total_grabs,
                "total_failures": total_failures,
                "success_rate": round((total_queries - total_failures) / total_queries * 100, 2)
                if total_queries > 0
                else 100,
            }
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                "total_indexers": 0,
                "enabled_indexers": 0,
                "connected_apps": 0,
                "total_queries": 0,
                "total_grabs": 0,
                "total_failures": 0,
                "success_rate": 0,
            }

    async def test_indexer(self, indexer_id: int) -> Dict[str, Any]:
        """Test a specific indexer by ID."""
        try:
            # First get the indexer config
            response = await self._make_request("GET", f"/api/v1/indexer/{indexer_id}")
            indexer_config = response.json()
            indexer_name = indexer_config.get("name", f"Indexer {indexer_id}")

            # Then test it
            await self._make_request("POST", "/api/v1/indexer/test", json=indexer_config, timeout=60.0)

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
