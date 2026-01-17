"""Audiobookshelf audiobook/podcast server adapter."""

from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from .base import (
    ConnectionTestResult,
    ServiceCapability,
    TokenAuthAdapter,
)


class AudiobookshelfAdapter(TokenAuthAdapter):
    """Adapter for Audiobookshelf audiobook/podcast server.

    Uses Bearer token authentication via API token.
    """

    @property
    def service_type(self) -> str:
        return "audiobookshelf"

    def _get_item_url(self, item_id: str) -> str:
        """Generate Audiobookshelf web UI URL for a library item."""
        if item_id:
            return f"{self.public_url}/item/{item_id}"
        return ""

    def _get_library_url(self, library_id: str) -> str:
        """Generate Audiobookshelf web UI URL for a library."""
        if library_id:
            return f"{self.public_url}/library/{library_id}"
        return ""

    @property
    def supported_capabilities(self) -> List[ServiceCapability]:
        return [ServiceCapability.MEDIA_CONTENT, ServiceCapability.USER_MANAGEMENT, ServiceCapability.API_ACCESS]

    @property
    def token_config_key(self) -> str:
        return "audiobookshelf_api_token"

    def _format_token_header(self, token: str) -> Dict[str, str]:
        """Format Audiobookshelf Bearer token header."""
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}

    def _get_auth_header(self) -> Dict[str, str]:
        """Get auth header with Bearer token."""
        # Try API token from service_config.api_key first, then config
        api_token = self.service_config.api_key or self.get_config_value("api_key")
        if api_token:
            return self._format_token_header(api_token)

        # No auth configured
        return {"Content-Type": "application/json", "Accept": "application/json"}

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ):
        """Make HTTP request to Audiobookshelf API."""
        url = f"{self.base_url.rstrip('/')}{endpoint}"
        headers = self._get_auth_header()

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, params=params, json=json, headers=headers)
            response.raise_for_status()
            return response

    async def test_connection(self) -> ConnectionTestResult:
        """Test connection to Audiobookshelf."""
        start_time = datetime.utcnow()

        try:
            # First try ping endpoint (no auth required)
            response = await self._make_request("GET", "/ping")
            end_time = datetime.utcnow()
            response_time = int((end_time - start_time).total_seconds() * 1000)

            data = response.json()

            if data.get("success"):
                # Now verify auth by getting current user
                try:
                    me_response = await self._make_request("GET", "/api/me")
                    me_data = me_response.json()

                    return ConnectionTestResult(
                        success=True,
                        message="Successfully connected to Audiobookshelf",
                        response_time_ms=response_time,
                        details={
                            "status": "connected",
                            "user": me_data.get("username"),
                            "user_type": me_data.get("type"),
                            "is_active": me_data.get("isActive", False),
                        },
                    )
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 401:
                        return ConnectionTestResult(
                            success=False,
                            message="Server reachable but authentication failed - check API token",
                            response_time_ms=response_time,
                            details={"status": "auth_failed", "status_code": 401},
                        )
                    raise
            else:
                return ConnectionTestResult(
                    success=False,
                    message="Connected but response doesn't appear to be from Audiobookshelf",
                    response_time_ms=response_time,
                    details={"status": "invalid_response"},
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return ConnectionTestResult(
                    success=False,
                    message="Authentication failed - check API token",
                    details={"status": "auth_failed", "status_code": 401},
                )
            return ConnectionTestResult(
                success=False,
                message=f"HTTP error: {e.response.status_code}",
                details={"status": "http_error", "status_code": e.response.status_code},
            )
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                details={"status": "connection_failed", "error": str(e)},
            )

    async def get_service_info(self) -> Dict[str, Any]:
        """Get Audiobookshelf service information."""
        try:
            # Get server status
            status_response = await self._make_request("GET", "/api/status")
            status = status_response.json()

            # Get current user
            me_response = await self._make_request("GET", "/api/me")
            me = me_response.json()

            return {
                "service": "audiobookshelf",
                "version": status.get("serverVersion", "unknown"),
                "user": me.get("username"),
                "user_type": me.get("type"),
                "is_admin": me.get("type") == "root" or me.get("type") == "admin",
                "auth_methods": status.get("authMethods", []),
                "status": "online",
            }
        except Exception as e:
            return {"service": "audiobookshelf", "version": "unknown", "status": "error", "error": str(e)}

    async def get_libraries(self) -> List[Dict[str, Any]]:
        """Get list of libraries."""
        try:
            response = await self._make_request("GET", "/api/libraries")
            data = response.json()
            libraries = data.get("libraries", [])

            return [
                {
                    "id": lib.get("id"),
                    "name": lib.get("name"),
                    "media_type": lib.get("mediaType"),  # "book" or "podcast"
                    "folders": [f.get("fullPath") for f in lib.get("folders", [])],
                    "icon": lib.get("icon"),
                    "provider": lib.get("provider"),
                    "settings": {
                        "cover_aspect_ratio": lib.get("settings", {}).get("coverAspectRatio"),
                        "disable_watcher": lib.get("settings", {}).get("disableWatcher", False),
                    },
                    "url": self._get_library_url(lib.get("id")),
                }
                for lib in libraries
            ]
        except Exception as e:
            self.logger.error(f"Failed to get libraries: {e}")
            return []

    async def get_library_items(
        self,
        library_id: str,
        limit: int = 50,
        page: int = 0,
        sort: str = "media.metadata.title",
        filter_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get items from a library."""
        try:
            params = {"limit": limit, "page": page, "sort": sort}
            if filter_type:
                params["filter"] = filter_type

            response = await self._make_request("GET", f"/api/libraries/{library_id}/items", params=params)
            data = response.json()

            return {
                "total": data.get("total", 0),
                "page": data.get("page", 0),
                "items_per_page": data.get("itemsPerPage", limit),
                "items": [
                    {
                        "id": item.get("id"),
                        "title": item.get("media", {}).get("metadata", {}).get("title"),
                        "author": item.get("media", {}).get("metadata", {}).get("authorName"),
                        "narrator": item.get("media", {}).get("metadata", {}).get("narratorName"),
                        "series": item.get("media", {}).get("metadata", {}).get("seriesName"),
                        "duration": item.get("media", {}).get("duration", 0),
                        "num_chapters": len(item.get("media", {}).get("chapters", [])),
                        "num_audio_files": item.get("media", {}).get("numAudioFiles", 0),
                        "added_at": item.get("addedAt"),
                        "updated_at": item.get("updatedAt"),
                        "url": self._get_item_url(item.get("id")),
                    }
                    for item in data.get("results", [])
                ],
            }
        except Exception as e:
            self.logger.error(f"Failed to get library items: {e}")
            return {"total": 0, "page": 0, "items_per_page": limit, "items": []}

    async def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific item (audiobook/podcast)."""
        try:
            response = await self._make_request("GET", f"/api/items/{item_id}")
            item = response.json()
            media = item.get("media", {})
            metadata = media.get("metadata", {})

            return {
                "id": item.get("id"),
                "library_id": item.get("libraryId"),
                "title": metadata.get("title"),
                "subtitle": metadata.get("subtitle"),
                "author": metadata.get("authorName"),
                "narrator": metadata.get("narratorName"),
                "series": metadata.get("seriesName"),
                "description": metadata.get("description"),
                "publisher": metadata.get("publisher"),
                "publish_year": metadata.get("publishedYear"),
                "language": metadata.get("language"),
                "isbn": metadata.get("isbn"),
                "asin": metadata.get("asin"),
                "genres": metadata.get("genres", []),
                "tags": media.get("tags", []),
                "duration": media.get("duration", 0),
                "size": item.get("size", 0),
                "num_chapters": len(media.get("chapters", [])),
                "num_audio_files": media.get("numAudioFiles", 0),
                "chapters": [
                    {"id": ch.get("id"), "title": ch.get("title"), "start": ch.get("start"), "end": ch.get("end")}
                    for ch in media.get("chapters", [])
                ],
                "added_at": item.get("addedAt"),
                "updated_at": item.get("updatedAt"),
            }
        except Exception as e:
            self.logger.error(f"Failed to get item: {e}")
            return None

    async def search(self, library_id: str, query: str, limit: int = 25) -> Dict[str, Any]:
        """Search for items in a library with detailed results."""
        try:
            response = await self._make_request(
                "GET", f"/api/libraries/{library_id}/search", params={"q": query, "limit": limit}
            )
            data = response.json()

            books = []
            for item in data.get("book", []):
                lib_item = item.get("libraryItem", {})
                media = lib_item.get("media", {})
                metadata = media.get("metadata", {})
                books.append(
                    {
                        "id": lib_item.get("id"),
                        "title": metadata.get("title"),
                        "subtitle": metadata.get("subtitle"),
                        "author": metadata.get("authorName"),
                        "narrator": metadata.get("narratorName"),
                        "series": metadata.get("seriesName"),
                        "description": metadata.get("description"),
                        "publisher": metadata.get("publisher"),
                        "publish_year": metadata.get("publishedYear"),
                        "language": metadata.get("language"),
                        "genres": metadata.get("genres", []),
                        "duration": media.get("duration", 0),
                        "num_chapters": len(media.get("chapters", [])),
                        "num_audio_files": media.get("numAudioFiles", 0),
                        "match_key": item.get("matchKey"),
                        "match_text": item.get("matchText"),
                        "url": self._get_item_url(lib_item.get("id")),
                    }
                )

            podcasts = []
            for item in data.get("podcast", []):
                lib_item = item.get("libraryItem", {})
                media = lib_item.get("media", {})
                metadata = media.get("metadata", {})
                podcasts.append(
                    {
                        "id": lib_item.get("id"),
                        "title": metadata.get("title"),
                        "author": metadata.get("author"),
                        "description": metadata.get("description"),
                        "release_date": metadata.get("releaseDate"),
                        "language": metadata.get("language"),
                        "genres": metadata.get("genres", []),
                        "num_episodes": media.get("numEpisodes", 0),
                        "match_key": item.get("matchKey"),
                        "match_text": item.get("matchText"),
                        "url": self._get_item_url(lib_item.get("id")),
                    }
                )

            return {
                "book": books,
                "podcast": podcasts,
                "authors": [{"id": a.get("id"), "name": a.get("name")} for a in data.get("authors", [])],
                "series": [
                    {
                        "id": s.get("series", {}).get("id"),
                        "name": s.get("series", {}).get("name"),
                        "num_books": len(s.get("books", [])),
                    }
                    for s in data.get("series", [])
                ],
            }
        except Exception as e:
            self.logger.error(f"Failed to search: {e}")
            return {"book": [], "podcast": [], "authors": [], "series": []}

    async def get_users(self) -> List[Dict[str, Any]]:
        """Get list of users (admin only)."""
        try:
            response = await self._make_request("GET", "/api/users")
            data = response.json()
            # API returns {"users": [...]} not a direct array
            users = data.get("users", []) if isinstance(data, dict) else data

            return [
                {
                    "id": user.get("id"),
                    "username": user.get("username"),
                    "type": user.get("type"),  # "root", "admin", "user", "guest"
                    "is_active": user.get("isActive", False),
                    "is_locked": user.get("isLocked", False),
                    "created_at": user.get("createdAt"),
                    "libraries_allowed": user.get("librariesAccessible", []),
                    "permissions": user.get("permissions", {}),
                }
                for user in users
            ]
        except Exception as e:
            self.logger.error(f"Failed to get users: {e}")
            return []

    async def get_listening_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get listening sessions."""
        try:
            endpoint = f"/api/users/{user_id}/listening-sessions" if user_id else "/api/me/listening-sessions"
            response = await self._make_request("GET", endpoint)
            data = response.json()
            sessions = data.get("sessions", [])

            return [
                {
                    "id": session.get("id"),
                    "user_id": session.get("userId"),
                    "library_item_id": session.get("libraryItemId"),
                    "display_title": session.get("displayTitle"),
                    "display_author": session.get("displayAuthor"),
                    "duration": session.get("duration"),
                    "play_method": session.get("playMethod"),
                    "device_info": session.get("deviceInfo", {}),
                    "started_at": session.get("startedAt"),
                    "updated_at": session.get("updatedAt"),
                }
                for session in sessions
            ]
        except Exception as e:
            self.logger.error(f"Failed to get listening sessions: {e}")
            return []

    async def get_listening_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get listening statistics for a user."""
        try:
            endpoint = f"/api/users/{user_id}/listening-stats" if user_id else "/api/me/listening-stats"
            response = await self._make_request("GET", endpoint)
            data = response.json()

            return {
                "total_time": data.get("totalTime", 0),
                "items": [
                    {
                        "id": item.get("id"),
                        "media_metadata": item.get("mediaMetadata", {}),
                        "min_since_update": item.get("minSinceUpdate"),
                        "recently_listened": item.get("recentlyListened"),
                    }
                    for item in data.get("items", [])
                ],
                "days": data.get("days", {}),
                "day_of_week": data.get("dayOfWeek", {}),
                "today": data.get("today", 0),
                "recent_sessions": data.get("recentSessions", []),
            }
        except Exception as e:
            self.logger.error(f"Failed to get listening stats: {e}")
            return {"total_time": 0, "items": [], "days": {}, "day_of_week": {}, "today": 0}

    async def get_media_progress(
        self, library_item_id: str, episode_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get media progress for a library item."""
        try:
            if episode_id:
                endpoint = f"/api/me/progress/{library_item_id}/{episode_id}"
            else:
                endpoint = f"/api/me/progress/{library_item_id}"

            response = await self._make_request("GET", endpoint)
            progress = response.json()

            return {
                "id": progress.get("id"),
                "library_item_id": progress.get("libraryItemId"),
                "episode_id": progress.get("episodeId"),
                "duration": progress.get("duration", 0),
                "progress": progress.get("progress", 0),  # 0-1 percentage
                "current_time": progress.get("currentTime", 0),
                "is_finished": progress.get("isFinished", False),
                "hide_from_continue_listening": progress.get("hideFromContinueListening", False),
                "started_at": progress.get("startedAt"),
                "finished_at": progress.get("finishedAt"),
                "last_update": progress.get("lastUpdate"),
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None  # No progress for this item
            raise
        except Exception as e:
            self.logger.error(f"Failed to get media progress: {e}")
            return None

    async def get_statistics(self) -> Dict[str, Any]:
        """Get Audiobookshelf statistics."""
        try:
            libraries = await self.get_libraries()

            total_books = 0
            total_podcasts = 0
            total_duration = 0

            for lib in libraries:
                items = await self.get_library_items(lib["id"], limit=10000)
                if lib["media_type"] == "book":
                    total_books += items["total"]
                else:
                    total_podcasts += items["total"]
                for item in items["items"]:
                    total_duration += item.get("duration", 0)

            # Get listening stats for current user
            listening_stats = await self.get_listening_stats()

            return {
                "total_libraries": len(libraries),
                "total_books": total_books,
                "total_podcasts": total_podcasts,
                "total_duration_hours": round(total_duration / 3600, 2),
                "listening_time_hours": round(listening_stats.get("total_time", 0) / 3600, 2),
                "listened_today_hours": round(listening_stats.get("today", 0) / 3600, 2),
            }
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                "total_libraries": 0,
                "total_books": 0,
                "total_podcasts": 0,
                "total_duration_hours": 0,
                "listening_time_hours": 0,
                "listened_today_hours": 0,
            }

    async def scan_library(self, library_id: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
        """Trigger a library scan in Audiobookshelf.

        Args:
            library_id: Optional library ID to scan. If not provided, scans all libraries.
            force: Force scan even for unchanged files.

        Returns:
            Dict with scan status and scanned libraries info.
        """
        try:
            libraries = await self.get_libraries()

            if not libraries:
                return {"success": False, "error": "No libraries found in Audiobookshelf"}

            scanned = []
            errors = []

            if library_id:
                # Scan specific library
                library = next((lib for lib in libraries if lib.get("id") == library_id), None)
                if not library:
                    available = [{"id": lib.get("id"), "name": lib.get("name")} for lib in libraries]
                    return {
                        "success": False,
                        "error": f"Library with ID '{library_id}' not found",
                        "available_libraries": available,
                    }
                libraries_to_scan = [library]
            else:
                # Scan all libraries
                libraries_to_scan = libraries

            for library in libraries_to_scan:
                lib_id = library.get("id")
                lib_name = library.get("name")
                try:
                    # Trigger scan - POST /api/libraries/{id}/scan
                    params = {"force": "1" if force else "0"}
                    await self._make_request("POST", f"/api/libraries/{lib_id}/scan", params=params)
                    scanned.append({
                        "id": lib_id,
                        "name": lib_name,
                        "status": "scan_started",
                        "force": force,
                    })
                except Exception as e:
                    errors.append({
                        "library": lib_name,
                        "error": str(e),
                    })

            return {
                "success": len(scanned) > 0,
                "scanned_libraries": scanned,
                "total_scanned": len(scanned),
                "errors": errors if errors else None,
                "message": f"Scan started for {len(scanned)} library(ies)" if scanned else "No libraries scanned",
            }

        except Exception as e:
            self.logger.error(f"Failed to scan library: {e}")
            return {"success": False, "error": str(e)}

    async def update_media_progress(
        self,
        library_item_id: str,
        current_time: float,
        duration: Optional[float] = None,
        is_finished: bool = False,
        episode_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update listening progress for a library item.

        Args:
            library_item_id: The library item ID
            current_time: Current position in seconds
            duration: Total duration in seconds (optional)
            is_finished: Whether the item is finished
            episode_id: Episode ID for podcasts (optional)

        Returns:
            Dict with success status and updated progress info
        """
        try:
            # Get item info first
            item = await self.get_item(library_item_id)
            if not item:
                return {"success": False, "error": f"Item with ID {library_item_id} not found"}

            title = item.get("title", library_item_id)
            total_duration = duration or item.get("duration", 0)

            # Calculate progress percentage
            progress = current_time / total_duration if total_duration > 0 else 0
            if is_finished:
                progress = 1.0
                current_time = total_duration

            # Build the request payload
            payload = {
                "currentTime": current_time,
                "progress": progress,
                "isFinished": is_finished,
            }

            if duration:
                payload["duration"] = duration

            # Update progress
            if episode_id:
                endpoint = f"/api/me/progress/{library_item_id}/{episode_id}"
            else:
                endpoint = f"/api/me/progress/{library_item_id}"

            await self._make_request("PATCH", endpoint, json=payload)

            return {
                "success": True,
                "message": f"Progress updated for '{title}'",
                "library_item_id": library_item_id,
                "title": title,
                "current_time": current_time,
                "duration": total_duration,
                "progress_percent": round(progress * 100, 2),
                "is_finished": is_finished,
                "url": self._get_item_url(library_item_id),
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"success": False, "error": f"Item with ID {library_item_id} not found"}
            return {"success": False, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            self.logger.error(f"Failed to update media progress: {e}")
            return {"success": False, "error": str(e)}

    async def mark_item_finished(self, library_item_id: str, episode_id: Optional[str] = None) -> Dict[str, Any]:
        """Mark a library item as finished/completed.

        Args:
            library_item_id: The library item ID
            episode_id: Episode ID for podcasts (optional)

        Returns:
            Dict with success status
        """
        try:
            # Get item info
            item = await self.get_item(library_item_id)
            if not item:
                return {"success": False, "error": f"Item with ID {library_item_id} not found"}

            duration = item.get("duration", 0)

            return await self.update_media_progress(
                library_item_id=library_item_id,
                current_time=duration,
                duration=duration,
                is_finished=True,
                episode_id=episode_id,
            )

        except Exception as e:
            self.logger.error(f"Failed to mark item as finished: {e}")
            return {"success": False, "error": str(e)}

    async def clear_item_progress(self, library_item_id: str, episode_id: Optional[str] = None) -> Dict[str, Any]:
        """Clear/reset progress for a library item.

        Args:
            library_item_id: The library item ID
            episode_id: Episode ID for podcasts (optional)

        Returns:
            Dict with success status
        """
        try:
            # Get item info
            item = await self.get_item(library_item_id)
            if not item:
                return {"success": False, "error": f"Item with ID {library_item_id} not found"}

            # Reset progress to 0
            return await self.update_media_progress(
                library_item_id=library_item_id,
                current_time=0,
                is_finished=False,
                episode_id=episode_id,
            )

        except Exception as e:
            self.logger.error(f"Failed to clear item progress: {e}")
            return {"success": False, "error": str(e)}
