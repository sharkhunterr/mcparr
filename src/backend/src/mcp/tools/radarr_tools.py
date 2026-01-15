"""MCP tools for Radarr integration."""

from typing import List

from .base import BaseTool, ToolDefinition, ToolParameter


class RadarrTools(BaseTool):
    """MCP tools for interacting with Radarr movie management."""

    @property
    def definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="radarr_search_movie",
                description="Search for a movie to add to Radarr",
                parameters=[
                    ToolParameter(
                        name="query",
                        description="Movie title to search for",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum number of results to return",
                        type="number",
                        required=False,
                        default=10,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="radarr",
            ),
            ToolDefinition(
                name="radarr_get_movie_status",
                description="Get detailed status of a specific movie in Radarr library (monitored, has file, quality profile, etc.)",
                parameters=[
                    ToolParameter(
                        name="title",
                        description="Movie title to search for in Radarr library",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="year",
                        description="Release year (helps with disambiguation)",
                        type="number",
                        required=False,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="radarr",
            ),
            ToolDefinition(
                name="radarr_get_queue",
                description="Get current download queue in Radarr",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="radarr",
            ),
            ToolDefinition(
                name="radarr_get_calendar",
                description="Get upcoming movie releases from Radarr calendar",
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
                requires_service="radarr",
            ),
            ToolDefinition(
                name="radarr_get_statistics",
                description="Get Radarr library statistics",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="radarr",
            ),
            ToolDefinition(
                name="radarr_get_indexers",
                description="Get list of configured indexers in Radarr",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="radarr",
            ),
            ToolDefinition(
                name="radarr_test_indexer",
                description="Test a specific indexer in Radarr by ID",
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
                requires_service="radarr",
            ),
            ToolDefinition(
                name="radarr_test_all_indexers",
                description="Test all enabled indexers in Radarr",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="radarr",
            ),
            ToolDefinition(
                name="radarr_get_releases",
                description="Get available releases/torrents for a movie (manual search). Shows quality, language, seeders, size, and whether the release matches the profile.",
                parameters=[
                    ToolParameter(
                        name="movie_id",
                        description="Radarr movie ID (get from radarr_get_movie_status or radarr_search_movie)",
                        type="number",
                        required=True,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="radarr",
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute a Radarr tool."""
        if not self.service_config:
            return {"success": False, "error": "Radarr service not configured"}

        try:
            from src.adapters.radarr import RadarrAdapter

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
            adapter = RadarrAdapter(service_proxy)

            if tool_name == "radarr_search_movie":
                return await self._search_movie(adapter, arguments)
            elif tool_name == "radarr_get_movie_status":
                return await self._get_movie_status(adapter, arguments)
            elif tool_name == "radarr_get_queue":
                return await self._get_queue(adapter)
            elif tool_name == "radarr_get_calendar":
                return await self._get_calendar(adapter, arguments)
            elif tool_name == "radarr_get_statistics":
                return await self._get_statistics(adapter)
            elif tool_name == "radarr_get_indexers":
                return await self._get_indexers(adapter)
            elif tool_name == "radarr_test_indexer":
                return await self._test_indexer(adapter, arguments)
            elif tool_name == "radarr_test_all_indexers":
                return await self._test_all_indexers(adapter)
            elif tool_name == "radarr_get_releases":
                return await self._get_releases(adapter, arguments)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    async def _search_movie(self, adapter, arguments: dict) -> dict:
        """Search for a movie."""
        query = arguments.get("query")
        limit = int(arguments.get("limit", 10))
        results = await adapter.search_movie(query)

        return {"success": True, "result": {"query": query, "count": len(results), "results": results[:limit]}}

    async def _get_movie_status(self, adapter, arguments: dict) -> dict:
        """Get detailed status of a movie in Radarr library."""
        title = arguments.get("title")
        year = arguments.get("year")

        result = await adapter.get_movie_by_title(title, year)

        if not result.get("found"):
            return {
                "success": True,
                "result": {
                    "found": False,
                    "title": title,
                    "message": result.get("message", f"Movie '{title}' not found in Radarr library"),
                },
            }

        return {"success": True, "result": result}

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

    async def _get_releases(self, adapter, arguments: dict) -> dict:
        """Get available releases/torrents for a movie (manual search)."""
        movie_id = arguments.get("movie_id")
        if not movie_id:
            return {"success": False, "error": "movie_id is required"}

        result = await adapter.get_releases(int(movie_id))

        if result.get("error"):
            return {"success": False, "error": result.get("error")}

        return {"success": True, "result": result}
