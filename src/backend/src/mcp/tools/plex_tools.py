"""MCP tools for Plex integration."""

from typing import List

from .base import BaseTool, ToolDefinition, ToolParameter


class PlexTools(BaseTool):
    """MCP tools for interacting with Plex Media Server."""

    @property
    def definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="plex_get_libraries",
                description="Get list of all Plex media libraries (Movies, TV Shows, Music, etc.)",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="plex",
            ),
            ToolDefinition(
                name="plex_search_media",
                description="Search for movies, TV shows, or other media in Plex library",
                parameters=[
                    ToolParameter(
                        name="query",
                        description="Search query (title, actor, director, etc.)",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="media_type",
                        description="Type of media to search for",
                        type="string",
                        required=False,
                        enum=["movie", "show", "episode", "artist", "album", "track"],
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
                requires_service="plex",
            ),
            ToolDefinition(
                name="plex_get_recently_added",
                description="Get recently added media to Plex library",
                parameters=[
                    ToolParameter(
                        name="library_name",
                        description="Name of the library (e.g., 'Movies', 'TV Shows'). Leave empty for all libraries.",
                        type="string",
                        required=False,
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum number of items to return",
                        type="number",
                        required=False,
                        default=10,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="plex",
            ),
            ToolDefinition(
                name="plex_get_on_deck",
                description="Get 'On Deck' items (continue watching) for the server",
                parameters=[
                    ToolParameter(
                        name="limit",
                        description="Maximum number of items to return",
                        type="number",
                        required=False,
                        default=10,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="plex",
            ),
            ToolDefinition(
                name="plex_get_media_details",
                description="Get detailed information about a specific movie or TV show",
                parameters=[
                    ToolParameter(
                        name="title",
                        description="Title of the movie or TV show",
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
                requires_service="plex",
            ),
            ToolDefinition(
                name="plex_get_active_sessions",
                description="Get list of currently active streaming sessions on Plex",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="plex",
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute a Plex tool."""
        if not self.service_config:
            return {"success": False, "error": "Plex service not configured"}

        try:
            # Import adapter here to avoid circular imports
            from src.adapters.plex import PlexAdapter

            # Create a mock ServiceConfig object for the adapter
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
            adapter = PlexAdapter(service_proxy)

            if tool_name == "plex_get_libraries":
                return await self._get_libraries(adapter)
            elif tool_name == "plex_search_media":
                return await self._search_media(adapter, arguments)
            elif tool_name == "plex_get_recently_added":
                return await self._get_recently_added(adapter, arguments)
            elif tool_name == "plex_get_on_deck":
                return await self._get_on_deck(adapter, arguments)
            elif tool_name == "plex_get_media_details":
                return await self._get_media_details(adapter, arguments)
            elif tool_name == "plex_get_active_sessions":
                return await self._get_active_sessions(adapter)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    async def _get_libraries(self, adapter) -> dict:
        """Get all Plex libraries."""
        libraries = await adapter.get_libraries()
        return {
            "success": True,
            "result": {
                "libraries": [
                    {
                        "name": lib.get("title"),
                        "type": lib.get("type"),
                        "key": lib.get("key"),
                        "count": lib.get("count", 0),
                        "url": lib.get("url"),
                    }
                    for lib in libraries
                ]
            },
        }

    async def _search_media(self, adapter, arguments: dict) -> dict:
        """Search for media in Plex."""
        query = arguments.get("query")
        media_type = arguments.get("media_type")
        limit = arguments.get("limit", 10)

        results = await adapter.search(query, media_type=media_type, limit=limit)

        return {
            "success": True,
            "result": {
                "query": query,
                "count": len(results),
                "items": [
                    {
                        "title": item.get("title"),
                        "type": item.get("type"),
                        "year": item.get("year"),
                        "summary": item.get("summary", "")[:200] + "..."
                        if item.get("summary") and len(item.get("summary", "")) > 200
                        else item.get("summary"),
                        "rating": item.get("rating"),
                        "duration_minutes": item.get("duration", 0) // 60000 if item.get("duration") else None,
                        "url": item.get("url"),
                    }
                    for item in results[:limit]
                ],
            },
        }

    async def _get_recently_added(self, adapter, arguments: dict) -> dict:
        """Get recently added media."""
        library_name = arguments.get("library_name")
        limit = arguments.get("limit", 10)

        items = await adapter.get_recently_added(library_name=library_name, limit=limit)

        # Apply limit (adapter may return more than requested)
        items = items[:limit]

        result_items = []
        for item in items:
            item_type = item.get("type")
            title = item.get("title")
            year = item.get("year") or item.get("parentYear")  # Use parent year for seasons/episodes

            # Build descriptive title for episodes and seasons
            if item_type == "episode":
                series = item.get("grandparentTitle", "")
                season = item.get("parentIndex")
                episode = item.get("index")
                if series and season is not None and episode is not None:
                    title = f"{series} S{season:02d}E{episode:02d} - {title}"
            elif item_type == "season":
                series = item.get("parentTitle", "")
                season_num = item.get("index")
                if series and season_num is not None:
                    title = f"{series} - Season {season_num}"

            item_data = {
                "title": title,
                "type": item_type,
                "year": year,
                "added_at": item.get("addedAt"),
                "url": item.get("url"),
            }
            # Only include library if available (not present when filtering by specific library)
            lib_title = item.get("librarySectionTitle")
            if lib_title:
                item_data["library"] = lib_title

            result_items.append(item_data)

        return {
            "success": True,
            "result": {
                "count": len(result_items),
                "items": result_items,
            },
        }

    async def _get_on_deck(self, adapter, arguments: dict) -> dict:
        """Get on deck items."""
        limit = arguments.get("limit", 10)

        items = await adapter.get_on_deck(limit=limit)

        result_items = []
        for item in items:
            item_type = item.get("type")
            title = item.get("title")
            year = item.get("year") or item.get("parentYear")

            # Build descriptive title for episodes
            if item_type == "episode":
                series = item.get("grandparentTitle", "")
                season = item.get("parentIndex")
                episode = item.get("index")
                if series and season is not None and episode is not None:
                    title = f"{series} S{season:02d}E{episode:02d} - {title}"

            progress = 0
            if item.get("duration"):
                progress = round((item.get("viewOffset", 0) / item.get("duration")) * 100)

            result_items.append(
                {
                    "title": title,
                    "type": item_type,
                    "year": year,
                    "progress_percent": progress,
                    "url": item.get("url"),
                }
            )

        return {
            "success": True,
            "result": {
                "count": len(result_items),
                "items": result_items,
            },
        }

    async def _get_media_details(self, adapter, arguments: dict) -> dict:
        """Get details for a specific media item."""
        title = arguments.get("title")
        year = arguments.get("year")

        # Search for the item first
        results = await adapter.search(title, limit=5)

        # Filter by year if provided
        if year:
            results = [r for r in results if r.get("year") == year]

        if not results:
            return {
                "success": False,
                "error": f"No media found with title '{title}'" + (f" and year {year}" if year else ""),
            }

        item = results[0]

        return {
            "success": True,
            "result": {
                "title": item.get("title"),
                "type": item.get("type"),
                "year": item.get("year"),
                "summary": item.get("summary"),
                "rating": item.get("rating"),
                "content_rating": item.get("contentRating"),
                "duration_minutes": item.get("duration", 0) // 60000 if item.get("duration") else None,
                "genres": item.get("Genre", []),
                "directors": item.get("Director", []),
                "actors": item.get("Role", [])[:5],  # Limit actors
                "studio": item.get("studio"),
                "added_at": item.get("addedAt"),
                "url": item.get("url"),
            },
        }

    async def _get_active_sessions(self, adapter) -> dict:
        """Get active streaming sessions."""
        sessions = await adapter.get_sessions()

        return {
            "success": True,
            "result": {
                "active_streams": len(sessions),
                "sessions": [
                    {
                        "user": session.get("User", {}).get("title", "Unknown"),
                        "title": session.get("title"),
                        "grandparent_title": session.get("grandparentTitle"),
                        "type": session.get("type"),
                        "player": session.get("Player", {}).get("title"),
                        "state": session.get("Player", {}).get("state"),
                        "progress_percent": round((session.get("viewOffset", 0) / session.get("duration", 1)) * 100)
                        if session.get("duration")
                        else 0,
                    }
                    for session in sessions
                ],
            },
        }
