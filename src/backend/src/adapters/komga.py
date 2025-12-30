"""Komga comic/manga server adapter."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx
import base64

from .base import (
    TokenAuthAdapter,
    ServiceCapability,
    ConnectionTestResult,
    AdapterError,
    AuthenticationError
)


class KomgaAdapter(TokenAuthAdapter):
    """Adapter for Komga comic/manga server.

    Supports both API key authentication (preferred) and basic auth (username/password).
    """

    @property
    def service_type(self) -> str:
        return "komga"

    @property
    def supported_capabilities(self) -> List[ServiceCapability]:
        return [
            ServiceCapability.MEDIA_CONTENT,
            ServiceCapability.USER_MANAGEMENT,
            ServiceCapability.API_ACCESS
        ]

    @property
    def token_config_key(self) -> str:
        return "komga_api_key"

    def _format_token_header(self, token: str) -> Dict[str, str]:
        """Format Komga API key header."""
        return {
            "X-API-Key": token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _get_auth_header(self) -> Dict[str, str]:
        """Get auth header - tries API key first, then falls back to basic auth."""
        # Try API key first - check service_config.api_key first, then config
        api_key = self.service_config.api_key or self.get_config_value("api_key")
        if api_key:
            return self._format_token_header(api_key)

        # Fall back to basic auth
        username = getattr(self.service_config, 'username', None) or self.get_config_value("username") or ""
        password = getattr(self.service_config, 'password', None) or self.get_config_value("password") or ""

        if username and password:
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            return {
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

        # No auth configured
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ):
        """Make HTTP request to Komga API."""
        url = f"{self.base_url.rstrip('/')}{endpoint}"
        headers = self._get_auth_header()

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method,
                url,
                params=params,
                json=json,
                headers=headers
            )
            response.raise_for_status()
            return response

    async def test_connection(self) -> ConnectionTestResult:
        """Test connection to Komga."""
        start_time = datetime.utcnow()

        try:
            response = await self._make_request("GET", "/api/v2/users/me")
            end_time = datetime.utcnow()
            response_time = int((end_time - start_time).total_seconds() * 1000)

            data = response.json()

            if "id" in data:
                return ConnectionTestResult(
                    success=True,
                    message="Successfully connected to Komga",
                    response_time_ms=response_time,
                    details={
                        "status": "connected",
                        "user": data.get("email"),
                        "roles": data.get("roles", [])
                    }
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message="Connected but response doesn't appear to be from Komga",
                    response_time_ms=response_time,
                    details={"status": "invalid_response"}
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return ConnectionTestResult(
                    success=False,
                    message="Authentication failed - check API key or credentials",
                    details={"status": "auth_failed", "status_code": 401}
                )
            return ConnectionTestResult(
                success=False,
                message=f"HTTP error: {e.response.status_code}",
                details={"status": "http_error", "status_code": e.response.status_code}
            )
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                details={"status": "connection_failed", "error": str(e)}
            )

    async def get_service_info(self) -> Dict[str, Any]:
        """Get Komga service information."""
        try:
            # Get server info
            response = await self._make_request("GET", "/api/v1/actuator/info")
            info = response.json()

            # Get current user
            user_response = await self._make_request("GET", "/api/v2/users/me")
            user = user_response.json()

            return {
                "service": "komga",
                "version": info.get("build", {}).get("version", "unknown"),
                "user": user.get("email"),
                "is_admin": "ADMIN" in user.get("roles", []),
                "status": "online"
            }
        except Exception as e:
            return {
                "service": "komga",
                "version": "unknown",
                "status": "error",
                "error": str(e)
            }

    async def get_libraries(self) -> List[Dict[str, Any]]:
        """Get list of libraries."""
        try:
            response = await self._make_request("GET", "/api/v1/libraries")
            libraries = response.json()

            return [
                {
                    "id": lib.get("id"),
                    "name": lib.get("name"),
                    "root": lib.get("root"),
                    "unavailable_date": lib.get("unavailableDate")
                }
                for lib in libraries
            ]
        except Exception as e:
            self.logger.error(f"Failed to get libraries: {e}")
            return []

    async def get_series(self, library_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of series."""
        try:
            params = {"size": limit, "sort": "metadata.titleSort,asc"}
            if library_id:
                params["library_id"] = library_id

            response = await self._make_request("GET", "/api/v1/series", params=params)
            data = response.json()

            return [
                {
                    "id": series.get("id"),
                    "name": series.get("metadata", {}).get("title", series.get("name")),
                    "library_id": series.get("libraryId"),
                    "books_count": series.get("booksCount", 0),
                    "books_read_count": series.get("booksReadCount", 0),
                    "books_unread_count": series.get("booksUnreadCount", 0),
                    "status": series.get("metadata", {}).get("status"),
                    "publisher": series.get("metadata", {}).get("publisher"),
                    "genres": series.get("metadata", {}).get("genres", [])
                }
                for series in data.get("content", [])
            ]
        except Exception as e:
            self.logger.error(f"Failed to get series: {e}")
            return []

    async def get_books(self, series_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of books."""
        try:
            endpoint = f"/api/v1/series/{series_id}/books" if series_id else "/api/v1/books"
            params = {"size": limit}

            response = await self._make_request("GET", endpoint, params=params)
            data = response.json()

            return [
                {
                    "id": book.get("id"),
                    "name": book.get("metadata", {}).get("title", book.get("name")),
                    "series_id": book.get("seriesId"),
                    "number": book.get("metadata", {}).get("number"),
                    "pages_count": book.get("media", {}).get("pagesCount", 0),
                    "size_bytes": book.get("sizeBytes", 0),
                    "read_progress": book.get("readProgress", {}).get("page", 0),
                    "completed": book.get("readProgress", {}).get("completed", False)
                }
                for book in data.get("content", [])
            ]
        except Exception as e:
            self.logger.error(f"Failed to get books: {e}")
            return []

    async def search(self, query: str) -> Dict[str, Any]:
        """Search for series and books."""
        try:
            response = await self._make_request("GET", "/api/v1/search", params={"q": query})
            data = response.json()

            return {
                "series": [
                    {
                        "id": s.get("id"),
                        "name": s.get("metadata", {}).get("title", s.get("name")),
                        "books_count": s.get("booksCount", 0)
                    }
                    for s in data.get("series", {}).get("content", [])[:10]
                ],
                "books": [
                    {
                        "id": b.get("id"),
                        "name": b.get("metadata", {}).get("title", b.get("name")),
                        "series_id": b.get("seriesId")
                    }
                    for b in data.get("books", {}).get("content", [])[:10]
                ]
            }
        except Exception as e:
            self.logger.error(f"Failed to search: {e}")
            return {"series": [], "books": []}

    async def get_users(self) -> List[Dict[str, Any]]:
        """Get list of users."""
        try:
            response = await self._make_request("GET", "/api/v2/users")
            users = response.json()

            return [
                {
                    "id": user.get("id"),
                    "email": user.get("email"),
                    "username": user.get("email"),
                    "name": user.get("email").split("@")[0] if user.get("email") else "Unknown",
                    "roles": user.get("roles", []),
                    "shared_libraries_ids": user.get("sharedLibrariesIds", [])
                }
                for user in users
            ]
        except Exception as e:
            self.logger.error(f"Failed to get users: {e}")
            return []

    async def get_statistics(self) -> Dict[str, Any]:
        """Get Komga statistics."""
        try:
            libraries = await self.get_libraries()
            series = await self.get_series(limit=10000)

            total_books = sum(s.get("books_count", 0) for s in series)
            total_read = sum(s.get("books_read_count", 0) for s in series)
            total_unread = sum(s.get("books_unread_count", 0) for s in series)

            return {
                "total_libraries": len(libraries),
                "total_series": len(series),
                "total_books": total_books,
                "books_read": total_read,
                "books_unread": total_unread,
                "completion_rate": round(total_read / total_books * 100, 2) if total_books > 0 else 0
            }
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                "total_libraries": 0,
                "total_series": 0,
                "total_books": 0,
                "books_read": 0,
                "books_unread": 0,
                "completion_rate": 0
            }
