"""MCP tools for Tautulli integration."""

from typing import List

from .base import BaseTool, ToolDefinition, ToolParameter


class TautulliTools(BaseTool):
    """MCP tools for interacting with Tautulli Plex analytics."""

    @property
    def definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="tautulli_get_activity",
                description=(
                    "Get current Plex streaming activity including active sessions, "
                    "bandwidth usage, and stream counts"
                ),
                parameters=[],
                category="monitoring",
                is_mutation=False,
                requires_service="tautulli",
            ),
            ToolDefinition(
                name="tautulli_get_history",
                description="Get play history from Tautulli with optional user filtering",
                parameters=[
                    ToolParameter(
                        name="length",
                        description="Number of history items to return",
                        type="number",
                        required=False,
                        default=25,
                    ),
                    ToolParameter(
                        name="user",
                        description="Filter history by username",
                        type="string",
                        required=False,
                    ),
                ],
                category="monitoring",
                is_mutation=False,
                requires_service="tautulli",
            ),
            ToolDefinition(
                name="tautulli_get_users",
                description="Get list of all Plex users known to Tautulli with their details and permissions",
                parameters=[],
                category="monitoring",
                is_mutation=False,
                requires_service="tautulli",
            ),
            ToolDefinition(
                name="tautulli_get_libraries",
                description="Get library statistics from Tautulli including item counts and types",
                parameters=[],
                category="monitoring",
                is_mutation=False,
                requires_service="tautulli",
            ),
            ToolDefinition(
                name="tautulli_get_statistics",
                description="Get comprehensive statistics including activity, history, users, and libraries overview",
                parameters=[],
                category="monitoring",
                is_mutation=False,
                requires_service="tautulli",
            ),
            ToolDefinition(
                name="tautulli_get_recently_added",
                description="Get recently added items to Plex libraries",
                parameters=[
                    ToolParameter(
                        name="count",
                        description="Number of recently added items to return",
                        type="number",
                        required=False,
                        default=25,
                    ),
                ],
                category="monitoring",
                is_mutation=False,
                requires_service="tautulli",
            ),
            ToolDefinition(
                name="tautulli_get_server_info",
                description="Get Tautulli and Plex server information including versions and status",
                parameters=[],
                category="monitoring",
                is_mutation=False,
                requires_service="tautulli",
            ),
            ToolDefinition(
                name="tautulli_get_top_users",
                description="Get top Plex users by play count or watch duration over a specified period",
                parameters=[
                    ToolParameter(
                        name="days",
                        description="Number of days to analyze (default: 30)",
                        type="number",
                        required=False,
                        default=30,
                    ),
                    ToolParameter(
                        name="stats_type",
                        description="Type of stats: 'plays' for play count, 'duration' for watch time",
                        type="string",
                        required=False,
                        enum=["plays", "duration"],
                        default="plays",
                    ),
                    ToolParameter(
                        name="limit",
                        description="Number of users to return (default: 10)",
                        type="number",
                        required=False,
                        default=10,
                    ),
                ],
                category="monitoring",
                is_mutation=False,
                requires_service="tautulli",
            ),
            ToolDefinition(
                name="tautulli_get_top_movies",
                description="Get top watched movies over a specified period, optionally filtered by user",
                parameters=[
                    ToolParameter(
                        name="days",
                        description="Number of days to analyze (default: 30)",
                        type="number",
                        required=False,
                        default=30,
                    ),
                    ToolParameter(
                        name="stats_type",
                        description="Type of stats: 'plays' for play count, 'duration' for watch time",
                        type="string",
                        required=False,
                        enum=["plays", "duration"],
                        default="plays",
                    ),
                    ToolParameter(
                        name="limit",
                        description="Number of movies to return (default: 10)",
                        type="number",
                        required=False,
                        default=10,
                    ),
                    ToolParameter(
                        name="username",
                        description="Filter by username (optional, if not provided shows all users)",
                        type="string",
                        required=False,
                    ),
                ],
                category="monitoring",
                is_mutation=False,
                requires_service="tautulli",
            ),
            ToolDefinition(
                name="tautulli_get_top_tv_shows",
                description="Get top watched TV shows over a specified period, optionally filtered by user",
                parameters=[
                    ToolParameter(
                        name="days",
                        description="Number of days to analyze (default: 30)",
                        type="number",
                        required=False,
                        default=30,
                    ),
                    ToolParameter(
                        name="stats_type",
                        description="Type of stats: 'plays' for play count, 'duration' for watch time",
                        type="string",
                        required=False,
                        enum=["plays", "duration"],
                        default="plays",
                    ),
                    ToolParameter(
                        name="limit",
                        description="Number of TV shows to return (default: 10)",
                        type="number",
                        required=False,
                        default=10,
                    ),
                    ToolParameter(
                        name="username",
                        description="Filter by username (optional, if not provided shows all users)",
                        type="string",
                        required=False,
                    ),
                ],
                category="monitoring",
                is_mutation=False,
                requires_service="tautulli",
            ),
            ToolDefinition(
                name="tautulli_get_top_music",
                description="Get top listened music over a specified period, optionally filtered by user",
                parameters=[
                    ToolParameter(
                        name="days",
                        description="Number of days to analyze (default: 30)",
                        type="number",
                        required=False,
                        default=30,
                    ),
                    ToolParameter(
                        name="stats_type",
                        description="Type of stats: 'plays' for play count, 'duration' for listen time",
                        type="string",
                        required=False,
                        enum=["plays", "duration"],
                        default="plays",
                    ),
                    ToolParameter(
                        name="limit",
                        description="Number of music items to return (default: 10)",
                        type="number",
                        required=False,
                        default=10,
                    ),
                    ToolParameter(
                        name="username",
                        description="Filter by username (optional, if not provided shows all users)",
                        type="string",
                        required=False,
                    ),
                ],
                category="monitoring",
                is_mutation=False,
                requires_service="tautulli",
            ),
            ToolDefinition(
                name="tautulli_get_top_platforms",
                description="Get most used platforms/devices for streaming over a specified period",
                parameters=[
                    ToolParameter(
                        name="days",
                        description="Number of days to analyze (default: 30)",
                        type="number",
                        required=False,
                        default=30,
                    ),
                    ToolParameter(
                        name="stats_type",
                        description="Type of stats: 'plays' for play count, 'duration' for watch time",
                        type="string",
                        required=False,
                        enum=["plays", "duration"],
                        default="plays",
                    ),
                    ToolParameter(
                        name="limit",
                        description="Number of platforms to return (default: 10)",
                        type="number",
                        required=False,
                        default=10,
                    ),
                ],
                category="monitoring",
                is_mutation=False,
                requires_service="tautulli",
            ),
            ToolDefinition(
                name="tautulli_get_user_stats",
                description=(
                    "Get detailed watch statistics for a specific user "
                    "including watch time, top content, and devices"
                ),
                parameters=[
                    ToolParameter(
                        name="username",
                        description="Username or friendly name of the user",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="days",
                        description="Number of days to analyze (default: 30)",
                        type="number",
                        required=False,
                        default=30,
                    ),
                ],
                category="monitoring",
                is_mutation=False,
                requires_service="tautulli",
            ),
            ToolDefinition(
                name="tautulli_get_watch_stats_summary",
                description=(
                    "Get a comprehensive summary of watch statistics "
                    "including top users, movies, TV shows, and platforms"
                ),
                parameters=[
                    ToolParameter(
                        name="days",
                        description="Number of days to analyze (default: 30)",
                        type="number",
                        required=False,
                        default=30,
                    ),
                    ToolParameter(
                        name="stats_type",
                        description="Type of stats: 'plays' for play count, 'duration' for watch time",
                        type="string",
                        required=False,
                        enum=["plays", "duration"],
                        default="plays",
                    ),
                    ToolParameter(
                        name="limit",
                        description="Number of items per category (default: 5)",
                        type="number",
                        required=False,
                        default=5,
                    ),
                ],
                category="monitoring",
                is_mutation=False,
                requires_service="tautulli",
            ),
            ToolDefinition(
                name="tautulli_terminate_session",
                description=(
                    "Terminate/stop an active Plex streaming session. "
                    "Use tautulli_get_activity first to get the session_id of the stream to stop."
                ),
                parameters=[
                    ToolParameter(
                        name="session_id",
                        description="The session_id from tautulli_get_activity to terminate",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="message",
                        description="Optional message to display to the user before termination",
                        type="string",
                        required=False,
                    ),
                ],
                category="monitoring",
                is_mutation=True,
                requires_service="tautulli",
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute a Tautulli tool."""
        if not self.service_config:
            return {"success": False, "error": "Tautulli service not configured"}

        try:
            # Import adapter here to avoid circular imports
            from src.adapters.tautulli import TautulliAdapter

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
            adapter = TautulliAdapter(service_proxy)

            if tool_name == "tautulli_get_activity":
                return await self._get_activity(adapter)
            elif tool_name == "tautulli_get_history":
                return await self._get_history(adapter, arguments)
            elif tool_name == "tautulli_get_users":
                return await self._get_users(adapter)
            elif tool_name == "tautulli_get_libraries":
                return await self._get_libraries(adapter)
            elif tool_name == "tautulli_get_statistics":
                return await self._get_statistics(adapter)
            elif tool_name == "tautulli_get_recently_added":
                return await self._get_recently_added(adapter, arguments)
            elif tool_name == "tautulli_get_server_info":
                return await self._get_server_info(adapter)
            elif tool_name == "tautulli_get_top_users":
                return await self._get_top_users(adapter, arguments)
            elif tool_name == "tautulli_get_top_movies":
                return await self._get_top_movies(adapter, arguments)
            elif tool_name == "tautulli_get_top_tv_shows":
                return await self._get_top_tv_shows(adapter, arguments)
            elif tool_name == "tautulli_get_top_music":
                return await self._get_top_music(adapter, arguments)
            elif tool_name == "tautulli_get_top_platforms":
                return await self._get_top_platforms(adapter, arguments)
            elif tool_name == "tautulli_get_user_stats":
                return await self._get_user_stats(adapter, arguments)
            elif tool_name == "tautulli_get_watch_stats_summary":
                return await self._get_watch_stats_summary(adapter, arguments)
            elif tool_name == "tautulli_terminate_session":
                return await self._terminate_session(adapter, arguments)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    async def _get_activity(self, adapter) -> dict:
        """Get current Plex activity."""
        activity = await adapter.get_activity()
        return {
            "success": True,
            "result": {
                "stream_count": activity.get("stream_count", 0),
                "direct_play_count": activity.get("stream_count_direct_play", 0),
                "direct_stream_count": activity.get("stream_count_direct_stream", 0),
                "transcode_count": activity.get("stream_count_transcode", 0),
                "total_bandwidth_mbps": round(activity.get("total_bandwidth", 0) / 1000, 2),
                "wan_bandwidth_mbps": round(activity.get("wan_bandwidth", 0) / 1000, 2),
                "lan_bandwidth_mbps": round(activity.get("lan_bandwidth", 0) / 1000, 2),
                "sessions": [
                    {
                        "session_id": session.get("session_id"),  # Used for terminate_session
                        "session_key": session.get("session_key"),
                        "user": session.get("friendly_name") or session.get("user"),
                        "user_id": session.get("user_id"),
                        "title": self._format_title(session),
                        "full_title": session.get("full_title"),
                        "media_type": session.get("media_type"),
                        "state": session.get("state"),
                        "progress_percent": session.get("progress_percent"),
                        "player": session.get("player"),
                        "platform": session.get("platform"),
                        "quality": session.get("quality_profile"),
                        "video_decision": session.get("video_decision"),
                        "audio_decision": session.get("audio_decision"),
                        "location": session.get("location"),
                        "ip_address": session.get("ip_address"),
                    }
                    for session in activity.get("sessions", [])
                ],
            },
        }

    async def _get_history(self, adapter, arguments: dict) -> dict:
        """Get play history."""
        length = arguments.get("length", 25)
        user = arguments.get("user")

        history_data = await adapter.get_history(length=length, user=user)

        # Convert total_duration to int (may be string from API)
        total_duration = history_data.get("total_duration", 0)
        if isinstance(total_duration, str):
            total_duration = int(total_duration) if total_duration.isdigit() else 0

        return {
            "success": True,
            "result": {
                "total_plays": history_data.get("total_plays", 0),
                "total_duration_hours": round(total_duration / 3600, 2),
                "history": [
                    {
                        "user": item.get("friendly_name") or item.get("user"),
                        "title": self._format_title(item),
                        "media_type": item.get("media_type"),
                        "date": item.get("date"),
                        "duration_minutes": round(item.get("duration", 0) / 60, 1),
                        "percent_complete": item.get("percent_complete"),
                        "watched_status": item.get("watched_status"),
                        "player": item.get("player"),
                    }
                    for item in history_data.get("history", [])
                ],
            },
        }

    async def _get_users(self, adapter) -> dict:
        """Get all users."""
        users = await adapter.get_users()

        return {
            "success": True,
            "result": {
                "total_users": len(users),
                "users": [
                    {
                        "username": user.get("username"),
                        "friendly_name": user.get("friendly_name"),
                        "email": user.get("email"),
                        "is_active": user.get("is_active"),
                        "is_admin": user.get("is_admin"),
                        "is_home_user": user.get("is_home_user"),
                        "shared_libraries": user.get("shared_libraries", []),
                    }
                    for user in users
                ],
            },
        }

    async def _get_libraries(self, adapter) -> dict:
        """Get library statistics."""
        libraries = await adapter.get_libraries()

        return {
            "success": True,
            "result": {
                "total_libraries": len(libraries),
                "libraries": [
                    {
                        "name": lib.get("section_name"),
                        "type": lib.get("section_type"),
                        "count": lib.get("count", 0),
                        "parent_count": lib.get("parent_count"),
                        "child_count": lib.get("child_count"),
                        "is_active": lib.get("is_active"),
                    }
                    for lib in libraries
                ],
            },
        }

    async def _get_statistics(self, adapter) -> dict:
        """Get comprehensive statistics."""
        stats = await adapter.get_statistics()

        activity = stats.get("current_activity", {})
        return {
            "success": True,
            "result": {
                "current_streams": activity.get("stream_count", 0),
                "recent_history_count": stats.get("recent_history_count", 0),
                "total_users": stats.get("total_users", 0),
                "active_users": stats.get("active_users", 0),
                "libraries_count": stats.get("libraries_count", 0),
                "libraries": [
                    {
                        "name": lib.get("section_name"),
                        "type": lib.get("section_type"),
                        "count": lib.get("count", 0),
                    }
                    for lib in stats.get("libraries", [])
                ],
                "recent_sessions": [
                    {
                        "user": session.get("friendly_name") or session.get("user"),
                        "title": self._format_title(session),
                        "state": session.get("state"),
                    }
                    for session in stats.get("recent_sessions", [])
                ],
            },
        }

    async def _get_recently_added(self, adapter, arguments: dict) -> dict:
        """Get recently added items."""
        count = arguments.get("count", 25)

        items = await adapter.get_recently_added(count=count)

        return {
            "success": True,
            "result": {
                "count": len(items),
                "items": [
                    {
                        "title": self._format_title(item),
                        "media_type": item.get("media_type"),
                        "year": item.get("year"),
                        "library": item.get("library_name"),
                        "added_at": item.get("added_at"),
                        "rating": item.get("rating"),
                    }
                    for item in items
                ],
            },
        }

    async def _get_server_info(self, adapter) -> dict:
        """Get server information."""
        info = await adapter.get_service_info()

        return {
            "success": True,
            "result": {
                "tautulli_version": info.get("version"),
                "plex_name": info.get("plex_name"),
                "plex_version": info.get("plex_version"),
                "plex_platform": info.get("plex_platform"),
                "update_available": info.get("update_available", False),
                "update_version": info.get("update_version"),
            },
        }

    def _format_title(self, item: dict) -> str:
        """Format title including parent/grandparent for TV shows."""
        title = item.get("title", "")
        grandparent = item.get("grandparent_title")
        parent = item.get("parent_title")

        if grandparent:
            # TV episode: Show - Season - Episode
            return f"{grandparent} - {parent} - {title}" if parent else f"{grandparent} - {title}"
        elif parent:
            return f"{parent} - {title}"
        return title

    async def _get_user_id_from_username(self, adapter, username: str) -> int | None:
        """Get user_id from username or friendly_name."""
        user = await adapter.get_user_by_username(username)
        if user:
            return user.get("user_id")
        return None

    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to human readable string."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}m"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"{hours}h {minutes}m"
            return f"{hours}h"

    def _extract_stat_rows(self, stats_data: list, stat_id: str) -> list:
        """Extract rows for a specific stat_id from home stats data.

        Handles two formats:
        1. When stat_id filter is used: returns list with single stat object containing rows
        2. When no filter: returns list of all stats, each with stat_id and rows
        """
        if not stats_data:
            return []

        # Check if this is a filtered response (single stat with rows directly)
        if len(stats_data) == 1 and stats_data[0].get("stat_id") == stat_id:
            return stats_data[0].get("rows", [])

        # Also handle case where rows are directly in the response
        if len(stats_data) == 1 and "rows" in stats_data[0] and "stat_id" not in stats_data[0]:
            return stats_data[0].get("rows", [])

        # Standard format: search for matching stat_id
        for stat in stats_data:
            if stat.get("stat_id") == stat_id:
                return stat.get("rows", [])

        return []

    async def _get_top_users(self, adapter, arguments: dict) -> dict:
        """Get top users by plays or duration."""
        days = arguments.get("days", 30)
        stats_type = arguments.get("stats_type", "plays")
        limit = arguments.get("limit", 10)

        stats_data = await adapter.get_home_stats(
            time_range=days, stats_type=stats_type, stats_count=limit, stat_id="top_users"
        )

        rows = self._extract_stat_rows(stats_data, "top_users")

        users = []
        for row in rows:
            user_data = {
                "rank": len(users) + 1,
                "username": row.get("friendly_name") or row.get("user"),
                "user_id": row.get("user_id"),
            }
            if stats_type == "plays":
                user_data["total_plays"] = row.get("total_plays", 0)
            else:
                duration = row.get("total_duration", 0)
                user_data["total_duration_seconds"] = duration
                user_data["total_duration"] = self._format_duration(duration)
            users.append(user_data)

        return {"success": True, "result": {"period_days": days, "stats_type": stats_type, "users": users}}

    async def _get_top_movies(self, adapter, arguments: dict) -> dict:
        """Get top watched movies."""
        days = arguments.get("days", 30)
        stats_type = arguments.get("stats_type", "plays")
        limit = arguments.get("limit", 10)
        username = arguments.get("username")

        user_id = None
        if username:
            user_id = await self._get_user_id_from_username(adapter, username)
            if user_id is None:
                return {"success": False, "error": f"User '{username}' not found"}

        stats_data = await adapter.get_home_stats(
            time_range=days, stats_type=stats_type, stats_count=limit, stat_id="top_movies", user_id=user_id
        )

        rows = self._extract_stat_rows(stats_data, "top_movies")

        movies = []
        for row in rows:
            movie_data = {
                "rank": len(movies) + 1,
                "title": row.get("title"),
                "year": row.get("year"),
                "rating_key": row.get("rating_key"),
            }
            if stats_type == "plays":
                movie_data["total_plays"] = row.get("total_plays", 0)
            else:
                duration = row.get("total_duration", 0)
                movie_data["total_duration_seconds"] = duration
                movie_data["total_duration"] = self._format_duration(duration)
            movies.append(movie_data)

        result = {"period_days": days, "stats_type": stats_type, "movies": movies}
        if username:
            result["filtered_by_user"] = username

        return {"success": True, "result": result}

    async def _get_top_tv_shows(self, adapter, arguments: dict) -> dict:
        """Get top watched TV shows."""
        days = arguments.get("days", 30)
        stats_type = arguments.get("stats_type", "plays")
        limit = arguments.get("limit", 10)
        username = arguments.get("username")

        user_id = None
        if username:
            user_id = await self._get_user_id_from_username(adapter, username)
            if user_id is None:
                return {"success": False, "error": f"User '{username}' not found"}

        stats_data = await adapter.get_home_stats(
            time_range=days, stats_type=stats_type, stats_count=limit, stat_id="top_tv", user_id=user_id
        )

        rows = self._extract_stat_rows(stats_data, "top_tv")

        shows = []
        for row in rows:
            show_data = {
                "rank": len(shows) + 1,
                "title": row.get("grandparent_title") or row.get("title"),
                "rating_key": row.get("grandparent_rating_key") or row.get("rating_key"),
            }
            if stats_type == "plays":
                show_data["total_plays"] = row.get("total_plays", 0)
            else:
                duration = row.get("total_duration", 0)
                show_data["total_duration_seconds"] = duration
                show_data["total_duration"] = self._format_duration(duration)
            shows.append(show_data)

        result = {"period_days": days, "stats_type": stats_type, "tv_shows": shows}
        if username:
            result["filtered_by_user"] = username

        return {"success": True, "result": result}

    async def _get_top_music(self, adapter, arguments: dict) -> dict:
        """Get top listened music."""
        days = arguments.get("days", 30)
        stats_type = arguments.get("stats_type", "plays")
        limit = arguments.get("limit", 10)
        username = arguments.get("username")

        user_id = None
        if username:
            user_id = await self._get_user_id_from_username(adapter, username)
            if user_id is None:
                return {"success": False, "error": f"User '{username}' not found"}

        stats_data = await adapter.get_home_stats(
            time_range=days, stats_type=stats_type, stats_count=limit, stat_id="top_music", user_id=user_id
        )

        rows = self._extract_stat_rows(stats_data, "top_music")

        music = []
        for row in rows:
            music_data = {
                "rank": len(music) + 1,
                "artist": row.get("grandparent_title"),
                "album": row.get("parent_title"),
                "track": row.get("title"),
                "rating_key": row.get("rating_key"),
            }
            if stats_type == "plays":
                music_data["total_plays"] = row.get("total_plays", 0)
            else:
                duration = row.get("total_duration", 0)
                music_data["total_duration_seconds"] = duration
                music_data["total_duration"] = self._format_duration(duration)
            music.append(music_data)

        result = {"period_days": days, "stats_type": stats_type, "music": music}
        if username:
            result["filtered_by_user"] = username

        return {"success": True, "result": result}

    async def _get_top_platforms(self, adapter, arguments: dict) -> dict:
        """Get top platforms/devices."""
        days = arguments.get("days", 30)
        stats_type = arguments.get("stats_type", "plays")
        limit = arguments.get("limit", 10)

        stats_data = await adapter.get_home_stats(
            time_range=days, stats_type=stats_type, stats_count=limit, stat_id="top_platforms"
        )

        rows = self._extract_stat_rows(stats_data, "top_platforms")

        platforms = []
        for row in rows:
            platform_data = {
                "rank": len(platforms) + 1,
                "platform": row.get("platform"),
            }
            if stats_type == "plays":
                platform_data["total_plays"] = row.get("total_plays", 0)
            else:
                duration = row.get("total_duration", 0)
                platform_data["total_duration_seconds"] = duration
                platform_data["total_duration"] = self._format_duration(duration)
            platforms.append(platform_data)

        return {"success": True, "result": {"period_days": days, "stats_type": stats_type, "platforms": platforms}}

    async def _get_user_stats(self, adapter, arguments: dict) -> dict:
        """Get detailed statistics for a specific user."""
        username = arguments.get("username")
        days = arguments.get("days", 30)

        if not username:
            return {"success": False, "error": "Username is required"}

        # Find user
        user = await adapter.get_user_by_username(username)
        if not user:
            return {"success": False, "error": f"User '{username}' not found"}

        user_id = user.get("user_id")

        # Get user's watch time stats
        watch_time_stats = await adapter.get_user_watch_time_stats(user_id, query_days=[1, 7, 30, 0])

        # Get user's top content for the period
        top_movies_data = await adapter.get_home_stats(
            time_range=days, stats_count=5, stat_id="top_movies", user_id=user_id
        )
        top_tv_data = await adapter.get_home_stats(time_range=days, stats_count=5, stat_id="top_tv", user_id=user_id)

        # Get player stats
        player_stats = await adapter.get_user_player_stats(user_id)

        # Process watch time stats
        watch_time = {}
        if isinstance(watch_time_stats, list):
            for stat in watch_time_stats:
                query_days = stat.get("query_days", 0)
                total_time = stat.get("total_time", 0)
                total_plays = stat.get("total_plays", 0)
                if query_days == 1:
                    watch_time["last_24h"] = {"plays": total_plays, "duration": self._format_duration(total_time)}
                elif query_days == 7:
                    watch_time["last_7_days"] = {"plays": total_plays, "duration": self._format_duration(total_time)}
                elif query_days == 30:
                    watch_time["last_30_days"] = {"plays": total_plays, "duration": self._format_duration(total_time)}
                elif query_days == 0:
                    watch_time["all_time"] = {"plays": total_plays, "duration": self._format_duration(total_time)}

        # Extract top content
        top_movies = [
            {"title": m.get("title"), "plays": m.get("total_plays", 0)}
            for m in self._extract_stat_rows(top_movies_data, "top_movies")[:5]
        ]
        top_shows = [
            {"title": s.get("grandparent_title") or s.get("title"), "plays": s.get("total_plays", 0)}
            for s in self._extract_stat_rows(top_tv_data, "top_tv")[:5]
        ]

        # Process player stats
        devices = [
            {"platform": p.get("platform"), "player": p.get("player"), "total_plays": p.get("total_plays", 0)}
            for p in (player_stats[:5] if player_stats else [])
        ]

        return {
            "success": True,
            "result": {
                "user": {
                    "username": user.get("username"),
                    "friendly_name": user.get("friendly_name"),
                    "user_id": user_id,
                    "is_active": user.get("is_active"),
                },
                "watch_time": watch_time,
                f"top_movies_last_{days}_days": top_movies,
                f"top_tv_shows_last_{days}_days": top_shows,
                "devices": devices,
            },
        }

    async def _get_watch_stats_summary(self, adapter, arguments: dict) -> dict:
        """Get comprehensive watch statistics summary."""
        days = arguments.get("days", 30)
        stats_type = arguments.get("stats_type", "plays")
        limit = arguments.get("limit", 5)

        # Fetch all stats at once
        stats_data = await adapter.get_home_stats(time_range=days, stats_type=stats_type, stats_count=limit)

        # Extract each category
        def extract_items(stat_id: str, title_key: str = "title") -> list:
            rows = self._extract_stat_rows(stats_data, stat_id)
            items = []
            for row in rows:
                item = {"title": row.get(title_key) or row.get("grandparent_title") or row.get("title")}
                if stats_type == "plays":
                    item["plays"] = row.get("total_plays", 0)
                else:
                    item["duration"] = self._format_duration(row.get("total_duration", 0))
                items.append(item)
            return items

        top_users = []
        for row in self._extract_stat_rows(stats_data, "top_users"):
            user_item = {"username": row.get("friendly_name") or row.get("user")}
            if stats_type == "plays":
                user_item["plays"] = row.get("total_plays", 0)
            else:
                user_item["duration"] = self._format_duration(row.get("total_duration", 0))
            top_users.append(user_item)

        top_platforms = []
        for row in self._extract_stat_rows(stats_data, "top_platforms"):
            platform_item = {"platform": row.get("platform")}
            if stats_type == "plays":
                platform_item["plays"] = row.get("total_plays", 0)
            else:
                platform_item["duration"] = self._format_duration(row.get("total_duration", 0))
            top_platforms.append(platform_item)

        return {
            "success": True,
            "result": {
                "period_days": days,
                "stats_type": stats_type,
                "top_users": top_users,
                "top_movies": extract_items("top_movies"),
                "top_tv_shows": extract_items("top_tv", "grandparent_title"),
                "top_music": extract_items("top_music", "grandparent_title"),
                "top_platforms": top_platforms,
            },
        }

    async def _terminate_session(self, adapter, arguments: dict) -> dict:
        """Terminate an active Plex streaming session."""
        session_id = arguments.get("session_id")
        message = arguments.get("message")

        if not session_id:
            return {"success": False, "error": "session_id is required"}

        result = await adapter.terminate_session(session_id=session_id, message=message)

        if result.get("success"):
            return {
                "success": True,
                "result": {
                    "terminated": True,
                    "session_id": session_id,
                    "message": message or "Session terminated successfully",
                },
            }
        else:
            return {"success": False, "error": result.get("error", "Failed to terminate session")}
