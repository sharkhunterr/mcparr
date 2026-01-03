"""MCP tools for Open WebUI integration."""

from typing import List

from .base import BaseTool, ToolDefinition, ToolParameter


class OpenWebUITools(BaseTool):
    """MCP tools for interacting with Open WebUI."""

    @property
    def definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="openwebui_get_status",
                description="Get Open WebUI service status including version and current user info",
                parameters=[],
                category="system",
                is_mutation=False,
                requires_service="openwebui",
            ),
            ToolDefinition(
                name="openwebui_get_users",
                description="Get list of all users registered in Open WebUI (requires admin privileges)",
                parameters=[
                    ToolParameter(
                        name="limit",
                        description="Maximum number of users to return",
                        type="number",
                        required=False,
                        default=50,
                    ),
                ],
                category="users",
                is_mutation=False,
                requires_service="openwebui",
            ),
            ToolDefinition(
                name="openwebui_get_models",
                description="Get list of available AI models in Open WebUI",
                parameters=[],
                category="system",
                is_mutation=False,
                requires_service="openwebui",
            ),
            ToolDefinition(
                name="openwebui_get_chats",
                description="Get chat history for the authenticated user",
                parameters=[
                    ToolParameter(
                        name="limit",
                        description="Maximum number of chats to return",
                        type="number",
                        required=False,
                        default=20,
                    ),
                ],
                category="system",
                is_mutation=False,
                requires_service="openwebui",
            ),
            ToolDefinition(
                name="openwebui_get_statistics",
                description="Get Open WebUI statistics including user count, models, and chat activity",
                parameters=[],
                category="system",
                is_mutation=False,
                requires_service="openwebui",
            ),
            ToolDefinition(
                name="openwebui_search_users",
                description="Search for users by email or name in Open WebUI (requires admin privileges)",
                parameters=[
                    ToolParameter(
                        name="query",
                        description="Search query (email or name)",
                        type="string",
                        required=True,
                    ),
                ],
                category="users",
                is_mutation=False,
                requires_service="openwebui",
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute an Open WebUI tool."""
        if not self.service_config:
            return {"success": False, "error": "Open WebUI service not configured"}

        try:
            # Import adapter here to avoid circular imports
            from src.adapters.openwebui import OpenWebUIAdapter

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
            adapter = OpenWebUIAdapter(service_proxy)

            if tool_name == "openwebui_get_status":
                return await self._get_status(adapter)
            elif tool_name == "openwebui_get_users":
                return await self._get_users(adapter, arguments)
            elif tool_name == "openwebui_get_models":
                return await self._get_models(adapter)
            elif tool_name == "openwebui_get_chats":
                return await self._get_chats(adapter, arguments)
            elif tool_name == "openwebui_get_statistics":
                return await self._get_statistics(adapter)
            elif tool_name == "openwebui_search_users":
                return await self._search_users(adapter, arguments)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    async def _get_status(self, adapter) -> dict:
        """Get Open WebUI status."""
        info = await adapter.get_service_info()
        return {
            "success": True,
            "result": {
                "service": info.get("service"),
                "version": info.get("version"),
                "models_available": info.get("models_available"),
                "current_user": info.get("current_user"),
            },
        }

    async def _get_users(self, adapter, arguments: dict) -> dict:
        """Get Open WebUI users."""
        limit = arguments.get("limit", 50)
        result = await adapter.get_users(limit=limit)

        if "error" in result:
            return {"success": False, "error": result.get("error", "Failed to get users")}

        return {
            "success": True,
            "result": {
                "count": result.get("count", 0),
                "users": [
                    {
                        "id": user.get("id"),
                        "email": user.get("email"),
                        "name": user.get("name"),
                        "role": user.get("role"),
                        "created_at": user.get("created_at"),
                        "last_active_at": user.get("last_active_at"),
                    }
                    for user in result.get("users", [])
                ],
            },
        }

    async def _get_models(self, adapter) -> dict:
        """Get available AI models."""
        models = await adapter.get_models()
        return {
            "success": True,
            "result": {
                "count": len(models),
                "models": [
                    {
                        "id": model.get("id"),
                        "name": model.get("name"),
                        "owned_by": model.get("owned_by"),
                    }
                    for model in models
                ],
            },
        }

    async def _get_chats(self, adapter, arguments: dict) -> dict:
        """Get chat history."""
        limit = arguments.get("limit", 20)
        result = await adapter.get_chats(limit=limit)

        return {"success": True, "result": {"count": result.get("count", 0), "chats": result.get("chats", [])}}

    async def _get_statistics(self, adapter) -> dict:
        """Get Open WebUI statistics."""
        stats = await adapter.get_statistics()
        return {"success": True, "result": stats}

    async def _search_users(self, adapter, arguments: dict) -> dict:
        """Search for users."""
        query = arguments.get("query", "")
        if not query:
            return {"success": False, "error": "Search query is required"}

        users = await adapter.search_users(query)

        return {
            "success": True,
            "result": {
                "query": query,
                "count": len(users),
                "users": [
                    {
                        "id": user.get("id"),
                        "email": user.get("email"),
                        "name": user.get("name"),
                        "role": user.get("role"),
                    }
                    for user in users
                ],
            },
        }
