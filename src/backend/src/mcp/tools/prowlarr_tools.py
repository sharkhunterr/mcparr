"""MCP tools for Prowlarr integration."""

from typing import List
from .base import BaseTool, ToolDefinition, ToolParameter


class ProwlarrTools(BaseTool):
    """MCP tools for interacting with Prowlarr indexer management."""

    @property
    def definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="prowlarr_get_indexers",
                description="Get list of configured indexers in Prowlarr",
                parameters=[],
                category="indexers",
                is_mutation=False,
                requires_service="prowlarr",
            ),
            ToolDefinition(
                name="prowlarr_search",
                description="Search across all indexers in Prowlarr",
                parameters=[
                    ToolParameter(
                        name="query",
                        description="Search query",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="categories",
                        description="Category IDs to filter (comma-separated)",
                        type="string",
                        required=False,
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum number of results",
                        type="number",
                        required=False,
                        default=50,
                    ),
                ],
                category="indexers",
                is_mutation=False,
                requires_service="prowlarr",
            ),
            ToolDefinition(
                name="prowlarr_get_indexer_stats",
                description="Get indexer statistics from Prowlarr",
                parameters=[],
                category="indexers",
                is_mutation=False,
                requires_service="prowlarr",
            ),
            ToolDefinition(
                name="prowlarr_get_applications",
                description="Get list of connected applications (Radarr, Sonarr, etc.)",
                parameters=[],
                category="indexers",
                is_mutation=False,
                requires_service="prowlarr",
            ),
            ToolDefinition(
                name="prowlarr_get_statistics",
                description="Get Prowlarr overall statistics",
                parameters=[],
                category="indexers",
                is_mutation=False,
                requires_service="prowlarr",
            ),
            ToolDefinition(
                name="prowlarr_test_indexer",
                description="Test a specific indexer in Prowlarr by ID",
                parameters=[
                    ToolParameter(
                        name="indexer_id",
                        description="ID of the indexer to test",
                        type="number",
                        required=True,
                    ),
                ],
                category="indexers",
                is_mutation=False,
                requires_service="prowlarr",
            ),
            ToolDefinition(
                name="prowlarr_test_all_indexers",
                description="Test all enabled indexers in Prowlarr",
                parameters=[],
                category="indexers",
                is_mutation=False,
                requires_service="prowlarr",
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute a Prowlarr tool."""
        if not self.service_config:
            return {
                "success": False,
                "error": "Prowlarr service not configured"
            }

        try:
            from src.adapters.prowlarr import ProwlarrAdapter

            class ServiceConfigProxy:
                def __init__(self, config: dict):
                    self._config = config
                    self.api_key = config.get("api_key")
                    # Support both 'base_url' and 'url' keys for compatibility
                    self.base_url = config.get("base_url") or config.get("url", "")
                    self.port = config.get("port")
                    self.config = config.get("config") or config.get("extra_config", {})

                def get_config_value(self, key: str, default=None):
                    return self.config.get(key, default)

            service_proxy = ServiceConfigProxy(self.service_config)
            adapter = ProwlarrAdapter(service_proxy)

            if tool_name == "prowlarr_get_indexers":
                return await self._get_indexers(adapter)
            elif tool_name == "prowlarr_search":
                return await self._search(adapter, arguments)
            elif tool_name == "prowlarr_get_indexer_stats":
                return await self._get_indexer_stats(adapter)
            elif tool_name == "prowlarr_get_applications":
                return await self._get_applications(adapter)
            elif tool_name == "prowlarr_get_statistics":
                return await self._get_statistics(adapter)
            elif tool_name == "prowlarr_test_indexer":
                return await self._test_indexer(adapter, arguments)
            elif tool_name == "prowlarr_test_all_indexers":
                return await self._test_all_indexers(adapter)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    async def _get_indexers(self, adapter) -> dict:
        """Get indexers from Prowlarr."""
        indexers = await adapter.get_indexers()

        return {
            "success": True,
            "result": {
                "count": len(indexers),
                "indexers": indexers
            }
        }

    async def _search(self, adapter, arguments: dict) -> dict:
        """Search across indexers."""
        query = arguments.get("query")
        categories_str = arguments.get("categories")
        limit = arguments.get("limit", 50)

        categories = None
        if categories_str:
            categories = [int(c.strip()) for c in categories_str.split(",")]

        results = await adapter.search(query, categories=categories, limit=limit)

        return {
            "success": True,
            "result": {
                "query": query,
                "count": len(results),
                "results": results
            }
        }

    async def _get_indexer_stats(self, adapter) -> dict:
        """Get indexer statistics."""
        stats = await adapter.get_indexer_stats()

        return {
            "success": True,
            "result": stats
        }

    async def _get_applications(self, adapter) -> dict:
        """Get connected applications."""
        apps = await adapter.get_applications()

        return {
            "success": True,
            "result": {
                "count": len(apps),
                "applications": apps
            }
        }

    async def _get_statistics(self, adapter) -> dict:
        """Get statistics."""
        stats = await adapter.get_statistics()

        return {
            "success": True,
            "result": stats
        }

    async def _test_indexer(self, adapter, arguments: dict) -> dict:
        """Test a specific indexer."""
        indexer_id = arguments.get("indexer_id")
        if not indexer_id:
            return {"success": False, "error": "indexer_id is required"}

        result = await adapter.test_indexer(int(indexer_id))
        return {
            "success": result.get("success", False),
            "result": result
        }

    async def _test_all_indexers(self, adapter) -> dict:
        """Test all enabled indexers."""
        result = await adapter.test_all_indexers()
        return {
            "success": True,
            "result": result
        }
