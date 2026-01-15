"""MCP tools for Komga integration."""

from typing import List

from .base import BaseTool, ToolDefinition, ToolParameter


class KomgaTools(BaseTool):
    """MCP tools for interacting with Komga comic/manga/BD server (NOT for audiobooks - use Audiobookshelf instead)."""

    @property
    def definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="komga_get_libraries",
                description="Get list of comic/manga/BD libraries in Komga (NOT for audiobooks - use Audiobookshelf)",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="komga",
            ),
            ToolDefinition(
                name="komga_search",
                description=(
                    "Search for comics, manga, or BD in Komga by title (NOT for audiobooks - use audiobookshelf_search). "
                    "Returns detailed information including genres, publisher, read progress, and URLs. "
                    "Can optionally filter by library name."
                ),
                parameters=[
                    ToolParameter(
                        name="query",
                        description="Search query (searches in titles)",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="library_name",
                        description=(
                            "Library name to search in (e.g., 'Comics', 'Manga'). "
                            "Optional - if not specified, searches all libraries."
                        ),
                        type="string",
                        required=False,
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum number of results per category",
                        type="number",
                        required=False,
                        default=20,
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
                description="Get Komga comic/manga/BD library statistics (NOT for audiobooks)",
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
                    self.external_url = config.get("external_url")  # Public URL for user links
                    self.port = config.get("port")
                    self.config = config.get("config") or config.get("extra_config", {})

                def get_config_value(self, key: str, default=None):
                    return self.config.get(key, default)

            service_proxy = ServiceConfigProxy(self.service_config)
            adapter = KomgaAdapter(service_proxy)

            if tool_name == "komga_get_libraries":
                return await self._get_libraries(adapter)
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

    async def _resolve_library_id(self, adapter, library_name: str = None) -> tuple:
        """Resolve library name to library ID.

        Returns (library_id, library_name) tuple or (None, None) if no filter.
        """
        if not library_name:
            return None, None

        libraries = await adapter.get_libraries()
        if not libraries:
            raise ValueError("No libraries found in Komga")

        # Case-insensitive match
        library = next((lib for lib in libraries if lib.get("name", "").lower() == library_name.lower()), None)
        if not library:
            available = ", ".join(lib.get("name", "") for lib in libraries)
            raise ValueError(f"Library '{library_name}' not found. Available libraries: {available}")
        return library["id"], library["name"]

    async def _search(self, adapter, arguments: dict) -> dict:
        """Search in Komga."""
        query = arguments.get("query")
        library_name = arguments.get("library_name")
        limit = arguments.get("limit", 20)

        library_id, resolved_name = await self._resolve_library_id(adapter, library_name)
        results = await adapter.search(query, library_id=library_id, limit=limit)

        result = {
            "success": True,
            "result": {
                "query": query,
                "series_count": len(results.get("series", [])),
                "books_count": len(results.get("books", [])),
                "results": results,
            },
        }
        if resolved_name:
            result["result"]["library_name"] = resolved_name

        return result

    async def _get_users(self, adapter) -> dict:
        """Get users from Komga."""
        users = await adapter.get_users()

        return {"success": True, "result": {"count": len(users), "users": users}}

    async def _get_statistics(self, adapter) -> dict:
        """Get statistics."""
        stats = await adapter.get_statistics()

        return {"success": True, "result": stats}
