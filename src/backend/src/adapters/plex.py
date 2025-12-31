"""Plex Media Server adapter."""

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


class PlexAdapter(TokenAuthAdapter):
    """Adapter for Plex Media Server integration."""

    @property
    def service_type(self) -> str:
        return "plex"

    @property
    def supported_capabilities(self) -> List[ServiceCapability]:
        return [ServiceCapability.MEDIA_CONTENT, ServiceCapability.USER_MANAGEMENT, ServiceCapability.API_ACCESS]

    @property
    def token_config_key(self) -> str:
        return "plex_token"

    def get_auth_headers(self) -> Dict[str, str]:
        """Get Plex authentication headers."""
        # First try to get token from api_key field
        token = self.service_config.api_key

        # Fall back to config if api_key is not set
        if not token:
            token = self.get_config_value(self.token_config_key)

        if not token:
            return {"Accept": "application/json"}

        return self._format_token_header(token)

    def _format_token_header(self, token: str) -> Dict[str, str]:
        """Format Plex token header."""
        return {"X-Plex-Token": token, "Accept": "application/json"}

    async def test_connection(self) -> ConnectionTestResult:
        """Test connection to Plex server."""
        start_time = datetime.utcnow()

        try:
            # Test basic connectivity
            response = await self._make_request("GET", "/")

            end_time = datetime.utcnow()
            response_time = int((end_time - start_time).total_seconds() * 1000)

            # Check if we got a valid Plex response
            if "MediaContainer" in response.text:
                return ConnectionTestResult(
                    success=True,
                    message="Successfully connected to Plex server",
                    response_time_ms=response_time,
                    details={"status": "connected", "server_type": "plex"},
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message="Connected but response doesn't appear to be from Plex",
                    response_time_ms=response_time,
                    details={"status": "invalid_response"},
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return ConnectionTestResult(
                    success=False,
                    message="Authentication failed - check Plex token",
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
        """Get Plex server information."""
        try:
            response = await self._make_request("GET", "/")
            data = response.json()

            if "MediaContainer" not in data:
                raise AdapterError("Invalid response from Plex server")

            container = data["MediaContainer"]

            return {
                "service": "plex",
                "version": container.get("version", "unknown"),
                "platform": container.get("platform", "unknown"),
                "server_name": container.get("friendlyName", "Plex Server"),
                "machine_identifier": container.get("machineIdentifier"),
                "updated_at": container.get("updatedAt"),
                "multiuser": container.get("multiuser", False),
                "my_plex": container.get("myPlex", False),
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid Plex token") from e
            raise AdapterError(f"HTTP error: {e.response.status_code}") from e
        except Exception as e:
            raise AdapterError(f"Failed to get service info: {str(e)}") from e

    async def get_libraries(self) -> List[Dict[str, Any]]:
        """Get Plex libraries."""
        try:
            response = await self._make_request("GET", "/library/sections")
            data = response.json()

            if "MediaContainer" not in data:
                return []

            directories = data["MediaContainer"].get("Directory", [])
            libraries = []

            for directory in directories:
                libraries.append(
                    {
                        "key": directory.get("key"),
                        "title": directory.get("title"),
                        "type": directory.get("type"),
                        "agent": directory.get("agent"),
                        "language": directory.get("language"),
                        "refreshing": directory.get("refreshing", False),
                        "created_at": directory.get("createdAt"),
                        "updated_at": directory.get("updatedAt"),
                    }
                )

            return libraries

        except Exception as e:
            self.logger.error(f"Failed to get libraries: {e}")
            return []

    async def get_users(self) -> List[Dict[str, Any]]:
        """Get Plex users (requires Plex Pass for full functionality)."""
        try:
            # Try to get users from the server
            response = await self._make_request("GET", "/accounts")
            data = response.json()

            if "MediaContainer" not in data:
                return []

            accounts = data["MediaContainer"].get("Account", [])
            users = []

            for account in accounts:
                users.append(
                    {
                        "id": account.get("id"),
                        "name": account.get("name"),
                        "email": account.get("email"),
                        "thumb": account.get("thumb"),
                        "home": account.get("home", False),
                        "admin": account.get("admin", False),
                        "guest": account.get("guest", False),
                    }
                )

            return users

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Users endpoint not available, return empty list
                return []
            raise
        except Exception as e:
            self.logger.warning(f"Failed to get users: {e}")
            return []

    async def get_sessions(self) -> List[Dict[str, Any]]:
        """Get current Plex sessions (active streams)."""
        try:
            response = await self._make_request("GET", "/status/sessions")
            data = response.json()

            if "MediaContainer" not in data:
                return []

            sessions = data["MediaContainer"].get("Metadata", [])
            active_sessions = []

            for session in sessions:
                user_info = session.get("User", [{}])[0] if session.get("User") else {}
                player_info = session.get("Player", {})

                active_sessions.append(
                    {
                        "session_key": session.get("sessionKey"),
                        "user_id": user_info.get("id"),
                        "username": user_info.get("title"),
                        "title": session.get("title"),
                        "type": session.get("type"),
                        "state": session.get("Player", {}).get("state"),
                        "player": player_info.get("title"),
                        "platform": player_info.get("platform"),
                        "progress": session.get("viewOffset", 0),
                        "duration": session.get("duration", 0),
                    }
                )

            return active_sessions

        except Exception as e:
            self.logger.warning(f"Failed to get sessions: {e}")
            return []

    async def get_recently_added(self, limit: int = 10, library_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recently added content.

        Args:
            limit: Maximum number of items to return
            library_name: Optional library name to filter by (e.g., 'Movies', 'TV Shows')
        """
        try:
            # If library_name is specified, get items from that specific library
            if library_name:
                libraries = await self.get_libraries()
                library = next((lib for lib in libraries if lib.get("title", "").lower() == library_name.lower()), None)
                if library:
                    response = await self._make_request(
                        "GET",
                        f"/library/sections/{library['key']}/recentlyAdded",
                        params={"X-Plex-Container-Size": str(limit)},
                    )
                else:
                    # Library not found, fall back to global recently added
                    response = await self._make_request(
                        "GET", "/library/recentlyAdded", params={"X-Plex-Container-Size": str(limit)}
                    )
            else:
                response = await self._make_request(
                    "GET", "/library/recentlyAdded", params={"X-Plex-Container-Size": str(limit)}
                )

            data = response.json()

            if "MediaContainer" not in data:
                return []

            metadata = data["MediaContainer"].get("Metadata", [])
            recent_items = []

            for item in metadata:
                recent_items.append(
                    {
                        "key": item.get("key"),
                        "title": item.get("title"),
                        "type": item.get("type"),
                        "year": item.get("year"),
                        "rating": item.get("rating"),
                        "duration": item.get("duration"),
                        "addedAt": item.get("addedAt"),
                        "updated_at": item.get("updatedAt"),
                        "thumb": item.get("thumb"),
                        "art": item.get("art"),
                        "librarySectionTitle": item.get("librarySectionTitle"),
                    }
                )

            return recent_items

        except Exception as e:
            self.logger.warning(f"Failed to get recently added: {e}")
            return []

    async def search_content(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for content in Plex."""
        try:
            response = await self._make_request("GET", "/search", params={"query": query, "limit": str(limit)})
            data = response.json()

            if "MediaContainer" not in data:
                return []

            metadata = data["MediaContainer"].get("Metadata", [])
            search_results = []

            for item in metadata:
                search_results.append(
                    {
                        "key": item.get("key"),
                        "title": item.get("title"),
                        "type": item.get("type"),
                        "year": item.get("year"),
                        "score": item.get("score"),
                        "library_section_title": item.get("librarySectionTitle"),
                        "thumb": item.get("thumb"),
                    }
                )

            return search_results

        except Exception as e:
            self.logger.warning(f"Failed to search content: {e}")
            return []

    async def search(self, query: str, media_type: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for content in Plex with optional media type filter.

        Args:
            query: Search query
            media_type: Optional filter (movie, show, episode, artist, album, track)
            limit: Maximum results to return
        """
        try:
            params = {"query": query, "limit": str(limit)}
            if media_type:
                # Map our media types to Plex types
                type_map = {"movie": 1, "show": 2, "episode": 4, "artist": 8, "album": 9, "track": 10}
                if media_type in type_map:
                    params["type"] = str(type_map[media_type])

            response = await self._make_request("GET", "/search", params=params)
            data = response.json()

            if "MediaContainer" not in data:
                return []

            metadata = data["MediaContainer"].get("Metadata", [])
            search_results = []

            for item in metadata:
                search_results.append(
                    {
                        "key": item.get("key"),
                        "title": item.get("title"),
                        "type": item.get("type"),
                        "year": item.get("year"),
                        "summary": item.get("summary"),
                        "rating": item.get("rating"),
                        "duration": item.get("duration"),
                        "contentRating": item.get("contentRating"),
                        "librarySectionTitle": item.get("librarySectionTitle"),
                        "thumb": item.get("thumb"),
                        "Genre": [g.get("tag") for g in item.get("Genre", [])],
                        "Director": [d.get("tag") for d in item.get("Director", [])],
                        "Role": [r.get("tag") for r in item.get("Role", [])],
                        "studio": item.get("studio"),
                        "addedAt": item.get("addedAt"),
                    }
                )

            return search_results

        except Exception as e:
            self.logger.warning(f"Failed to search: {e}")
            return []

    async def get_on_deck(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get On Deck items (continue watching).

        Args:
            limit: Maximum items to return
        """
        try:
            response = await self._make_request("GET", "/library/onDeck", params={"X-Plex-Container-Size": str(limit)})
            data = response.json()

            if "MediaContainer" not in data:
                return []

            metadata = data["MediaContainer"].get("Metadata", [])
            on_deck_items = []

            for item in metadata:
                on_deck_items.append(
                    {
                        "key": item.get("key"),
                        "title": item.get("title"),
                        "grandparentTitle": item.get("grandparentTitle"),  # Show name for episodes
                        "type": item.get("type"),
                        "year": item.get("year"),
                        "viewOffset": item.get("viewOffset", 0),
                        "duration": item.get("duration", 0),
                        "thumb": item.get("thumb"),
                        "art": item.get("art"),
                        "librarySectionTitle": item.get("librarySectionTitle"),
                    }
                )

            return on_deck_items

        except Exception as e:
            self.logger.warning(f"Failed to get on deck: {e}")
            return []

    def validate_config(self) -> List[str]:
        """Validate Plex-specific configuration."""
        errors = super().validate_config()

        # Check for required Plex token - try both api_key and config
        if not self.service_config.api_key and not self.get_config_value(self.token_config_key):
            errors.append("Plex token is required")

        return errors

    async def get_server_preferences(self) -> Dict[str, Any]:
        """Get server preferences and settings."""
        try:
            response = await self._make_request("GET", "/:/prefs")
            data = response.json()

            if "MediaContainer" not in data:
                return {}

            settings = data["MediaContainer"].get("Setting", [])
            preferences = {}

            for setting in settings:
                preferences[setting.get("id", "unknown")] = {
                    "label": setting.get("label"),
                    "summary": setting.get("summary"),
                    "type": setting.get("type"),
                    "default": setting.get("default"),
                    "value": setting.get("value"),
                    "hidden": setting.get("hidden", False),
                    "advanced": setting.get("advanced", False),
                }

            return preferences

        except Exception as e:
            self.logger.warning(f"Failed to get server preferences: {e}")
            return {}

    async def get_statistics(self) -> Dict[str, Any]:
        """Get server statistics."""
        try:
            # Get basic server info
            server_info = await self.get_service_info()

            # Get libraries count
            libraries = await self.get_libraries()

            # Get active sessions
            sessions = await self.get_sessions()

            # Get recent items
            recent = await self.get_recently_added(5)

            return {
                "server_info": server_info,
                "libraries_count": len(libraries),
                "active_sessions": len(sessions),
                "recent_additions": len(recent),
                "libraries": libraries,
                "sessions": sessions[:5],  # Limit for overview
                "recent_items": recent,
            }

        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                "error": str(e),
                "server_info": {},
                "libraries_count": 0,
                "active_sessions": 0,
                "recent_additions": 0,
            }
