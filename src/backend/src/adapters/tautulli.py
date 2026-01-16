"""Tautulli Plex analytics adapter."""

from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from .base import (
    AdapterError,
    AuthenticationError,
    ConnectionTestResult,
    ServiceCapability,
    TokenAuthAdapter,
)


class TautulliAdapter(TokenAuthAdapter):
    """Adapter for Tautulli Plex analytics and monitoring."""

    @property
    def service_type(self) -> str:
        return "tautulli"

    @property
    def supported_capabilities(self) -> List[ServiceCapability]:
        return [ServiceCapability.MONITORING, ServiceCapability.MEDIA_CONTENT, ServiceCapability.API_ACCESS]

    @property
    def token_config_key(self) -> str:
        return "tautulli_api_key"

    def _format_token_header(self, token: str) -> Dict[str, str]:
        """Format Tautulli API key header."""
        return {"Accept": "application/json", "Content-Type": "application/json"}

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for Tautulli (uses query params, not headers)."""
        return {"Accept": "application/json", "Content-Type": "application/json"}

    def _get_auth_params(self) -> Dict[str, str]:
        """Get authentication parameters for Tautulli API."""
        # First try to get token from api_key field
        token = self.service_config.api_key

        # Fall back to config if api_key is not set
        if not token:
            token = self.get_config_value(self.token_config_key)

        if not token:
            return {}
        return {"apikey": token}

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Override to add API key as query parameter."""
        # Add auth params to existing params
        params = kwargs.get("params", {})
        params.update(self._get_auth_params())
        kwargs["params"] = params

        # Tautulli API endpoints start with /api/v2
        if not endpoint.startswith("/api/"):
            endpoint = f"/api/v2{endpoint}"

        return await super()._make_request(method, endpoint, **kwargs)

    async def test_connection(self) -> ConnectionTestResult:
        """Test connection to Tautulli."""
        start_time = datetime.utcnow()

        try:
            # Test basic connectivity and auth
            response = await self._make_request("GET", "?cmd=arnold")

            end_time = datetime.utcnow()
            response_time = int((end_time - start_time).total_seconds() * 1000)

            data = response.json()

            if data.get("response", {}).get("result") == "success":
                return ConnectionTestResult(
                    success=True,
                    message="Successfully connected to Tautulli",
                    response_time_ms=response_time,
                    details={"status": "connected", "message": data.get("response", {}).get("message", "")},
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message="Connected but Tautulli returned an error",
                    response_time_ms=response_time,
                    details={"status": "api_error", "error": data.get("response", {}).get("message")},
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return ConnectionTestResult(
                    success=False,
                    message="Authentication failed - check API key",
                    details={"status": "auth_failed", "status_code": 401},
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message=f"HTTP error: {e.response.status_code}",
                    details={"status": "http_error", "status_code": e.response.status_code},
                )
        except httpx.RequestError as e:
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                details={"status": "connection_failed", "error": str(e)},
            )
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Unexpected error: {str(e)}",
                details={"status": "unexpected_error", "error": str(e)},
            )

    async def get_service_info(self) -> Dict[str, Any]:
        """Get Tautulli service information."""
        try:
            # Get server info
            response = await self._make_request("GET", "?cmd=get_server_info")
            data = response.json()

            if data.get("response", {}).get("result") != "success":
                raise AdapterError("Failed to get server info from Tautulli")

            server_info = data.get("response", {}).get("data", {})

            return {
                "service": "tautulli",
                "version": server_info.get("version"),
                "plex_name": server_info.get("plex_name"),
                "plex_version": server_info.get("plex_version"),
                "plex_platform": server_info.get("plex_platform"),
                "plex_machine_identifier": server_info.get("plex_machine_identifier"),
                "update_available": server_info.get("update_available", False),
                "update_version": server_info.get("update_version"),
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid Tautulli API key") from e
            raise AdapterError(f"HTTP error: {e.response.status_code}") from e
        except Exception as e:
            raise AdapterError(f"Failed to get service info: {str(e)}") from e

    async def get_activity(self) -> Dict[str, Any]:
        """Get current Plex activity from Tautulli."""
        try:
            response = await self._make_request("GET", "?cmd=get_activity")
            data = response.json()

            if data.get("response", {}).get("result") != "success":
                return {"sessions": [], "stream_count": 0}

            activity_data = data.get("response", {}).get("data", {})
            sessions = activity_data.get("sessions", [])

            processed_sessions = []
            for session in sessions:
                processed_sessions.append(
                    {
                        "session_key": session.get("session_key"),
                        "session_id": session.get("session_id"),  # Used for terminate_session
                        "user": session.get("user"),
                        "user_id": session.get("user_id"),
                        "friendly_name": session.get("friendly_name"),
                        "title": session.get("title"),
                        "parent_title": session.get("parent_title"),
                        "grandparent_title": session.get("grandparent_title"),
                        "full_title": session.get("full_title"),
                        "media_type": session.get("media_type"),
                        "state": session.get("state"),
                        "progress_percent": session.get("progress_percent"),
                        "duration": session.get("duration"),
                        "view_offset": session.get("view_offset"),
                        "player": session.get("player"),
                        "platform": session.get("platform"),
                        "product": session.get("product"),
                        "quality_profile": session.get("quality_profile"),
                        "video_decision": session.get("video_decision"),
                        "audio_decision": session.get("audio_decision"),
                        "bandwidth": session.get("bandwidth"),
                        "location": session.get("location"),
                        "ip_address": session.get("ip_address"),
                    }
                )

            return {
                "sessions": processed_sessions,
                "stream_count": activity_data.get("stream_count", 0),
                "stream_count_direct_play": activity_data.get("stream_count_direct_play", 0),
                "stream_count_direct_stream": activity_data.get("stream_count_direct_stream", 0),
                "stream_count_transcode": activity_data.get("stream_count_transcode", 0),
                "total_bandwidth": activity_data.get("total_bandwidth", 0),
                "wan_bandwidth": activity_data.get("wan_bandwidth", 0),
                "lan_bandwidth": activity_data.get("lan_bandwidth", 0),
            }

        except Exception as e:
            self.logger.warning(f"Failed to get activity: {e}")
            return {"sessions": [], "stream_count": 0}

    async def get_history(self, length: int = 25, start: int = 0, user: Optional[str] = None) -> Dict[str, Any]:
        """Get play history from Tautulli."""
        try:
            params = {"cmd": "get_history", "length": str(length), "start": str(start)}
            if user:
                params["user"] = user

            response = await self._make_request("GET", "", params=params)
            data = response.json()

            if data.get("response", {}).get("result") != "success":
                return {"history": [], "total_duration": 0}

            history_data = data.get("response", {}).get("data", {})
            history_items = history_data.get("data", [])

            processed_history = []
            for item in history_items:
                processed_history.append(
                    {
                        "id": item.get("id"),
                        "date": item.get("date"),
                        "started": item.get("started"),
                        "stopped": item.get("stopped"),
                        "duration": item.get("duration"),
                        "watched_status": item.get("watched_status"),
                        "user": item.get("user"),
                        "friendly_name": item.get("friendly_name"),
                        "title": item.get("title"),
                        "parent_title": item.get("parent_title"),
                        "grandparent_title": item.get("grandparent_title"),
                        "media_type": item.get("media_type"),
                        "rating_key": item.get("rating_key"),
                        "parent_rating_key": item.get("parent_rating_key"),
                        "grandparent_rating_key": item.get("grandparent_rating_key"),
                        "year": item.get("year"),
                        "player": item.get("player"),
                        "ip_address": item.get("ip_address"),
                        "paused_counter": item.get("paused_counter"),
                        "percent_complete": item.get("percent_complete"),
                    }
                )

            return {
                "history": processed_history,
                "total_duration": history_data.get("total_duration", 0),
                "filtered_from_grouping": history_data.get("filtered_from_grouping", 0),
                "total_plays": len(processed_history),
            }

        except Exception as e:
            self.logger.warning(f"Failed to get history: {e}")
            return {"history": [], "total_duration": 0}

    async def get_users(self) -> List[Dict[str, Any]]:
        """Get users from Tautulli."""
        try:
            response = await self._make_request("GET", "?cmd=get_users")
            data = response.json()

            if data.get("response", {}).get("result") != "success":
                return []

            users_data = data.get("response", {}).get("data", [])
            users = []

            for user in users_data:
                users.append(
                    {
                        "user_id": user.get("user_id"),
                        "username": user.get("username"),
                        "friendly_name": user.get("friendly_name"),
                        "email": user.get("email"),
                        "thumb": user.get("thumb"),
                        "is_active": user.get("is_active"),
                        "is_admin": user.get("is_admin"),
                        "is_home_user": user.get("is_home_user"),
                        "is_allow_sync": user.get("is_allow_sync"),
                        "is_restricted": user.get("is_restricted"),
                        "do_notify": user.get("do_notify"),
                        "keep_history": user.get("keep_history"),
                        "allow_guest": user.get("allow_guest"),
                        "server_token": user.get("server_token"),
                        "shared_libraries": user.get("shared_libraries", []),
                        "filter_all": user.get("filter_all"),
                        "filter_movies": user.get("filter_movies"),
                        "filter_tv": user.get("filter_tv"),
                        "filter_music": user.get("filter_music"),
                        "filter_photos": user.get("filter_photos"),
                    }
                )

            return users

        except Exception as e:
            self.logger.warning(f"Failed to get users: {e}")
            return []

    async def get_libraries(self) -> List[Dict[str, Any]]:
        """Get library statistics from Tautulli."""
        try:
            response = await self._make_request("GET", "?cmd=get_libraries")
            data = response.json()

            if data.get("response", {}).get("result") != "success":
                return []

            libraries_data = data.get("response", {}).get("data", [])
            libraries = []

            for library in libraries_data:
                libraries.append(
                    {
                        "section_id": library.get("section_id"),
                        "section_name": library.get("section_name"),
                        "section_type": library.get("section_type"),
                        "agent": library.get("agent"),
                        "thumb": library.get("thumb"),
                        "art": library.get("art"),
                        "count": library.get("count"),
                        "parent_count": library.get("parent_count"),
                        "child_count": library.get("child_count"),
                        "is_active": library.get("is_active"),
                        "do_notify": library.get("do_notify"),
                        "do_notify_created": library.get("do_notify_created"),
                        "keep_history": library.get("keep_history"),
                        "deleted_section": library.get("deleted_section"),
                    }
                )

            return libraries

        except Exception as e:
            self.logger.warning(f"Failed to get libraries: {e}")
            return []

    async def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics from Tautulli."""
        try:
            # Get current activity
            activity = await self.get_activity()

            # Get recent history
            history = await self.get_history(50)

            # Get users count
            users = await self.get_users()

            # Get libraries
            libraries = await self.get_libraries()

            # Get home stats
            home_stats = await self._safe_request("GET", "?cmd=get_home_stats&time_range=30")

            stats_data = {}
            if home_stats and home_stats.get("response", {}).get("result") == "success":
                stats_data = home_stats.get("response", {}).get("data", [])

            return {
                "current_activity": activity,
                "recent_history_count": len(history.get("history", [])),
                "total_users": len(users),
                "active_users": sum(1 for user in users if user.get("is_active")),
                "libraries_count": len(libraries),
                "home_stats": stats_data[:5] if isinstance(stats_data, list) else {},
                "libraries": libraries,
                "recent_sessions": activity.get("sessions", [])[:5],
            }

        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                "current_activity": {"sessions": [], "stream_count": 0},
                "recent_history_count": 0,
                "total_users": 0,
                "active_users": 0,
                "libraries_count": 0,
                "home_stats": [],
                "libraries": [],
                "recent_sessions": [],
            }

    async def get_recently_added(self, count: int = 25) -> List[Dict[str, Any]]:
        """Get recently added items."""
        try:
            params = {"cmd": "get_recently_added", "count": str(count)}
            response = await self._make_request("GET", "", params=params)
            data = response.json()

            if data.get("response", {}).get("result") != "success":
                return []

            recently_added = data.get("response", {}).get("data", {}).get("recently_added", [])
            items = []

            for item in recently_added:
                items.append(
                    {
                        "added_at": item.get("added_at"),
                        "title": item.get("title"),
                        "parent_title": item.get("parent_title"),
                        "grandparent_title": item.get("grandparent_title"),
                        "media_type": item.get("media_type"),
                        "year": item.get("year"),
                        "rating": item.get("rating"),
                        "section_id": item.get("section_id"),
                        "library_name": item.get("library_name"),
                        "thumb": item.get("thumb"),
                        "art": item.get("art"),
                    }
                )

            return items

        except Exception as e:
            self.logger.warning(f"Failed to get recently added: {e}")
            return []

    async def get_home_stats(
        self,
        time_range: int = 30,
        stats_type: str = "plays",
        stats_count: int = 10,
        stat_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get homepage watch statistics.

        Args:
            time_range: Number of days to calculate statistics (default: 30)
            stats_type: 'plays' or 'duration'
            stats_count: Number of items to return per stat (default: 10)
            stat_id: Optional specific stat to return (top_movies, top_tv, top_users, etc.)
            user_id: Optional user_id to filter stats for a specific user

        Available stat_id values:
            - top_movies: Most watched movies
            - popular_movies: Most popular movies (unique users)
            - top_tv: Most watched TV shows
            - popular_tv: Most popular TV shows (unique users)
            - top_music: Most listened music
            - popular_music: Most popular music
            - top_libraries: Most active libraries
            - top_users: Most active users
            - top_platforms: Most used platforms
            - last_watched: Last watched items
            - most_concurrent: Most concurrent streams
        """
        try:
            params = {
                "cmd": "get_home_stats",
                "time_range": str(time_range),
                "stats_type": stats_type,
                "stats_count": str(stats_count),
            }

            if stat_id:
                params["stat_id"] = stat_id

            if user_id:
                params["user_id"] = str(user_id)

            response = await self._make_request("GET", "", params=params)
            data = response.json()

            if data.get("response", {}).get("result") != "success":
                self.logger.warning(f"get_home_stats failed: {data.get('response', {})}")
                return []

            stats_data = data.get("response", {}).get("data", [])
            # When stat_id is specified, Tautulli returns a single dict instead of a list
            # Normalize to always return a list for consistent handling
            if isinstance(stats_data, dict):
                stats_data = [stats_data]
            return stats_data if isinstance(stats_data, list) else []

        except Exception as e:
            self.logger.warning(f"Failed to get home stats: {e}")
            return []

    async def get_user_watch_time_stats(self, user_id: int, query_days: Optional[List[int]] = None) -> Dict[str, Any]:
        """Get a user's watch time statistics.

        Args:
            user_id: The user's Tautulli user_id
            query_days: Optional list of days to query (e.g., [1, 7, 30, 0] where 0 is all time)
        """
        try:
            params = {"cmd": "get_user_watch_time_stats", "user_id": str(user_id)}

            if query_days:
                params["query_days"] = ",".join(str(d) for d in query_days)

            response = await self._make_request("GET", "", params=params)
            data = response.json()

            if data.get("response", {}).get("result") != "success":
                return {}

            return data.get("response", {}).get("data", {})

        except Exception as e:
            self.logger.warning(f"Failed to get user watch time stats: {e}")
            return {}

    async def get_user_player_stats(self, user_id: int) -> List[Dict[str, Any]]:
        """Get a user's player statistics."""
        try:
            params = {"cmd": "get_user_player_stats", "user_id": str(user_id)}
            response = await self._make_request("GET", "", params=params)
            data = response.json()

            if data.get("response", {}).get("result") != "success":
                return []

            return data.get("response", {}).get("data", [])

        except Exception as e:
            self.logger.warning(f"Failed to get user player stats: {e}")
            return []

    async def get_plays_by_date(
        self, time_range: int = 30, y_axis: str = "plays", user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get play counts by date.

        Args:
            time_range: Number of days (default: 30)
            y_axis: 'plays' or 'duration'
            user_id: Optional user_id filter
        """
        try:
            params = {"cmd": "get_plays_by_date", "time_range": str(time_range), "y_axis": y_axis}

            if user_id:
                params["user_id"] = str(user_id)

            response = await self._make_request("GET", "", params=params)
            data = response.json()

            if data.get("response", {}).get("result") != "success":
                return {}

            return data.get("response", {}).get("data", {})

        except Exception as e:
            self.logger.warning(f"Failed to get plays by date: {e}")
            return {}

    async def get_plays_per_month(
        self, time_range: int = 12, y_axis: str = "plays", user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get play counts per month.

        Args:
            time_range: Number of months (default: 12)
            y_axis: 'plays' or 'duration'
            user_id: Optional user_id filter
        """
        try:
            params = {"cmd": "get_plays_per_month", "time_range": str(time_range), "y_axis": y_axis}

            if user_id:
                params["user_id"] = str(user_id)

            response = await self._make_request("GET", "", params=params)
            data = response.json()

            if data.get("response", {}).get("result") != "success":
                return {}

            return data.get("response", {}).get("data", {})

        except Exception as e:
            self.logger.warning(f"Failed to get plays per month: {e}")
            return {}

    async def get_stream_type_by_top_10_users(self, time_range: int = 30, y_axis: str = "plays") -> Dict[str, Any]:
        """Get stream type breakdown for top 10 users."""
        try:
            params = {"cmd": "get_stream_type_by_top_10_users", "time_range": str(time_range), "y_axis": y_axis}

            response = await self._make_request("GET", "", params=params)
            data = response.json()

            if data.get("response", {}).get("result") != "success":
                return {}

            return data.get("response", {}).get("data", {})

        except Exception as e:
            self.logger.warning(f"Failed to get stream type by top 10 users: {e}")
            return {}

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user details by user_id."""
        try:
            params = {"cmd": "get_user", "user_id": str(user_id)}
            response = await self._make_request("GET", "", params=params)
            data = response.json()

            if data.get("response", {}).get("result") != "success":
                return None

            return data.get("response", {}).get("data")

        except Exception as e:
            self.logger.warning(f"Failed to get user by id: {e}")
            return None

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user details by username."""
        users = await self.get_users()
        for user in users:
            if (
                user.get("username", "").lower() == username.lower()
                or user.get("friendly_name", "").lower() == username.lower()
            ):
                return user
        return None

    async def terminate_session(
        self, session_id: str, session_key: Optional[str] = None, message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Terminate a Plex streaming session.

        Args:
            session_id: The session_id from get_activity (required)
            session_key: The session_key from get_activity (optional, for display)
            message: Optional message to display to the user before termination

        Returns:
            Dict with termination status
        """
        try:
            params = {"cmd": "terminate_session", "session_id": session_id}

            if message:
                params["message"] = message

            response = await self._make_request("GET", "", params=params)
            data = response.json()

            if data.get("response", {}).get("result") == "success":
                return {
                    "success": True,
                    "session_id": session_id,
                    "session_key": session_key,
                    "message": message or "Session terminated",
                }
            else:
                error_msg = data.get("response", {}).get("message", "Failed to terminate session")
                return {"success": False, "error": error_msg, "session_id": session_id}

        except Exception as e:
            self.logger.error(f"Failed to terminate session: {e}")
            return {"success": False, "error": str(e), "session_id": session_id}

    def validate_config(self) -> List[str]:
        """Validate Tautulli-specific configuration."""
        errors = super().validate_config()

        # Check for required API key
        if not self.get_config_value(self.token_config_key):
            errors.append("Tautulli API key is required")

        return errors
