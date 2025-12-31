"""Overseerr request management adapter."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

from .base import (
    AdapterError,
    AuthenticationError,
    ConnectionTestResult,
    ServiceCapability,
    TokenAuthAdapter,
)


class RequestStatus(Enum):
    """Overseerr request status."""

    PENDING = 1
    APPROVED = 2
    DECLINED = 3
    AVAILABLE = 4


class MediaType(Enum):
    """Media type."""

    MOVIE = "movie"
    TV = "tv"


class OverseerrAdapter(TokenAuthAdapter):
    """Adapter for Overseerr request management system."""

    @property
    def service_type(self) -> str:
        return "overseerr"

    @property
    def supported_capabilities(self) -> List[ServiceCapability]:
        return [ServiceCapability.MEDIA_CONTENT, ServiceCapability.USER_MANAGEMENT, ServiceCapability.API_ACCESS]

    @property
    def token_config_key(self) -> str:
        return "overseerr_api_key"

    def _format_token_header(self, token: str) -> Dict[str, str]:
        """Format Overseerr API key header."""
        return {"X-Api-Key": token, "Content-Type": "application/json", "Accept": "application/json"}

    async def test_connection(self) -> ConnectionTestResult:
        """Test connection to Overseerr."""
        start_time = datetime.utcnow()

        try:
            # Test basic connectivity and auth
            response = await self._make_request("GET", "/api/v1/status")

            end_time = datetime.utcnow()
            response_time = int((end_time - start_time).total_seconds() * 1000)

            data = response.json()

            if "version" in data:
                return ConnectionTestResult(
                    success=True,
                    message="Successfully connected to Overseerr",
                    response_time_ms=response_time,
                    details={
                        "status": "connected",
                        "version": data.get("version"),
                        "commit_tag": data.get("commitTag"),
                    },
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message="Connected but response doesn't appear to be from Overseerr",
                    response_time_ms=response_time,
                    details={"status": "invalid_response"},
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return ConnectionTestResult(
                    success=False,
                    message="Authentication failed - check API key",
                    details={"status": "auth_failed", "status_code": 401},
                )
            elif e.response.status_code == 403:
                return ConnectionTestResult(
                    success=False,
                    message="Access denied - insufficient permissions",
                    details={"status": "access_denied", "status_code": 403},
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
        """Get Overseerr service information."""
        try:
            # Get status info
            status_response = await self._make_request("GET", "/api/v1/status")
            status_data = status_response.json()

            # Get settings info
            settings_data = await self._safe_request("GET", "/api/v1/settings/main")

            return {
                "service": "overseerr",
                "version": status_data.get("version"),
                "commit_tag": status_data.get("commitTag"),
                "build_id": status_data.get("buildId"),
                "repository": status_data.get("repository"),
                "application_title": settings_data.get("applicationTitle", "Overseerr")
                if settings_data
                else "Overseerr",
                "application_url": settings_data.get("applicationUrl") if settings_data else None,
                "trust_proxy": settings_data.get("trustProxy", False) if settings_data else False,
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid Overseerr API key") from e
            raise AdapterError(f"HTTP error: {e.response.status_code}") from e
        except Exception as e:
            raise AdapterError(f"Failed to get service info: {str(e)}") from e

    async def _get_media_title(self, media_type: str, tmdb_id: int) -> Optional[str]:
        """Get media title from TMDB ID by calling Overseerr's media endpoint."""
        if not tmdb_id:
            return None
        try:
            endpoint = f"/api/v1/{'movie' if media_type == 'movie' else 'tv'}/{tmdb_id}"
            # _safe_request returns JSON dict directly, not an HTTP response
            data = await self._safe_request("GET", endpoint)
            if data:
                # Movies have 'title', TV shows have 'name'
                return data.get("title") or data.get("name")
        except Exception as e:
            self.logger.debug(f"Failed to get media title for {media_type}/{tmdb_id}: {e}")
        return None

    async def get_requests(
        self, take: int = 20, skip: int = 0, status: Optional[RequestStatus] = None
    ) -> Dict[str, Any]:
        """Get media requests."""
        try:
            params = {"take": str(take), "skip": str(skip)}
            if status:
                params["filter"] = status.value

            response = await self._make_request("GET", "/api/v1/request", params=params)
            data = response.json()

            # Process requests to add user-friendly information
            requests = []
            for request in data.get("results", []):
                media = request.get("media", {})
                media_type = request.get("type")
                tmdb_id = media.get("tmdbId")

                # Get title from TMDB ID
                title = await self._get_media_title(media_type, tmdb_id)

                processed_request = {
                    "id": request.get("id"),
                    "status": request.get("status"),
                    "status_name": self._get_status_name(request.get("status")),
                    "media_type": media_type,
                    "created_at": request.get("createdAt"),
                    "updated_at": request.get("updatedAt"),
                    "requested_by": request.get("requestedBy", {}).get("displayName"),
                    "requested_by_id": request.get("requestedBy", {}).get("id"),
                    "media_info": {**self._extract_media_info(media), "title": title},  # Add title from TMDB lookup
                }

                # Add seasons for TV shows
                if request.get("seasons"):
                    processed_request["seasons"] = [
                        {
                            "id": season.get("id"),
                            "season_number": season.get("seasonNumber"),
                            "status": season.get("status"),
                        }
                        for season in request.get("seasons", [])
                    ]

                requests.append(processed_request)

            return {
                "results": requests,
                "page_info": {
                    "pages": data.get("pageInfo", {}).get("pages", 1),
                    "page_size": data.get("pageInfo", {}).get("pageSize", take),
                    "results": data.get("pageInfo", {}).get("results", len(requests)),
                    "page": data.get("pageInfo", {}).get("page", 1),
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to get requests: {e}")
            return {"results": [], "page_info": {}}

    async def get_users(self) -> List[Dict[str, Any]]:
        """Get Overseerr users."""
        try:
            response = await self._make_request("GET", "/api/v1/user")
            data = response.json()

            users = []
            for user in data.get("results", []):
                display_name = user.get("displayName") or user.get("username") or user.get("email", "").split("@")[0]
                users.append(
                    {
                        "id": user.get("id"),
                        "email": user.get("email"),
                        "display_name": display_name,
                        "friendly_name": display_name,  # Alias for matching
                        "username": user.get("username") or display_name,
                        "name": display_name,  # Alias for matching
                        "user_type": user.get("userType"),
                        "permissions": user.get("permissions"),
                        "avatar": user.get("avatar"),
                        "created_at": user.get("createdAt"),
                        "updated_at": user.get("updatedAt"),
                        "request_count": user.get("requestCount", 0),
                        "movie_quota_limit": user.get("movieQuotaLimit"),
                        "movie_quota_days": user.get("movieQuotaDays"),
                        "tv_quota_limit": user.get("tvQuotaLimit"),
                        "tv_quota_days": user.get("tvQuotaDays"),
                    }
                )

            return users

        except Exception as e:
            self.logger.warning(f"Failed to get users: {e}")
            return []

    async def get_request_by_id(self, request_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific request by ID."""
        try:
            response = await self._make_request("GET", f"/api/v1/request/{request_id}")
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            self.logger.warning(f"Failed to get request {request_id}: {e}")
            return None

    async def approve_request(self, request_id: int) -> bool:
        """Approve a media request."""
        try:
            response = await self._make_request("POST", f"/api/v1/request/{request_id}/approve")
            return response.status_code == 200

        except Exception as e:
            self.logger.error(f"Failed to approve request {request_id}: {e}")
            return False

    async def decline_request(self, request_id: int, reason: Optional[str] = None) -> bool:
        """Decline a media request."""
        try:
            data = {}
            if reason:
                data["reason"] = reason

            response = await self._make_request("POST", f"/api/v1/request/{request_id}/decline", json=data)
            return response.status_code == 200

        except Exception as e:
            self.logger.error(f"Failed to decline request {request_id}: {e}")
            return False

    async def search_media(self, query: str, media_type: Optional[MediaType] = None) -> List[Dict[str, Any]]:
        """Search for media in Overseerr."""
        try:
            endpoint = "/api/v1/search"
            if media_type:
                endpoint = f"/api/v1/search/{media_type.value}"

            params = {"query": query}
            response = await self._make_request("GET", endpoint, params=params)
            data = response.json()

            search_results = []
            for result in data.get("results", []):
                search_results.append(
                    {
                        "id": result.get("id"),
                        "media_type": result.get("mediaType"),
                        "title": result.get("title") or result.get("name"),
                        "overview": result.get("overview"),
                        "release_date": result.get("releaseDate") or result.get("firstAirDate"),
                        "poster_path": result.get("posterPath"),
                        "backdrop_path": result.get("backdropPath"),
                        "vote_average": result.get("voteAverage"),
                        "genre_ids": result.get("genreIds", []),
                        "media_info": result.get("mediaInfo"),
                    }
                )

            return search_results

        except Exception as e:
            self.logger.warning(f"Failed to search media: {e}")
            return []

    async def get_statistics(self) -> Dict[str, Any]:
        """Get request statistics."""
        try:
            # Get recent requests
            requests_data = await self.get_requests(take=50)

            # Get users count
            users = await self.get_users()

            # Calculate statistics
            total_requests = len(requests_data.get("results", []))
            pending_count = sum(
                1 for r in requests_data.get("results", []) if r.get("status") == RequestStatus.PENDING.value
            )
            approved_count = sum(
                1 for r in requests_data.get("results", []) if r.get("status") == RequestStatus.APPROVED.value
            )
            available_count = sum(
                1 for r in requests_data.get("results", []) if r.get("status") == RequestStatus.AVAILABLE.value
            )

            return {
                "total_requests": total_requests,
                "pending_requests": pending_count,
                "approved_requests": approved_count,
                "available_requests": available_count,
                "declined_requests": total_requests - pending_count - approved_count - available_count,
                "total_users": len(users),
                "recent_requests": requests_data.get("results", [])[:10],
            }

        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                "total_requests": 0,
                "pending_requests": 0,
                "approved_requests": 0,
                "available_requests": 0,
                "declined_requests": 0,
                "total_users": 0,
                "recent_requests": [],
            }

    def _get_status_name(self, status: int) -> str:
        """Get human-readable status name."""
        status_map = {
            RequestStatus.PENDING.value: "Pending",
            RequestStatus.APPROVED.value: "Approved",
            RequestStatus.DECLINED.value: "Declined",
            RequestStatus.AVAILABLE.value: "Available",
        }
        return status_map.get(status, "Unknown")

    def _extract_media_info(self, media: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant media information."""
        if not media:
            return {}

        return {
            "id": media.get("id"),
            "media_type": media.get("mediaType"),
            "tmdb_id": media.get("tmdbId"),
            "imdb_id": media.get("imdbId"),
            "tvdb_id": media.get("tvdbId"),
            "status": media.get("status"),
            "created_at": media.get("createdAt"),
            "updated_at": media.get("updatedAt"),
        }

    def validate_config(self) -> List[str]:
        """Validate Overseerr-specific configuration."""
        errors = super().validate_config()

        # Check for required API key
        if not self.get_config_value(self.token_config_key):
            errors.append("Overseerr API key is required")

        return errors

    async def get_trending(self, media_type: str = "all", limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending movies and TV shows."""
        try:
            results = []

            # Fetch trending movies
            if media_type in ["all", "movie"]:
                response = await self._make_request("GET", "/api/v1/discover/movies")
                data = response.json()
                for item in data.get("results", [])[:limit]:
                    item["mediaType"] = "movie"
                    results.append(item)

            # Fetch trending TV shows
            if media_type in ["all", "tv"]:
                response = await self._make_request("GET", "/api/v1/discover/tv")
                data = response.json()
                for item in data.get("results", [])[:limit]:
                    item["mediaType"] = "tv"
                    results.append(item)

            # Limit total results if fetching both
            if media_type == "all":
                results = results[:limit]

            return results

        except Exception as e:
            self.logger.warning(f"Failed to get trending: {e}")
            return []

    async def get_settings(self) -> Dict[str, Any]:
        """Get Overseerr settings."""
        try:
            settings = {}

            # Get main settings
            main_settings = await self._safe_request("GET", "/api/v1/settings/main")
            if main_settings:
                settings["main"] = main_settings

            # Get Plex settings
            plex_settings = await self._safe_request("GET", "/api/v1/settings/plex")
            if plex_settings:
                settings["plex"] = plex_settings

            # Get notification settings
            notifications = await self._safe_request("GET", "/api/v1/settings/notifications")
            if notifications:
                settings["notifications"] = notifications

            return settings

        except Exception as e:
            self.logger.warning(f"Failed to get settings: {e}")
            return {}
