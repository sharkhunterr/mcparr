"""MCP tools for Komga integration."""

from typing import List

from .base import BaseTool, ToolDefinition, ToolParameter


class KomgaTools(BaseTool):
    """MCP tools for interacting with Komga comic/manga server."""

    @property
    def definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="komga_get_libraries",
                description="Get list of libraries in Komga",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="komga",
            ),
            ToolDefinition(
                name="komga_get_series",
                description="Get list of series (comics/manga)",
                parameters=[
                    ToolParameter(
                        name="library_id",
                        description="Filter by library ID",
                        type="string",
                        required=False,
                    ),
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
                requires_service="komga",
            ),
            ToolDefinition(
                name="komga_get_books",
                description="Get list of books (issues/chapters)",
                parameters=[
                    ToolParameter(
                        name="series_id",
                        description="Filter by series ID",
                        type="string",
                        required=False,
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum number of books to return",
                        type="number",
                        required=False,
                        default=50,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="komga",
            ),
            ToolDefinition(
                name="komga_search",
                description="Search for series and books in Komga",
                parameters=[
                    ToolParameter(
                        name="query",
                        description="Search query",
                        type="string",
                        required=True,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="komga",
            ),
            ToolDefinition(
                name="komga_get_users",
                description="Get list of users in Komga",
                parameters=[],
                category="users",
                is_mutation=False,
                requires_service="komga",
            ),
            ToolDefinition(
                name="komga_get_statistics",
                description="Get Komga library statistics",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="komga",
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute a Komga tool."""
        if not self.service_config:
            return {"success": False, "error": "Komga service not configured"}

        try:
            from src.adapters.komga import KomgaAdapter

            class ServiceConfigProxy:
                def __init__(self, config: dict):
                    self._config = config
                    self.api_key = config.get("api_key")
                    self.username = config.get("username")
                    self.password = config.get("password")
                    # Support both 'base_url' and 'url' keys for compatibility
                    self.base_url = config.get("base_url") or config.get("url", "")
                    self.port = config.get("port")
                    self.config = config.get("config") or config.get("extra_config", {})

                def get_config_value(self, key: str, default=None):
                    return self.config.get(key, default)

            service_proxy = ServiceConfigProxy(self.service_config)
            adapter = KomgaAdapter(service_proxy)

            if tool_name == "komga_get_libraries":
                return await self._get_libraries(adapter)
            elif tool_name == "komga_get_series":
                return await self._get_series(adapter, arguments)
            elif tool_name == "komga_get_books":
                return await self._get_books(adapter, arguments)
            elif tool_name == "komga_search":
                return await self._search(adapter, arguments)
            elif tool_name == "komga_get_users":
                return await self._get_users(adapter)
            elif tool_name == "komga_get_statistics":
                return await self._get_statistics(adapter)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    async def _get_libraries(self, adapter) -> dict:
        """Get libraries from Komga."""
        libraries = await adapter.get_libraries()

        return {"success": True, "result": {"count": len(libraries), "libraries": libraries}}

    async def _get_series(self, adapter, arguments: dict) -> dict:
        """Get series from Komga."""
        library_id = arguments.get("library_id")
        limit = arguments.get("limit", 50)
        series = await adapter.get_series(library_id=library_id, limit=limit)

        return {"success": True, "result": {"count": len(series), "series": series}}

    async def _get_books(self, adapter, arguments: dict) -> dict:
        """Get books from Komga."""
        series_id = arguments.get("series_id")
        limit = arguments.get("limit", 50)
        books = await adapter.get_books(series_id=series_id, limit=limit)

        return {"success": True, "result": {"count": len(books), "books": books}}

    async def _search(self, adapter, arguments: dict) -> dict:
        """Search in Komga."""
        query = arguments.get("query")
        results = await adapter.search(query)

        return {
            "success": True,
            "result": {
                "query": query,
                "series_count": len(results.get("series", [])),
                "books_count": len(results.get("books", [])),
                "results": results,
            },
        }

    async def _get_users(self, adapter) -> dict:
        """Get users from Komga."""
        users = await adapter.get_users()

        return {"success": True, "result": {"count": len(users), "users": users}}

    async def _get_statistics(self, adapter) -> dict:
        """Get statistics."""
        stats = await adapter.get_statistics()

        return {"success": True, "result": stats}
