"""Authentik identity provider adapter."""

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


class UserStatus(Enum):
    """User status in Authentik."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class AuthentikAdapter(TokenAuthAdapter):
    """Adapter for Authentik identity provider."""

    @property
    def service_type(self) -> str:
        return "authentik"

    @property
    def supported_capabilities(self) -> List[ServiceCapability]:
        return [ServiceCapability.AUTHENTICATION, ServiceCapability.USER_MANAGEMENT, ServiceCapability.API_ACCESS]

    @property
    def token_config_key(self) -> str:
        return "authentik_token"

    def _format_token_header(self, token: str) -> Dict[str, str]:
        """Format Authentik token header."""
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}

    async def test_connection(self) -> ConnectionTestResult:
        """Test connection to Authentik."""
        start_time = datetime.utcnow()

        try:
            # Test basic connectivity and auth by getting current user
            response = await self._make_request("GET", "/api/v3/core/users/me/")

            end_time = datetime.utcnow()
            response_time = int((end_time - start_time).total_seconds() * 1000)

            data = response.json()

            # Handle both old format (direct user data) and new format (wrapped in "user" key)
            user_data = data.get("user", data)

            if "pk" in user_data and "username" in user_data:
                return ConnectionTestResult(
                    success=True,
                    message="Successfully connected to Authentik",
                    response_time_ms=response_time,
                    details={
                        "status": "connected",
                        "user_pk": user_data.get("pk"),
                        "username": user_data.get("username"),
                        "is_superuser": user_data.get("is_superuser", False),
                    },
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message="Connected but response doesn't appear to be from Authentik",
                    response_time_ms=response_time,
                    details={"status": "invalid_response"},
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return ConnectionTestResult(
                    success=False,
                    message="Authentication failed - check token",
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
        """Get Authentik service information."""
        try:
            # Get current user info
            user_response = await self._make_request("GET", "/api/v3/core/users/me/")
            user_data = user_response.json()

            # Get version info
            version_data = await self._safe_request("GET", "/api/v3/admin/version/")

            # Get system info
            system_data = await self._safe_request("GET", "/api/v3/admin/system/")

            return {
                "service": "authentik",
                "version": version_data.get("version_current") if version_data else "unknown",
                "version_latest": version_data.get("version_latest") if version_data else None,
                "outdated": version_data.get("outdated", False) if version_data else False,
                "current_user": {
                    "pk": user_data.get("pk"),
                    "username": user_data.get("username"),
                    "name": user_data.get("name"),
                    "email": user_data.get("email"),
                    "is_superuser": user_data.get("is_superuser", False),
                    "is_staff": user_data.get("is_staff", False),
                    "is_active": user_data.get("is_active", True),
                    "groups": user_data.get("groups", []),
                },
                "system_info": system_data if system_data else {},
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid Authentik token") from e
            raise AdapterError(f"HTTP error: {e.response.status_code}") from e
        except Exception as e:
            raise AdapterError(f"Failed to get service info: {str(e)}") from e

    async def get_users(
        self, page: int = 1, page_size: int = 20, search: Optional[str] = None, is_active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Get users from Authentik."""
        try:
            params = {"page": str(page), "page_size": str(page_size)}

            if search:
                params["search"] = search
            if is_active is not None:
                params["is_active"] = str(is_active).lower()

            response = await self._make_request("GET", "/api/v3/core/users/", params=params)
            data = response.json()

            # Process users
            users = []
            for user in data.get("results", []):
                users.append(
                    {
                        "pk": user.get("pk"),
                        "username": user.get("username"),
                        "name": user.get("name"),
                        "email": user.get("email"),
                        "is_active": user.get("is_active"),
                        "is_superuser": user.get("is_superuser"),
                        "is_staff": user.get("is_staff"),
                        "date_joined": user.get("date_joined"),
                        "last_login": user.get("last_login"),
                        "groups": user.get("groups", []),
                        "avatar": user.get("avatar"),
                        "attributes": user.get("attributes", {}),
                    }
                )

            return {
                "users": users,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "count": data.get("pagination", {}).get("count", len(users)),
                    "total_pages": data.get("pagination", {}).get("num_pages", 1),
                    "next": data.get("pagination", {}).get("next"),
                    "previous": data.get("pagination", {}).get("previous"),
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to get users: {e}")
            return {"users": [], "pagination": {"page": page, "page_size": page_size, "count": 0}}

    async def get_user_by_id(self, user_pk: int) -> Optional[Dict[str, Any]]:
        """Get a specific user by ID."""
        try:
            response = await self._make_request("GET", f"/api/v3/core/users/{user_pk}/")
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            self.logger.warning(f"Failed to get user {user_pk}: {e}")
            return None

    async def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new user."""
        try:
            response = await self._make_request("POST", "/api/v3/core/users/", json=user_data)
            return response.json()

        except Exception as e:
            self.logger.error(f"Failed to create user: {e}")
            return None

    async def update_user(self, user_pk: int, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a user."""
        try:
            response = await self._make_request("PATCH", f"/api/v3/core/users/{user_pk}/", json=user_data)
            return response.json()

        except Exception as e:
            self.logger.error(f"Failed to update user {user_pk}: {e}")
            return None

    async def deactivate_user(self, user_pk: int) -> bool:
        """Deactivate a user."""
        try:
            response = await self._make_request("PATCH", f"/api/v3/core/users/{user_pk}/", json={"is_active": False})
            return response.status_code == 200

        except Exception as e:
            self.logger.error(f"Failed to deactivate user {user_pk}: {e}")
            return False

    async def get_groups(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Get groups from Authentik."""
        try:
            params = {"page": str(page), "page_size": str(page_size)}
            response = await self._make_request("GET", "/api/v3/core/groups/", params=params)
            data = response.json()

            groups = []
            for group in data.get("results", []):
                groups.append(
                    {
                        "pk": group.get("pk"),
                        "name": group.get("name"),
                        "is_superuser": group.get("is_superuser"),
                        "parent": group.get("parent"),
                        "users_obj": group.get("users_obj", []),
                        "attributes": group.get("attributes", {}),
                        "num_pk": group.get("num_pk"),
                    }
                )

            return {
                "groups": groups,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "count": data.get("pagination", {}).get("count", len(groups)),
                    "total_pages": data.get("pagination", {}).get("num_pages", 1),
                },
            }

        except Exception as e:
            self.logger.warning(f"Failed to get groups: {e}")
            return {"groups": [], "pagination": {"page": page, "page_size": page_size, "count": 0}}

    async def get_applications(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Get applications from Authentik."""
        try:
            params = {"page": str(page), "page_size": str(page_size)}
            response = await self._make_request("GET", "/api/v3/core/applications/", params=params)
            data = response.json()

            applications = []
            for app in data.get("results", []):
                applications.append(
                    {
                        "pk": app.get("pk"),
                        "name": app.get("name"),
                        "slug": app.get("slug"),
                        "provider": app.get("provider"),
                        "provider_obj": app.get("provider_obj", {}),
                        "launch_url": app.get("launch_url"),
                        "open_in_new_tab": app.get("open_in_new_tab"),
                        "meta_icon": app.get("meta_icon"),
                        "meta_description": app.get("meta_description"),
                        "policy_engine_mode": app.get("policy_engine_mode"),
                        "group": app.get("group"),
                    }
                )

            return {
                "applications": applications,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "count": data.get("pagination", {}).get("count", len(applications)),
                    "total_pages": data.get("pagination", {}).get("num_pages", 1),
                },
            }

        except Exception as e:
            self.logger.warning(f"Failed to get applications: {e}")
            return {"applications": [], "pagination": {"page": page, "page_size": page_size, "count": 0}}

    async def get_events(
        self, page: int = 1, page_size: int = 20, action: Optional[str] = None, username: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get audit events from Authentik."""
        try:
            params = {"page": str(page), "page_size": str(page_size), "ordering": "-created"}

            if action:
                params["action"] = action
            if username:
                params["username"] = username

            response = await self._make_request("GET", "/api/v3/events/events/", params=params)
            data = response.json()

            events = []
            for event in data.get("results", []):
                events.append(
                    {
                        "pk": event.get("pk"),
                        "user": event.get("user", {}),
                        "action": event.get("action"),
                        "result": event.get("result"),
                        "created": event.get("created"),
                        "client_ip": event.get("client_ip"),
                        "context": event.get("context", {}),
                        "app": event.get("app"),
                        "tenant": event.get("tenant", {}),
                    }
                )

            return {
                "events": events,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "count": data.get("pagination", {}).get("count", len(events)),
                    "total_pages": data.get("pagination", {}).get("num_pages", 1),
                },
            }

        except Exception as e:
            self.logger.warning(f"Failed to get events: {e}")
            return {"events": [], "pagination": {"page": page, "page_size": page_size, "count": 0}}

    async def search_users(self, query: str) -> List[Dict[str, Any]]:
        """Search for users by username, name, or email."""
        try:
            params = {"search": query, "page_size": "50"}
            response = await self._make_request("GET", "/api/v3/core/users/", params=params)
            data = response.json()

            return [
                {
                    "pk": user.get("pk"),
                    "username": user.get("username"),
                    "name": user.get("name"),
                    "email": user.get("email"),
                    "is_active": user.get("is_active"),
                }
                for user in data.get("results", [])
            ]

        except Exception as e:
            self.logger.warning(f"Failed to search users: {e}")
            return []

    async def get_statistics(self) -> Dict[str, Any]:
        """Get Authentik statistics."""
        try:
            # Get users count
            users_data = await self.get_users(page_size=1)
            total_users = users_data.get("pagination", {}).get("count", 0)

            # Get active users count
            active_users_data = await self.get_users(page_size=1, is_active=True)
            active_users = active_users_data.get("pagination", {}).get("count", 0)

            # Get groups count
            groups_data = await self.get_groups(page_size=1)
            total_groups = groups_data.get("pagination", {}).get("count", 0)

            # Get applications count
            apps_data = await self.get_applications(page_size=1)
            total_applications = apps_data.get("pagination", {}).get("count", 0)

            # Get recent events
            events_data = await self.get_events(page_size=10)
            recent_events = events_data.get("events", [])

            return {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": total_users - active_users,
                "total_groups": total_groups,
                "total_applications": total_applications,
                "recent_events_count": len(recent_events),
                "recent_events": recent_events[:5],
                "user_activity": {
                    "logins_today": sum(
                        1
                        for event in recent_events
                        if event.get("action") == "login" and "today" in event.get("created", "")
                    ),
                    "failed_logins": sum(1 for event in recent_events if event.get("action") == "login_failed"),
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                "total_users": 0,
                "active_users": 0,
                "inactive_users": 0,
                "total_groups": 0,
                "total_applications": 0,
                "recent_events_count": 0,
                "recent_events": [],
                "user_activity": {"logins_today": 0, "failed_logins": 0},
            }

    def validate_config(self) -> List[str]:
        """Validate Authentik-specific configuration."""
        errors = super().validate_config()

        # Check for required token
        if not self.get_config_value(self.token_config_key):
            errors.append("Authentik token is required")

        return errors

    async def sync_user_groups(self, user_pk: int, group_pks: List[int]) -> bool:
        """Synchronize user group memberships."""
        try:
            # Get current user data
            user = await self.get_user_by_id(user_pk)
            if not user:
                return False

            # Update user groups
            user_data = {"groups": group_pks}
            updated_user = await self.update_user(user_pk, user_data)

            return updated_user is not None

        except Exception as e:
            self.logger.error(f"Failed to sync user groups for user {user_pk}: {e}")
            return False
