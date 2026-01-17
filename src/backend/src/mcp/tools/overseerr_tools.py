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
                    ToolParameter(
                        name="limit",
                        description="Maximum number of results to return",
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
                name="overseerr_get_requests",
                description="Get list of media requests with their status. Can filter by status, user, and sort order.",
                parameters=[
                    ToolParameter(
                        name="status",
                        description="Filter by request status",
                        type="string",
                        required=False,
                        enum=["pending", "approved", "declined", "available", "processing"],
                    ),
                    ToolParameter(
                        name="user_id",
                        description="Filter by user ID (get from overseerr_get_users)",
                        type="number",
                        required=False,
                    ),
                    ToolParameter(
                        name="sort",
                        description="Sort order",
                        type="string",
                        required=False,
                        enum=["added", "modified"],
                        default="added",
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
                        description=(
                            "For TV shows, specify which seasons to request " "(comma-separated numbers, or 'all')"
                        ),
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
            ToolDefinition(
                name="overseerr_approve_request",
                description="Approve a media request. The media will be sent to Radarr/Sonarr for download.",
                parameters=[
                    ToolParameter(
                        name="request_id",
                        description="ID of the request to approve (get from overseerr_get_requests)",
                        type="number",
                        required=True,
                    ),
                ],
                category="requests",
                is_mutation=True,
                requires_service="overseerr",
            ),
            ToolDefinition(
                name="overseerr_decline_request",
                description="Decline/reject a media request with an optional reason.",
                parameters=[
                    ToolParameter(
                        name="request_id",
                        description="ID of the request to decline (get from overseerr_get_requests)",
                        type="number",
                        required=True,
                    ),
                    ToolParameter(
                        name="reason",
                        description="Optional reason for declining the request",
                        type="string",
                        required=False,
                    ),
                ],
                category="requests",
                is_mutation=True,
                requires_service="overseerr",
            ),
            ToolDefinition(
                name="overseerr_delete_request",
                description="Delete a media request completely.",
                parameters=[
                    ToolParameter(
                        name="request_id",
                        description="ID of the request to delete (get from overseerr_get_requests)",
                        type="number",
                        required=True,
                    ),
                ],
                category="requests",
                is_mutation=True,
                requires_service="overseerr",
            ),
            ToolDefinition(
                name="overseerr_get_issues",
                description="Get list of issues/problems reported by users for media items.",
                parameters=[
                    ToolParameter(
                        name="status",
                        description="Filter by issue status",
                        type="string",
                        required=False,
                        enum=["open", "resolved"],
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum number of issues to return",
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
                name="overseerr_update_issue",
                description="Update issue status (resolve or reopen) and optionally add a comment.",
                parameters=[
                    ToolParameter(
                        name="issue_id",
                        description="ID of the issue to update",
                        type="number",
                        required=True,
                    ),
                    ToolParameter(
                        name="status",
                        description="New status for the issue",
                        type="string",
                        required=False,
                        enum=["open", "resolved"],
                    ),
                    ToolParameter(
                        name="comment",
                        description="Optional comment to add to the issue",
                        type="string",
                        required=False,
                    ),
                ],
                category="requests",
                is_mutation=True,
                requires_service="overseerr",
            ),
            ToolDefinition(
                name="overseerr_delete_issue",
                description="Delete an issue completely.",
                parameters=[
                    ToolParameter(
                        name="issue_id",
                        description="ID of the issue to delete",
                        type="number",
                        required=True,
                    ),
                ],
                category="requests",
                is_mutation=True,
                requires_service="overseerr",
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute an Overseerr tool."""
        if not self.service_config:
            return {"success": False, "error": "Overseerr service not configured"}

        try:
            from src.adapters.overseerr import OverseerrAdapter

            # Create a mock ServiceConfig object for the adapter
            class ServiceConfigProxy:
                def __init__(self, config: dict):
                    self._config = config
                    self.api_key = config.get("api_key")
                    # base_url can come as 'url' from tool test or 'base_url' from MCP server
                    self.base_url = config.get("base_url") or config.get("url", "")
                    self.external_url = config.get("external_url")  # Public URL for user links
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
            elif tool_name == "overseerr_approve_request":
                return await self._approve_request(adapter, arguments)
            elif tool_name == "overseerr_decline_request":
                return await self._decline_request(adapter, arguments)
            elif tool_name == "overseerr_delete_request":
                return await self._delete_request(adapter, arguments)
            elif tool_name == "overseerr_get_issues":
                return await self._get_issues(adapter, arguments)
            elif tool_name == "overseerr_update_issue":
                return await self._update_issue(adapter, arguments)
            elif tool_name == "overseerr_delete_issue":
                return await self._delete_issue(adapter, arguments)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    async def _search_media(self, adapter, arguments: dict) -> dict:
        """Search for media in Overseerr."""
        from src.adapters.overseerr import MediaType

        query = arguments.get("query")
        media_type_str = arguments.get("media_type")
        limit = int(arguments.get("limit", 10))

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
                        "year": item.get("releaseDate", "")[:4]
                        if item.get("releaseDate")
                        else item.get("firstAirDate", "")[:4]
                        if item.get("firstAirDate")
                        else None,
                        "overview": (item.get("overview", "")[:200] + "...")
                        if item.get("overview") and len(item.get("overview", "")) > 200
                        else item.get("overview"),
                        "tmdb_id": item.get("id"),
                        "status": item.get("media_info", {}).get("status")
                        if item.get("media_info")
                        else "not_requested",
                        "url": adapter._get_media_url(
                            "movie" if item.get("mediaType") == "movie" else "tv", item.get("id")
                        ),
                    }
                    for item in results[:limit]
                ],
            },
        }

    async def _get_requests(self, adapter, arguments: dict) -> dict:
        """Get media requests."""
        status = arguments.get("status")
        user_id = arguments.get("user_id")
        sort = arguments.get("sort", "added")
        limit = arguments.get("limit", 20)

        # Adapter uses 'take' parameter, not 'limit'
        # Adapter returns {"results": [...], "page_info": {...}}
        response = await adapter.get_requests(
            status=status,
            take=limit,
            user_id=int(user_id) if user_id else None,
            sort=sort,
        )
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
                        "url": req.get("url"),
                        "media_url": req.get("media_url"),
                    }
                    for req in requests_list
                ],
            },
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
            return {"success": False, "error": f"No {media_type} found with title '{title}'"}

        media = results[0]
        tmdb_id = media.get("id")

        # Check if already available or requested
        media_info = media.get("media_info")
        if media_info:
            status = media_info.get("status")
            if status == 5:  # Available
                return {"success": False, "error": f"'{title}' is already available in the library"}
            elif status in [2, 3, 4]:  # Pending, Processing, Partially Available
                return {"success": False, "error": f"'{title}' has already been requested"}

        # Create the request
        result = await adapter.request_media(
            tmdb_id=tmdb_id, media_type=media_type, seasons=seasons if media_type == "tv" else None
        )

        return {
            "success": True,
            "result": {
                "message": f"Successfully requested '{title}'",
                "request_id": result.get("id"),
                "status": "pending",
            },
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
                        "year": item.get("releaseDate", "")[:4]
                        if item.get("releaseDate")
                        else item.get("firstAirDate", "")[:4]
                        if item.get("firstAirDate")
                        else None,
                        "overview": (item.get("overview", "")[:150] + "...")
                        if item.get("overview") and len(item.get("overview", "")) > 150
                        else item.get("overview"),
                        "tmdb_id": item.get("id"),
                        "available": item.get("media_info", {}).get("status") == 5 if item.get("media_info") else False,
                        "url": adapter._get_media_url(
                            "movie" if item.get("mediaType") == "movie" else "tv", item.get("id")
                        ),
                    }
                    for item in items
                ]
            },
        }

    async def _check_availability(self, adapter, arguments: dict) -> dict:
        """Check media availability."""
        title = arguments.get("title")
        year = arguments.get("year")

        results = await adapter.search_media(title)

        if not results:
            return {"success": True, "result": {"found": False, "message": f"No media found with title '{title}'"}}

        # Helper to extract year from item
        def get_item_year(item):
            release = item.get("releaseDate") or item.get("release_date") or ""
            first_air = item.get("firstAirDate") or item.get("first_air_date") or ""
            year_str = release[:4] if release else first_air[:4] if first_air else None
            try:
                return int(year_str) if year_str else None
            except (ValueError, TypeError):
                return None

        # Score and sort results for best match
        def score_result(item):
            score = 0
            item_title = (item.get("title") or item.get("name") or "").lower()
            search_title = title.lower()

            # Exact title match gets highest score
            if item_title == search_title:
                score += 100
            elif search_title in item_title:
                score += 50

            # Year match if provided
            if year:
                item_year = get_item_year(item)
                if item_year == year:
                    score += 80
                elif item_year and abs(item_year - year) <= 1:
                    score += 30  # Close year match

            # Prefer movies over TV for exact title matches (movies often have same name as TV)
            if item.get("mediaType") == "movie":
                score += 5

            return score

        # Sort by score descending
        sorted_results = sorted(results, key=score_result, reverse=True)
        media = sorted_results[0]

        media_info = media.get("media_info")

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

        # Get the actual media type from the result
        media_type = media.get("mediaType") or media.get("media_type")
        is_movie = media_type == "movie"

        # Get year properly
        result_year = get_item_year(media)

        return {
            "success": True,
            "result": {
                "found": True,
                "title": media.get("title") or media.get("name"),
                "type": "movie" if is_movie else "tv",
                "year": result_year,
                "tmdb_id": media.get("id"),
                "status": status,
                "available": status == "available",
                "can_request": status == "not_requested",
                "url": adapter._get_media_url("movie" if is_movie else "tv", media.get("id")),
            },
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
                ],
            },
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
            },
        }

    async def _approve_request(self, adapter, arguments: dict) -> dict:
        """Approve a media request."""
        request_id = arguments.get("request_id")

        if not request_id:
            return {"success": False, "error": "request_id is required"}

        result = await adapter.approve_request_detailed(int(request_id))

        if result.get("error") and not result.get("success"):
            return {"success": False, "error": result.get("error")}

        return {"success": True, "result": result}

    async def _decline_request(self, adapter, arguments: dict) -> dict:
        """Decline a media request."""
        request_id = arguments.get("request_id")
        reason = arguments.get("reason")

        if not request_id:
            return {"success": False, "error": "request_id is required"}

        result = await adapter.decline_request_detailed(int(request_id), reason=reason)

        if result.get("error") and not result.get("success"):
            return {"success": False, "error": result.get("error")}

        return {"success": True, "result": result}

    async def _delete_request(self, adapter, arguments: dict) -> dict:
        """Delete a media request."""
        request_id = arguments.get("request_id")

        if not request_id:
            return {"success": False, "error": "request_id is required"}

        result = await adapter.delete_request(int(request_id))

        if result.get("error") and not result.get("success"):
            return {"success": False, "error": result.get("error")}

        return {"success": True, "result": result}

    async def _get_issues(self, adapter, arguments: dict) -> dict:
        """Get issues list."""
        status = arguments.get("status")
        limit = arguments.get("limit", 20)

        response = await adapter.get_issues(take=limit, status=status)
        issues_list = response.get("results", [])

        return {
            "success": True,
            "result": {
                "count": len(issues_list),
                "issues": [
                    {
                        "id": issue.get("id"),
                        "title": issue.get("media_info", {}).get("title"),
                        "media_type": issue.get("media_info", {}).get("media_type"),
                        "issue_type": issue.get("issue_type"),
                        "status": issue.get("status"),
                        "message": issue.get("message"),
                        "created_by": issue.get("created_by"),
                        "created_at": issue.get("created_at"),
                        "problem_season": issue.get("problem_season"),
                        "problem_episode": issue.get("problem_episode"),
                        "url": issue.get("url"),
                    }
                    for issue in issues_list
                ],
            },
        }

    async def _update_issue(self, adapter, arguments: dict) -> dict:
        """Update issue status and/or add comment."""
        issue_id = arguments.get("issue_id")
        status = arguments.get("status")
        comment = arguments.get("comment")

        if not issue_id:
            return {"success": False, "error": "issue_id is required"}

        results = []

        # Add comment if provided
        if comment:
            comment_result = await adapter.add_issue_comment(int(issue_id), comment)
            if comment_result.get("error") and not comment_result.get("success"):
                return {"success": False, "error": comment_result.get("error")}
            results.append("Comment added")

        # Update status if provided
        if status:
            status_result = await adapter.update_issue_status(int(issue_id), status)
            if status_result.get("error") and not status_result.get("success"):
                return {"success": False, "error": status_result.get("error")}
            results.append(f"Status updated to {status}")

        if not results:
            return {"success": False, "error": "Either status or comment is required"}

        return {
            "success": True,
            "result": {
                "issue_id": issue_id,
                "actions": results,
                "message": " and ".join(results),
            },
        }

    async def _delete_issue(self, adapter, arguments: dict) -> dict:
        """Delete an issue."""
        issue_id = arguments.get("issue_id")

        if not issue_id:
            return {"success": False, "error": "issue_id is required"}

        result = await adapter.delete_issue(int(issue_id))

        if result.get("error") and not result.get("success"):
            return {"success": False, "error": result.get("error")}

        return {"success": True, "result": result}
