"""MCP tools for Overseerr integration."""

from typing import List
from .base import BaseTool, ToolDefinition, ToolParameter


class OverseerrTools(BaseTool):
    """MCP tools for interacting with Overseerr media request system."""

    @property
    def definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="overseerr_search_media",
                description="Search for movies or TV shows to request in Overseerr",
                parameters=[
                    ToolParameter(
                        name="query",
                        description="Search query (movie or TV show title)",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="media_type",
                        description="Type of media to search for",
                        type="string",
                        required=False,
                        enum=["movie", "tv"],
                    ),
                ],
                category="requests",
                is_mutation=False,
                requires_service="overseerr",
            ),
            ToolDefinition(
                name="overseerr_get_requests",
                description="Get list of media requests with their status",
                parameters=[
                    ToolParameter(
                        name="status",
                        description="Filter by request status",
                        type="string",
                        required=False,
                        enum=["pending", "approved", "declined", "available", "processing"],
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum number of requests to return",
                        type="number",
                        required=False,
                        default=20,
                    ),
                ],
                category="requests",
                is_mutation=False,
                requires_service="overseerr",
            ),
            ToolDefinition(
                name="overseerr_request_media",
                description="Request a movie or TV show to be added to the library",
                parameters=[
                    ToolParameter(
                        name="title",
                        description="Title of the movie or TV show to request",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="media_type",
                        description="Type of media",
                        type="string",
                        required=True,
                        enum=["movie", "tv"],
                    ),
                    ToolParameter(
                        name="seasons",
                        description="For TV shows, specify which seasons to request (comma-separated numbers, or 'all')",
                        type="string",
                        required=False,
                        default="all",
                    ),
                ],
                category="requests",
                is_mutation=True,
                requires_service="overseerr",
            ),
            ToolDefinition(
                name="overseerr_get_trending",
                description="Get trending movies and TV shows",
                parameters=[
                    ToolParameter(
                        name="media_type",
                        description="Type of media",
                        type="string",
                        required=False,
                        enum=["movie", "tv", "all"],
                        default="all",
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum number of items to return",
                        type="number",
                        required=False,
                        default=10,
                    ),
                ],
                category="requests",
                is_mutation=False,
                requires_service="overseerr",
            ),
            ToolDefinition(
                name="overseerr_check_availability",
                description="Check if a movie or TV show is available or already requested",
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
                category="requests",
                is_mutation=False,
                requires_service="overseerr",
            ),
            ToolDefinition(
                name="overseerr_get_users",
                description="Get list of users in Overseerr",
                parameters=[],
                category="users",
                is_mutation=False,
                requires_service="overseerr",
            ),
            ToolDefinition(
                name="overseerr_get_statistics",
                description="Get Overseerr statistics (request counts, user count, etc.)",
                parameters=[],
                category="requests",
                is_mutation=False,
                requires_service="overseerr",
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute an Overseerr tool."""
        if not self.service_config:
            return {
                "success": False,
                "error": "Overseerr service not configured"
            }

        try:
            from src.adapters.overseerr import OverseerrAdapter

            # Create a mock ServiceConfig object for the adapter
            class ServiceConfigProxy:
                def __init__(self, config: dict):
                    self._config = config
                    self.api_key = config.get("api_key")
                    # base_url can come as 'url' from tool test or 'base_url' from MCP server
                    self.base_url = config.get("base_url") or config.get("url", "")
                    self.port = config.get("port")  # Port is separate from base_url
                    self.config = config.get("config", config.get("extra_config", {}))

                def get_config_value(self, key: str, default=None):
                    return self.config.get(key, default)

            service_proxy = ServiceConfigProxy(self.service_config)
            adapter = OverseerrAdapter(service_proxy)

            if tool_name == "overseerr_search_media":
                return await self._search_media(adapter, arguments)
            elif tool_name == "overseerr_get_requests":
                return await self._get_requests(adapter, arguments)
            elif tool_name == "overseerr_request_media":
                return await self._request_media(adapter, arguments)
            elif tool_name == "overseerr_get_trending":
                return await self._get_trending(adapter, arguments)
            elif tool_name == "overseerr_check_availability":
                return await self._check_availability(adapter, arguments)
            elif tool_name == "overseerr_get_users":
                return await self._get_users(adapter)
            elif tool_name == "overseerr_get_statistics":
                return await self._get_statistics(adapter)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    async def _search_media(self, adapter, arguments: dict) -> dict:
        """Search for media in Overseerr."""
        from src.adapters.overseerr import MediaType

        query = arguments.get("query")
        media_type_str = arguments.get("media_type")

        # Convert string to MediaType enum if provided
        media_type = None
        if media_type_str:
            media_type = MediaType.MOVIE if media_type_str == "movie" else MediaType.TV

        results = await adapter.search_media(query, media_type=media_type)

        return {
            "success": True,
            "result": {
                "query": query,
                "count": len(results),
                "items": [
                    {
                        "title": item.get("title") or item.get("name"),
                        "type": "movie" if item.get("mediaType") == "movie" else "tv",
                        "year": item.get("releaseDate", "")[:4] if item.get("releaseDate") else item.get("firstAirDate", "")[:4] if item.get("firstAirDate") else None,
                        "overview": (item.get("overview", "")[:200] + "...") if item.get("overview") and len(item.get("overview", "")) > 200 else item.get("overview"),
                        "tmdb_id": item.get("id"),
                        "status": item.get("mediaInfo", {}).get("status") if item.get("mediaInfo") else "not_requested",
                    }
                    for item in results[:10]
                ]
            }
        }

    async def _get_requests(self, adapter, arguments: dict) -> dict:
        """Get media requests."""
        status = arguments.get("status")
        limit = arguments.get("limit", 20)

        # Adapter uses 'take' parameter, not 'limit'
        # Adapter returns {"results": [...], "page_info": {...}}
        response = await adapter.get_requests(status=status, take=limit)
        requests_list = response.get("results", [])

        return {
            "success": True,
            "result": {
                "count": len(requests_list),
                "requests": [
                    {
                        "id": req.get("id"),
                        "title": req.get("media_info", {}).get("title"),
                        "type": req.get("media_type"),
                        "status": req.get("status_name"),
                        "requested_by": req.get("requested_by"),
                        "requested_at": req.get("created_at"),
                    }
                    for req in requests_list
                ]
            }
        }

    async def _request_media(self, adapter, arguments: dict) -> dict:
        """Request new media."""
        from src.adapters.overseerr import MediaType

        title = arguments.get("title")
        media_type_str = arguments.get("media_type")
        seasons = arguments.get("seasons", "all")

        # Convert string to MediaType enum
        media_type = MediaType.MOVIE if media_type_str == "movie" else MediaType.TV

        # First search for the media
        results = await adapter.search_media(title, media_type=media_type)

        if not results:
            return {
                "success": False,
                "error": f"No {media_type} found with title '{title}'"
            }

        media = results[0]
        tmdb_id = media.get("id")

        # Check if already available or requested
        media_info = media.get("mediaInfo")
        if media_info:
            status = media_info.get("status")
            if status == 5:  # Available
                return {
                    "success": False,
                    "error": f"'{title}' is already available in the library"
                }
            elif status in [2, 3, 4]:  # Pending, Processing, Partially Available
                return {
                    "success": False,
                    "error": f"'{title}' has already been requested"
                }

        # Create the request
        result = await adapter.request_media(
            tmdb_id=tmdb_id,
            media_type=media_type,
            seasons=seasons if media_type == "tv" else None
        )

        return {
            "success": True,
            "result": {
                "message": f"Successfully requested '{title}'",
                "request_id": result.get("id"),
                "status": "pending",
            }
        }

    async def _get_trending(self, adapter, arguments: dict) -> dict:
        """Get trending media."""
        media_type = arguments.get("media_type", "all")
        limit = arguments.get("limit", 10)

        items = await adapter.get_trending(media_type=media_type, limit=limit)

        return {
            "success": True,
            "result": {
                "trending": [
                    {
                        "title": item.get("title") or item.get("name"),
                        "type": "movie" if item.get("mediaType") == "movie" else "tv",
                        "year": item.get("releaseDate", "")[:4] if item.get("releaseDate") else item.get("firstAirDate", "")[:4] if item.get("firstAirDate") else None,
                        "overview": (item.get("overview", "")[:150] + "...") if item.get("overview") and len(item.get("overview", "")) > 150 else item.get("overview"),
                        "available": item.get("mediaInfo", {}).get("status") == 5 if item.get("mediaInfo") else False,
                    }
                    for item in items
                ]
            }
        }

    async def _check_availability(self, adapter, arguments: dict) -> dict:
        """Check media availability."""
        title = arguments.get("title")
        year = arguments.get("year")

        results = await adapter.search_media(title)

        # Filter by year if provided
        if year:
            filtered = []
            for item in results:
                item_year = item.get("releaseDate", "")[:4] if item.get("releaseDate") else item.get("firstAirDate", "")[:4] if item.get("firstAirDate") else None
                if item_year and int(item_year) == year:
                    filtered.append(item)
            results = filtered or results  # Fall back to unfiltered if no year match

        if not results:
            return {
                "success": True,
                "result": {
                    "found": False,
                    "message": f"No media found with title '{title}'"
                }
            }

        media = results[0]
        media_info = media.get("mediaInfo")

        status_map = {
            1: "unknown",
            2: "pending",
            3: "processing",
            4: "partially_available",
            5: "available",
        }

        status = "not_requested"
        if media_info:
            status = status_map.get(media_info.get("status", 1), "unknown")

        return {
            "success": True,
            "result": {
                "found": True,
                "title": media.get("title") or media.get("name"),
                "type": "movie" if media.get("mediaType") == "movie" else "tv",
                "year": media.get("releaseDate", "")[:4] if media.get("releaseDate") else media.get("firstAirDate", "")[:4] if media.get("firstAirDate") else None,
                "status": status,
                "available": status == "available",
                "can_request": status == "not_requested",
            }
        }

    async def _get_users(self, adapter) -> dict:
        """Get Overseerr users."""
        users = await adapter.get_users()

        return {
            "success": True,
            "result": {
                "count": len(users),
                "users": [
                    {
                        "id": user.get("id"),
                        "display_name": user.get("display_name"),
                        "email": user.get("email"),
                        "user_type": user.get("user_type"),
                        "request_count": user.get("request_count", 0),
                        "created_at": user.get("created_at"),
                    }
                    for user in users
                ]
            }
        }

    async def _get_statistics(self, adapter) -> dict:
        """Get Overseerr statistics."""
        stats = await adapter.get_statistics()

        return {
            "success": True,
            "result": {
                "total_requests": stats.get("total_requests", 0),
                "pending_requests": stats.get("pending_requests", 0),
                "approved_requests": stats.get("approved_requests", 0),
                "available_requests": stats.get("available_requests", 0),
                "declined_requests": stats.get("declined_requests", 0),
                "total_users": stats.get("total_users", 0),
            }
        }
