"""MCP tools for Sonarr integration."""

from typing import List

from .base import BaseTool, ToolDefinition, ToolParameter


class SonarrTools(BaseTool):
    """MCP tools for interacting with Sonarr TV series management."""

    @property
    def definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="sonarr_get_series",
                description="Get list of TV series in Sonarr library",
                parameters=[
                    ToolParameter(
                        name="limit",
                        description="Maximum number of series to return",
                        type="number",
                        required=False,
                        default=50,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_search_series",
                description="Search for a TV series to add to Sonarr",
                parameters=[
                    ToolParameter(
                        name="query",
                        description="TV series title to search for",
                        type="string",
                        required=True,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_get_queue",
                description="Get current download queue in Sonarr",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_get_calendar",
                description="Get upcoming TV episode releases from Sonarr calendar",
                parameters=[
                    ToolParameter(
                        name="days",
                        description="Number of days to look ahead",
                        type="number",
                        required=False,
                        default=7,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_get_statistics",
                description="Get Sonarr library statistics",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_get_indexers",
                description="Get list of configured indexers in Sonarr",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_test_indexer",
                description="Test a specific indexer in Sonarr by ID",
                parameters=[
                    ToolParameter(
                        name="indexer_id",
                        description="ID of the indexer to test",
                        type="number",
                        required=True,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_test_all_indexers",
                description="Test all enabled indexers in Sonarr",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="sonarr",
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute a Sonarr tool."""
        if not self.service_config:
            return {"success": False, "error": "Sonarr service not configured"}

        try:
            from src.adapters.sonarr import SonarrAdapter

            class ServiceConfigProxy:
                def __init__(self, config: dict):
                    self._config = config
                    self.api_key = config.get("api_key")
                    # Support both 'base_url' and 'url' keys for compatibility
                    self.base_url = config.get("base_url") or config.get("url", "")
                    self.external_url = config.get("external_url")  # Public URL for user links
                    self.port = config.get("port")
                    self.config = config.get("config") or config.get("extra_config", {})

                def get_config_value(self, key: str, default=None):
                    return self.config.get(key, default)

            service_proxy = ServiceConfigProxy(self.service_config)
            adapter = SonarrAdapter(service_proxy)

            if tool_name == "sonarr_get_series":
                return await self._get_series(adapter, arguments)
            elif tool_name == "sonarr_search_series":
                return await self._search_series(adapter, arguments)
            elif tool_name == "sonarr_get_queue":
                return await self._get_queue(adapter)
            elif tool_name == "sonarr_get_calendar":
                return await self._get_calendar(adapter, arguments)
            elif tool_name == "sonarr_get_statistics":
                return await self._get_statistics(adapter)
            elif tool_name == "sonarr_get_indexers":
                return await self._get_indexers(adapter)
            elif tool_name == "sonarr_test_indexer":
                return await self._test_indexer(adapter, arguments)
            elif tool_name == "sonarr_test_all_indexers":
                return await self._test_all_indexers(adapter)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    async def _get_series(self, adapter, arguments: dict) -> dict:
        """Get series from Sonarr."""
        limit = arguments.get("limit", 50)
        series = await adapter.get_series(limit=limit)

        return {"success": True, "result": {"count": len(series), "series": series}}

    async def _search_series(self, adapter, arguments: dict) -> dict:
        """Search for a series."""
        query = arguments.get("query")
        results = await adapter.search_series(query)

        return {"success": True, "result": {"query": query, "count": len(results), "results": results}}

    async def _get_queue(self, adapter) -> dict:
        """Get download queue."""
        queue = await adapter.get_queue()

        return {"success": True, "result": {"count": len(queue), "queue": queue}}

    async def _get_calendar(self, adapter, arguments: dict) -> dict:
        """Get calendar."""
        days = arguments.get("days", 7)
        calendar = await adapter.get_calendar(days=days)

        return {"success": True, "result": {"days": days, "count": len(calendar), "upcoming": calendar}}

    async def _get_statistics(self, adapter) -> dict:
        """Get statistics."""
        stats = await adapter.get_statistics()

        return {"success": True, "result": stats}

    async def _get_indexers(self, adapter) -> dict:
        """Get list of indexers."""
        indexers = await adapter.get_indexers()

        return {
            "success": True,
            "result": {
                "count": len(indexers),
                "enabled_count": sum(1 for i in indexers if i.get("enable")),
                "indexers": indexers,
            },
        }

    async def _test_indexer(self, adapter, arguments: dict) -> dict:
        """Test a specific indexer."""
        indexer_id = arguments.get("indexer_id")
        if not indexer_id:
            return {"success": False, "error": "indexer_id is required"}

        result = await adapter.test_indexer(int(indexer_id))
        return {"success": result.get("success", False), "result": result}

    async def _test_all_indexers(self, adapter) -> dict:
        """Test all enabled indexers."""
        result = await adapter.test_all_indexers()
        return {"success": True, "result": result}
