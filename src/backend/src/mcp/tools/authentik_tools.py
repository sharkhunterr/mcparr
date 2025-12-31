"""MCP tools for Authentik integration."""

from typing import List

from .base import BaseTool, ToolDefinition, ToolParameter


class AuthentikTools(BaseTool):
    """MCP tools for interacting with Authentik identity provider."""

    @property
    def definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="authentik_get_users",
                description="Get list of users from Authentik with optional search and filtering",
                parameters=[
                    ToolParameter(
                        name="search",
                        description="Search query to filter users by username, name, or email",
                        type="string",
                        required=False,
                    ),
                    ToolParameter(
                        name="is_active",
                        description="Filter by user active status",
                        type="boolean",
                        required=False,
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum number of users to return",
                        type="number",
                        required=False,
                        default=20,
                    ),
                ],
                category="identity",
                is_mutation=False,
                requires_service="authentik",
            ),
            ToolDefinition(
                name="authentik_get_user",
                description="Get details of a specific user by their ID",
                parameters=[
                    ToolParameter(
                        name="user_pk",
                        description="User primary key (ID)",
                        type="number",
                        required=True,
                    ),
                ],
                category="identity",
                is_mutation=False,
                requires_service="authentik",
            ),
            ToolDefinition(
                name="authentik_search_users",
                description="Search for users by username, name, or email",
                parameters=[
                    ToolParameter(
                        name="query",
                        description="Search query",
                        type="string",
                        required=True,
                    ),
                ],
                category="identity",
                is_mutation=False,
                requires_service="authentik",
            ),
            ToolDefinition(
                name="authentik_get_groups",
                description="Get list of groups from Authentik",
                parameters=[
                    ToolParameter(
                        name="limit",
                        description="Maximum number of groups to return",
                        type="number",
                        required=False,
                        default=20,
                    ),
                ],
                category="identity",
                is_mutation=False,
                requires_service="authentik",
            ),
            ToolDefinition(
                name="authentik_get_applications",
                description="Get list of applications configured in Authentik",
                parameters=[
                    ToolParameter(
                        name="limit",
                        description="Maximum number of applications to return",
                        type="number",
                        required=False,
                        default=20,
                    ),
                ],
                category="identity",
                is_mutation=False,
                requires_service="authentik",
            ),
            ToolDefinition(
                name="authentik_get_events",
                description="Get audit events from Authentik",
                parameters=[
                    ToolParameter(
                        name="action",
                        description="Filter by action type (e.g., 'login', 'login_failed', 'logout')",
                        type="string",
                        required=False,
                    ),
                    ToolParameter(
                        name="username",
                        description="Filter by username",
                        type="string",
                        required=False,
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum number of events to return",
                        type="number",
                        required=False,
                        default=20,
                    ),
                ],
                category="identity",
                is_mutation=False,
                requires_service="authentik",
            ),
            ToolDefinition(
                name="authentik_get_statistics",
                description="Get Authentik statistics including user counts, groups, applications, and recent activity",
                parameters=[],
                category="identity",
                is_mutation=False,
                requires_service="authentik",
            ),
            ToolDefinition(
                name="authentik_get_server_info",
                description="Get Authentik server information including version and current user",
                parameters=[],
                category="identity",
                is_mutation=False,
                requires_service="authentik",
            ),
            ToolDefinition(
                name="authentik_deactivate_user",
                description="Deactivate a user account (set is_active to false)",
                parameters=[
                    ToolParameter(
                        name="user_pk",
                        description="User primary key (ID) to deactivate",
                        type="number",
                        required=True,
                    ),
                ],
                category="identity",
                is_mutation=True,
                requires_service="authentik",
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute an Authentik tool."""
        if not self.service_config:
            return {"success": False, "error": "Authentik service not configured"}

        try:
            from src.adapters.authentik import AuthentikAdapter

            class ServiceConfigProxy:
                def __init__(self, config: dict):
                    self._config = config
                    self.api_key = config.get("api_key")
                    self.base_url = config.get("base_url") or config.get("url", "")
                    self.port = config.get("port")
                    self.config = config.get("config", config.get("extra_config", {}))

                def get_config_value(self, key: str, default=None):
                    return self.config.get(key, default)

            service_proxy = ServiceConfigProxy(self.service_config)
            adapter = AuthentikAdapter(service_proxy)

            async with adapter:
                if tool_name == "authentik_get_users":
                    return await self._get_users(adapter, arguments)
                elif tool_name == "authentik_get_user":
                    return await self._get_user(adapter, arguments)
                elif tool_name == "authentik_search_users":
                    return await self._search_users(adapter, arguments)
                elif tool_name == "authentik_get_groups":
                    return await self._get_groups(adapter, arguments)
                elif tool_name == "authentik_get_applications":
                    return await self._get_applications(adapter, arguments)
                elif tool_name == "authentik_get_events":
                    return await self._get_events(adapter, arguments)
                elif tool_name == "authentik_get_statistics":
                    return await self._get_statistics(adapter)
                elif tool_name == "authentik_get_server_info":
                    return await self._get_server_info(adapter)
                elif tool_name == "authentik_deactivate_user":
                    return await self._deactivate_user(adapter, arguments)
                else:
                    return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    async def _get_users(self, adapter, arguments: dict) -> dict:
        """Get users from Authentik."""
        search = arguments.get("search")
        is_active = arguments.get("is_active")
        limit = arguments.get("limit", 20)

        result = await adapter.get_users(page_size=limit, search=search, is_active=is_active)

        return {
            "success": True,
            "result": {
                "count": len(result.get("users", [])),
                "total": result.get("pagination", {}).get("count", 0),
                "users": [
                    {
                        "pk": user.get("pk"),
                        "username": user.get("username"),
                        "name": user.get("name"),
                        "email": user.get("email"),
                        "is_active": user.get("is_active"),
                        "is_superuser": user.get("is_superuser"),
                        "last_login": user.get("last_login"),
                        "groups": [g.get("name") if isinstance(g, dict) else g for g in user.get("groups", [])],
                    }
                    for user in result.get("users", [])
                ],
            },
        }

    async def _get_user(self, adapter, arguments: dict) -> dict:
        """Get a specific user by ID."""
        user_pk = arguments.get("user_pk")
        if not user_pk:
            return {"success": False, "error": "user_pk is required"}

        user = await adapter.get_user_by_id(int(user_pk))
        if not user:
            return {"success": False, "error": f"User with ID {user_pk} not found"}

        return {
            "success": True,
            "result": {
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
                "attributes": user.get("attributes", {}),
            },
        }

    async def _search_users(self, adapter, arguments: dict) -> dict:
        """Search for users."""
        query = arguments.get("query")
        if not query:
            return {"success": False, "error": "query is required"}

        users = await adapter.search_users(query)

        return {"success": True, "result": {"query": query, "count": len(users), "users": users}}

    async def _get_groups(self, adapter, arguments: dict) -> dict:
        """Get groups from Authentik."""
        limit = arguments.get("limit", 20)

        result = await adapter.get_groups(page_size=limit)

        return {
            "success": True,
            "result": {
                "count": len(result.get("groups", [])),
                "total": result.get("pagination", {}).get("count", 0),
                "groups": [
                    {
                        "pk": group.get("pk"),
                        "name": group.get("name"),
                        "is_superuser": group.get("is_superuser"),
                        "parent": group.get("parent"),
                        "user_count": len(group.get("users_obj", [])),
                    }
                    for group in result.get("groups", [])
                ],
            },
        }

    async def _get_applications(self, adapter, arguments: dict) -> dict:
        """Get applications from Authentik."""
        limit = arguments.get("limit", 20)

        result = await adapter.get_applications(page_size=limit)

        return {
            "success": True,
            "result": {
                "count": len(result.get("applications", [])),
                "total": result.get("pagination", {}).get("count", 0),
                "applications": [
                    {
                        "pk": app.get("pk"),
                        "name": app.get("name"),
                        "slug": app.get("slug"),
                        "launch_url": app.get("launch_url"),
                        "description": app.get("meta_description"),
                        "group": app.get("group"),
                    }
                    for app in result.get("applications", [])
                ],
            },
        }

    async def _get_events(self, adapter, arguments: dict) -> dict:
        """Get audit events from Authentik."""
        action = arguments.get("action")
        username = arguments.get("username")
        limit = arguments.get("limit", 20)

        result = await adapter.get_events(page_size=limit, action=action, username=username)

        return {
            "success": True,
            "result": {
                "count": len(result.get("events", [])),
                "total": result.get("pagination", {}).get("count", 0),
                "events": [
                    {
                        "pk": event.get("pk"),
                        "action": event.get("action"),
                        "result": event.get("result"),
                        "created": event.get("created"),
                        "user": event.get("user", {}).get("username")
                        if isinstance(event.get("user"), dict)
                        else event.get("user"),
                        "client_ip": event.get("client_ip"),
                        "app": event.get("app"),
                    }
                    for event in result.get("events", [])
                ],
            },
        }

    async def _get_statistics(self, adapter) -> dict:
        """Get Authentik statistics."""
        stats = await adapter.get_statistics()

        return {
            "success": True,
            "result": {
                "users": {
                    "total": stats.get("total_users", 0),
                    "active": stats.get("active_users", 0),
                    "inactive": stats.get("inactive_users", 0),
                },
                "groups": stats.get("total_groups", 0),
                "applications": stats.get("total_applications", 0),
                "recent_activity": {
                    "logins_today": stats.get("user_activity", {}).get("logins_today", 0),
                    "failed_logins": stats.get("user_activity", {}).get("failed_logins", 0),
                },
                "recent_events": [
                    {
                        "action": event.get("action"),
                        "user": event.get("user", {}).get("username") if isinstance(event.get("user"), dict) else None,
                        "created": event.get("created"),
                    }
                    for event in stats.get("recent_events", [])[:5]
                ],
            },
        }

    async def _get_server_info(self, adapter) -> dict:
        """Get Authentik server information."""
        info = await adapter.get_service_info()

        return {
            "success": True,
            "result": {
                "service": info.get("service"),
                "version": info.get("version"),
                "version_latest": info.get("version_latest"),
                "outdated": info.get("outdated", False),
                "current_user": info.get("current_user", {}),
            },
        }

    async def _deactivate_user(self, adapter, arguments: dict) -> dict:
        """Deactivate a user account."""
        user_pk = arguments.get("user_pk")
        if not user_pk:
            return {"success": False, "error": "user_pk is required"}

        # First get user info
        user = await adapter.get_user_by_id(int(user_pk))
        if not user:
            return {"success": False, "error": f"User with ID {user_pk} not found"}

        if not user.get("is_active"):
            return {
                "success": True,
                "result": {
                    "message": f"User '{user.get('username')}' is already inactive",
                    "user_pk": user_pk,
                    "was_active": False,
                },
            }

        success = await adapter.deactivate_user(int(user_pk))

        if success:
            return {
                "success": True,
                "result": {
                    "message": f"User '{user.get('username')}' has been deactivated",
                    "user_pk": user_pk,
                    "username": user.get("username"),
                },
            }
        else:
            return {"success": False, "error": f"Failed to deactivate user {user_pk}"}
