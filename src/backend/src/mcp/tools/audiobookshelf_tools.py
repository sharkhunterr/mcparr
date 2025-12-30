"""MCP tools for Audiobookshelf integration."""

from typing import List
from .base import BaseTool, ToolDefinition, ToolParameter


class AudiobookshelfTools(BaseTool):
    """MCP tools for interacting with Audiobookshelf audiobook/podcast server."""

    @property
    def definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="audiobookshelf_get_libraries",
                description="Get list of libraries in Audiobookshelf (audiobooks and podcasts)",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="audiobookshelf",
            ),
            ToolDefinition(
                name="audiobookshelf_get_library_items",
                description="Get items (audiobooks/podcasts) from a library",
                parameters=[
                    ToolParameter(
                        name="library_id",
                        description="Library ID to get items from",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum number of items to return",
                        type="number",
                        required=False,
                        default=50,
                    ),
                    ToolParameter(
                        name="page",
                        description="Page number (0-indexed)",
                        type="number",
                        required=False,
                        default=0,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="audiobookshelf",
            ),
            ToolDefinition(
                name="audiobookshelf_get_item",
                description="Get detailed information about a specific audiobook or podcast",
                parameters=[
                    ToolParameter(
                        name="item_id",
                        description="ID of the audiobook/podcast to get",
                        type="string",
                        required=True,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="audiobookshelf",
            ),
            ToolDefinition(
                name="audiobookshelf_search",
                description="Search for audiobooks, podcasts, authors, or series in a library",
                parameters=[
                    ToolParameter(
                        name="library_id",
                        description="Library ID to search in",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="query",
                        description="Search query",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum number of results per category",
                        type="number",
                        required=False,
                        default=25,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="audiobookshelf",
            ),
            ToolDefinition(
                name="audiobookshelf_get_users",
                description="Get list of users in Audiobookshelf (admin only)",
                parameters=[],
                category="users",
                is_mutation=False,
                requires_service="audiobookshelf",
            ),
            ToolDefinition(
                name="audiobookshelf_get_listening_stats",
                description="Get listening statistics for current user or specified user",
                parameters=[
                    ToolParameter(
                        name="user_id",
                        description="User ID to get stats for (optional, defaults to current user)",
                        type="string",
                        required=False,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="audiobookshelf",
            ),
            ToolDefinition(
                name="audiobookshelf_get_media_progress",
                description="Get progress for a specific audiobook/podcast",
                parameters=[
                    ToolParameter(
                        name="library_item_id",
                        description="ID of the library item",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="episode_id",
                        description="Episode ID for podcasts (optional)",
                        type="string",
                        required=False,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="audiobookshelf",
            ),
            ToolDefinition(
                name="audiobookshelf_get_statistics",
                description="Get Audiobookshelf library statistics",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="audiobookshelf",
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute an Audiobookshelf tool."""
        if not self.service_config:
            return {
                "success": False,
                "error": "Audiobookshelf service not configured"
            }

        try:
            from src.adapters.audiobookshelf import AudiobookshelfAdapter

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
            adapter = AudiobookshelfAdapter(service_proxy)

            if tool_name == "audiobookshelf_get_libraries":
                return await self._get_libraries(adapter)
            elif tool_name == "audiobookshelf_get_library_items":
                return await self._get_library_items(adapter, arguments)
            elif tool_name == "audiobookshelf_get_item":
                return await self._get_item(adapter, arguments)
            elif tool_name == "audiobookshelf_search":
                return await self._search(adapter, arguments)
            elif tool_name == "audiobookshelf_get_users":
                return await self._get_users(adapter)
            elif tool_name == "audiobookshelf_get_listening_stats":
                return await self._get_listening_stats(adapter, arguments)
            elif tool_name == "audiobookshelf_get_media_progress":
                return await self._get_media_progress(adapter, arguments)
            elif tool_name == "audiobookshelf_get_statistics":
                return await self._get_statistics(adapter)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    async def _get_libraries(self, adapter) -> dict:
        """Get libraries from Audiobookshelf."""
        libraries = await adapter.get_libraries()

        return {
            "success": True,
            "result": {
                "count": len(libraries),
                "libraries": libraries
            }
        }

    async def _get_library_items(self, adapter, arguments: dict) -> dict:
        """Get library items from Audiobookshelf."""
        library_id = arguments.get("library_id")
        limit = arguments.get("limit", 50)
        page = arguments.get("page", 0)

        result = await adapter.get_library_items(
            library_id=library_id,
            limit=limit,
            page=page
        )

        return {
            "success": True,
            "result": result
        }

    async def _get_item(self, adapter, arguments: dict) -> dict:
        """Get a specific item from Audiobookshelf."""
        item_id = arguments.get("item_id")
        item = await adapter.get_item(item_id)

        if item:
            return {
                "success": True,
                "result": item
            }
        else:
            return {
                "success": False,
                "error": f"Item not found: {item_id}"
            }

    async def _search(self, adapter, arguments: dict) -> dict:
        """Search in Audiobookshelf."""
        library_id = arguments.get("library_id")
        query = arguments.get("query")
        limit = arguments.get("limit", 25)

        results = await adapter.search(library_id, query, limit=limit)

        return {
            "success": True,
            "result": {
                "query": query,
                "library_id": library_id,
                "books_count": len(results.get("book", [])),
                "podcasts_count": len(results.get("podcast", [])),
                "authors_count": len(results.get("authors", [])),
                "series_count": len(results.get("series", [])),
                "results": results
            }
        }

    async def _get_users(self, adapter) -> dict:
        """Get users from Audiobookshelf."""
        users = await adapter.get_users()

        return {
            "success": True,
            "result": {
                "count": len(users),
                "users": users
            }
        }

    async def _get_listening_stats(self, adapter, arguments: dict) -> dict:
        """Get listening statistics."""
        user_id = arguments.get("user_id")
        stats = await adapter.get_listening_stats(user_id=user_id)

        return {
            "success": True,
            "result": stats
        }

    async def _get_media_progress(self, adapter, arguments: dict) -> dict:
        """Get media progress."""
        library_item_id = arguments.get("library_item_id")
        episode_id = arguments.get("episode_id")

        progress = await adapter.get_media_progress(
            library_item_id=library_item_id,
            episode_id=episode_id
        )

        if progress:
            return {
                "success": True,
                "result": progress
            }
        else:
            return {
                "success": True,
                "result": {
                    "message": "No progress found for this item",
                    "progress": 0
                }
            }

    async def _get_statistics(self, adapter) -> dict:
        """Get statistics."""
        stats = await adapter.get_statistics()

        return {
            "success": True,
            "result": stats
        }
