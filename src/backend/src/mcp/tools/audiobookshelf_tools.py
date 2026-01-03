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
                description=(
                    "Get items (audiobooks/podcasts) from a library. "
                    "If no library specified, uses the first available library."
                ),
                parameters=[
                    ToolParameter(
                        name="library_name",
                        description=(
                            "Library name to get items from (e.g., 'Audiobooks', 'Podcasts'). "
                            "Optional - if not specified, uses the first library."
                        ),
                        type="string",
                        required=False,
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
                name="audiobookshelf_search",
                description=(
                    "Search for audiobooks, podcasts, authors, or series in a library. "
                    "Returns detailed information including description, narrator, series, "
                    "duration, genres, etc. If no library specified, uses the first library."
                ),
                parameters=[
                    ToolParameter(
                        name="query",
                        description="Search query",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="library_name",
                        description=(
                            "Library name to search in (e.g., 'Audiobooks', 'Podcasts'). "
                            "Optional - if not specified, uses the first library."
                        ),
                        type="string",
                        required=False,
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
                description="Get listening progress for a specific audiobook or podcast by title",
                parameters=[
                    ToolParameter(
                        name="title",
                        description="Title of the audiobook/podcast",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="library_name",
                        description=(
                            "Library name to search in (e.g., 'Audiobooks', 'Podcasts'). "
                            "Optional - if not specified, searches all libraries."
                        ),
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
            return {"success": False, "error": "Audiobookshelf service not configured"}

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
                    self.external_url = config.get("external_url")  # Public URL for user links
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

        return {"success": True, "result": {"count": len(libraries), "libraries": libraries}}

    async def _resolve_library_id(self, adapter, library_name: str = None) -> tuple[str, str]:
        """Resolve library name to library ID.

        Returns (library_id, library_name) tuple.
        If library_name not specified, returns the first library.
        """
        libraries = await adapter.get_libraries()
        if not libraries:
            raise ValueError("No libraries found in Audiobookshelf")

        if library_name:
            # Case-insensitive match
            library = next(
                (lib for lib in libraries if lib.get("name", "").lower() == library_name.lower()),
                None
            )
            if not library:
                available = ", ".join(lib.get("name", "") for lib in libraries)
                raise ValueError(f"Library '{library_name}' not found. Available libraries: {available}")
            return library["id"], library["name"]
        else:
            # Use first library
            return libraries[0]["id"], libraries[0]["name"]

    async def _get_library_items(self, adapter, arguments: dict) -> dict:
        """Get library items from Audiobookshelf."""
        library_name = arguments.get("library_name")
        limit = arguments.get("limit", 50)
        page = arguments.get("page", 0)

        library_id, resolved_name = await self._resolve_library_id(adapter, library_name)
        result = await adapter.get_library_items(library_id=library_id, limit=limit, page=page)
        result["library_name"] = resolved_name

        return {"success": True, "result": result}

    async def _find_item_by_title(self, adapter, title: str, library_name: str = None) -> tuple[dict, str]:
        """Find an item by title, searching in specified library or all libraries.

        Returns (item, library_name) tuple.
        """
        libraries = await adapter.get_libraries()
        if not libraries:
            raise ValueError("No libraries found in Audiobookshelf")

        # If library specified, search only in that library
        if library_name:
            library = next(
                (lib for lib in libraries if lib.get("name", "").lower() == library_name.lower()),
                None
            )
            if not library:
                available = ", ".join(lib.get("name", "") for lib in libraries)
                raise ValueError(f"Library '{library_name}' not found. Available libraries: {available}")
            libraries_to_search = [library]
        else:
            libraries_to_search = libraries

        # Search in each library
        for lib in libraries_to_search:
            results = await adapter.search(lib["id"], title, limit=10)

            # Check books
            for book in results.get("book", []):
                book_title = book.get("title", "").lower()
                if title.lower() in book_title or book_title in title.lower():
                    item = await adapter.get_item(book["id"])
                    if item:
                        item["url"] = adapter._get_item_url(book["id"])
                        return item, lib["name"]

            # Check podcasts
            for podcast in results.get("podcast", []):
                podcast_title = podcast.get("title", "").lower()
                if title.lower() in podcast_title or podcast_title in title.lower():
                    item = await adapter.get_item(podcast["id"])
                    if item:
                        item["url"] = adapter._get_item_url(podcast["id"])
                        return item, lib["name"]

        raise ValueError(f"No item found with title '{title}'")

    async def _search(self, adapter, arguments: dict) -> dict:
        """Search in Audiobookshelf."""
        query = arguments.get("query")
        library_name = arguments.get("library_name")
        limit = arguments.get("limit", 25)

        library_id, resolved_name = await self._resolve_library_id(adapter, library_name)
        results = await adapter.search(library_id, query, limit=limit)

        return {
            "success": True,
            "result": {
                "query": query,
                "library_name": resolved_name,
                "books_count": len(results.get("book", [])),
                "podcasts_count": len(results.get("podcast", [])),
                "authors_count": len(results.get("authors", [])),
                "series_count": len(results.get("series", [])),
                "results": results,
            },
        }

    async def _get_users(self, adapter) -> dict:
        """Get users from Audiobookshelf."""
        users = await adapter.get_users()

        return {"success": True, "result": {"count": len(users), "users": users}}

    async def _get_listening_stats(self, adapter, arguments: dict) -> dict:
        """Get listening statistics."""
        user_id = arguments.get("user_id")
        stats = await adapter.get_listening_stats(user_id=user_id)

        return {"success": True, "result": stats}

    async def _get_media_progress(self, adapter, arguments: dict) -> dict:
        """Get media progress by title."""
        title = arguments.get("title")
        library_name = arguments.get("library_name")

        if not title:
            return {"success": False, "error": "title is required"}

        # Find the item first
        item, found_library = await self._find_item_by_title(adapter, title, library_name)
        item_id = item.get("id")

        progress = await adapter.get_media_progress(library_item_id=item_id)

        if progress:
            progress["title"] = item.get("title")
            progress["library_name"] = found_library
            return {"success": True, "result": progress}
        else:
            return {
                "success": True,
                "result": {
                    "title": item.get("title"),
                    "library_name": found_library,
                    "message": "No progress found for this item",
                    "progress": 0,
                },
            }

    async def _get_statistics(self, adapter) -> dict:
        """Get statistics."""
        stats = await adapter.get_statistics()

        return {"success": True, "result": stats}
