"""Open WebUI adapter for AI chat interface integration."""

from typing import Dict, Any, List, Optional
import httpx
from datetime import datetime

from .base import (
    TokenAuthAdapter,
    ServiceCapability,
    ConnectionTestResult,
    AdapterError,
    AuthenticationError
)


class OpenWebUIAdapter(TokenAuthAdapter):
    """
    Adapter for Open WebUI AI chat interface.

    Open WebUI is a self-hosted AI chat interface that supports
    multiple LLM backends (Ollama, OpenAI, etc.).

    Capabilities:
        - USER_MANAGEMENT: Manage Open WebUI users
        - API_ACCESS: Access to Open WebUI API
        - AUTHENTICATION: User authentication info

    Auth:
        Bearer token via Authorization header
        Token can be obtained from Open WebUI settings or via login
    """

    @property
    def service_type(self) -> str:
        return "openwebui"

    @property
    def supported_capabilities(self) -> List[ServiceCapability]:
        return [
            ServiceCapability.USER_MANAGEMENT,
            ServiceCapability.API_ACCESS,
            ServiceCapability.AUTHENTICATION
        ]

    @property
    def token_config_key(self) -> str:
        return "openwebui_token"

    def _format_token_header(self, token: str) -> Dict[str, str]:
        """Format Open WebUI token header."""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def test_connection(self) -> ConnectionTestResult:
        """Test connection to Open WebUI."""
        start_time = datetime.utcnow()

        try:
            # Test by getting current user info
            response = await self._make_request("GET", "/api/v1/auths/")

            end_time = datetime.utcnow()
            response_time = int((end_time - start_time).total_seconds() * 1000)

            data = response.json()

            if "id" in data and "email" in data:
                return ConnectionTestResult(
                    success=True,
                    message="Successfully connected to Open WebUI",
                    response_time_ms=response_time,
                    details={
                        "status": "connected",
                        "user_id": data.get("id"),
                        "email": data.get("email"),
                        "name": data.get("name"),
                        "role": data.get("role")
                    }
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message="Connected but response doesn't appear to be from Open WebUI",
                    response_time_ms=response_time,
                    details={"status": "invalid_response"}
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return ConnectionTestResult(
                    success=False,
                    message="Authentication failed - check token",
                    details={"status": "auth_failed", "status_code": 401}
                )
            elif e.response.status_code == 403:
                return ConnectionTestResult(
                    success=False,
                    message="Access denied - insufficient permissions",
                    details={"status": "access_denied", "status_code": 403}
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message=f"HTTP error: {e.response.status_code}",
                    details={"status": "http_error", "status_code": e.response.status_code}
                )
        except httpx.RequestError as e:
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                details={"status": "connection_failed", "error": str(e)}
            )
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Unexpected error: {str(e)}",
                details={"status": "unexpected_error", "error": str(e)}
            )

    async def get_service_info(self) -> Dict[str, Any]:
        """Get Open WebUI service information."""
        try:
            # Get current user info
            user_response = await self._make_request("GET", "/api/v1/auths/")
            user_data = user_response.json()

            # Try to get version/config info
            config_data = await self._safe_request("GET", "/api/v1/config")

            # Try to get models info
            models_data = await self._safe_request("GET", "/api/models")

            return {
                "service": "openwebui",
                "version": config_data.get("version") if config_data else "unknown",
                "current_user": {
                    "id": user_data.get("id"),
                    "email": user_data.get("email"),
                    "name": user_data.get("name"),
                    "role": user_data.get("role"),
                    "profile_image_url": user_data.get("profile_image_url")
                },
                "models_available": len(models_data) if models_data and isinstance(models_data, list) else 0,
                "config": config_data if config_data else {}
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid Open WebUI token")
            raise AdapterError(f"HTTP error: {e.response.status_code}")
        except Exception as e:
            raise AdapterError(f"Failed to get service info: {str(e)}")

    async def get_users(
        self,
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get users from Open WebUI.

        Note: Requires admin privileges.
        """
        try:
            params = {"skip": str(skip), "limit": str(limit)}
            response = await self._make_request("GET", "/api/v1/users/", params=params)
            users_data = response.json()

            # Normalize user data
            users = []
            # Handle both list and dict response formats
            raw_users = users_data
            if isinstance(users_data, dict) and 'users' in users_data:
                raw_users = users_data['users']

            if isinstance(raw_users, list):
                for user in raw_users:
                    users.append({
                        "id": user.get("id"),
                        "email": user.get("email"),
                        "name": user.get("name"),
                        "username": user.get("email", "").split("@")[0] if user.get("email") else user.get("name"),
                        "role": user.get("role"),
                        "profile_image_url": user.get("profile_image_url"),
                        "created_at": user.get("created_at"),
                        "last_active_at": user.get("last_active_at"),
                        # Keep raw data for reference
                        "_raw": user
                    })

            return {
                "users": users,
                "count": len(users),
                "skip": skip,
                "limit": limit
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                self.logger.warning("Access denied - admin privileges required to list users")
                return {"users": [], "count": 0, "error": "Admin privileges required"}
            raise
        except Exception as e:
            self.logger.error(f"Failed to get users: {e}")
            return {"users": [], "count": 0, "error": str(e)}

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific user by ID."""
        try:
            response = await self._make_request("GET", f"/api/v1/users/{user_id}")
            user = response.json()

            return {
                "id": user.get("id"),
                "email": user.get("email"),
                "name": user.get("name"),
                "username": user.get("email", "").split("@")[0] if user.get("email") else user.get("name"),
                "role": user.get("role"),
                "profile_image_url": user.get("profile_image_url"),
                "created_at": user.get("created_at"),
                "last_active_at": user.get("last_active_at")
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            self.logger.warning(f"Failed to get user {user_id}: {e}")
            return None

    async def get_current_user(self) -> Dict[str, Any]:
        """Get the current authenticated user."""
        try:
            response = await self._make_request("GET", "/api/v1/auths/")
            user = response.json()

            return {
                "id": user.get("id"),
                "email": user.get("email"),
                "name": user.get("name"),
                "role": user.get("role"),
                "profile_image_url": user.get("profile_image_url")
            }

        except Exception as e:
            self.logger.error(f"Failed to get current user: {e}")
            raise

    async def get_models(self) -> List[Dict[str, Any]]:
        """Get available AI models."""
        try:
            response = await self._make_request("GET", "/api/models")
            models_data = response.json()

            if isinstance(models_data, list):
                return [
                    {
                        "id": model.get("id"),
                        "name": model.get("name"),
                        "owned_by": model.get("owned_by"),
                        "created": model.get("created"),
                        "object": model.get("object")
                    }
                    for model in models_data
                ]
            elif isinstance(models_data, dict) and "data" in models_data:
                return [
                    {
                        "id": model.get("id"),
                        "name": model.get("name", model.get("id")),
                        "owned_by": model.get("owned_by"),
                        "created": model.get("created"),
                        "object": model.get("object")
                    }
                    for model in models_data.get("data", [])
                ]
            return []

        except Exception as e:
            self.logger.warning(f"Failed to get models: {e}")
            return []

    async def get_chats(
        self,
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get chat history for current user."""
        try:
            params = {"skip": str(skip), "limit": str(limit)}
            response = await self._make_request("GET", "/api/v1/chats/", params=params)
            chats_data = response.json()

            chats = []
            if isinstance(chats_data, list):
                for chat in chats_data:
                    chats.append({
                        "id": chat.get("id"),
                        "title": chat.get("title"),
                        "created_at": chat.get("created_at"),
                        "updated_at": chat.get("updated_at"),
                        "models": chat.get("models", [])
                    })

            return {
                "chats": chats,
                "count": len(chats),
                "skip": skip,
                "limit": limit
            }

        except Exception as e:
            self.logger.warning(f"Failed to get chats: {e}")
            return {"chats": [], "count": 0, "error": str(e)}

    async def get_chat_by_id(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific chat by ID."""
        try:
            response = await self._make_request("GET", f"/api/v1/chats/{chat_id}")
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            self.logger.warning(f"Failed to get chat {chat_id}: {e}")
            return None

    async def get_statistics(self) -> Dict[str, Any]:
        """Get Open WebUI statistics."""
        try:
            # Get users count (admin only)
            users_data = await self.get_users(limit=1)
            total_users = users_data.get("count", 0) if "error" not in users_data else "N/A"

            # Get models
            models = await self.get_models()

            # Get current user's chats
            chats_data = await self.get_chats(limit=1)

            # Get service info
            service_info = await self.get_service_info()

            return {
                "total_users": total_users,
                "total_models": len(models),
                "models": [m.get("id") for m in models[:10]],  # First 10 model IDs
                "user_chats_count": chats_data.get("count", 0),
                "version": service_info.get("version", "unknown"),
                "current_user": service_info.get("current_user", {})
            }

        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                "total_users": "N/A",
                "total_models": 0,
                "models": [],
                "user_chats_count": 0,
                "version": "unknown",
                "error": str(e)
            }

    async def search_users(self, query: str) -> List[Dict[str, Any]]:
        """Search for users by email or name."""
        try:
            # Open WebUI may not have a direct search endpoint
            # We'll get all users and filter locally
            users_data = await self.get_users(limit=100)
            users = users_data.get("users", [])

            query_lower = query.lower()
            matching_users = [
                user for user in users
                if query_lower in (user.get("email") or "").lower()
                or query_lower in (user.get("name") or "").lower()
                or query_lower in (user.get("username") or "").lower()
            ]

            return matching_users

        except Exception as e:
            self.logger.warning(f"Failed to search users: {e}")
            return []

    def validate_config(self) -> List[str]:
        """Validate Open WebUI-specific configuration."""
        errors = super().validate_config()

        # Check for required token
        if not self.service_config.api_key and not self.get_config_value(self.token_config_key):
            errors.append("Open WebUI API token is required")

        return errors
