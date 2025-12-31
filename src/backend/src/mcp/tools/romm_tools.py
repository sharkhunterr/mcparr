"""MCP tools for RomM integration."""

from typing import List

from .base import BaseTool, ToolDefinition, ToolParameter


class RommTools(BaseTool):
    """MCP tools for interacting with RomM ROM management system."""

    @property
    def definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="romm_get_platforms",
                description="Get list of gaming platforms in RomM",
                parameters=[],
                category="gaming",
                is_mutation=False,
                requires_service="romm",
            ),
            ToolDefinition(
                name="romm_get_roms",
                description="Get list of ROMs",
                parameters=[
                    ToolParameter(
                        name="platform_id",
                        description="Filter by platform ID",
                        type="number",
                        required=False,
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum number of ROMs to return",
                        type="number",
                        required=False,
                        default=50,
                    ),
                ],
                category="gaming",
                is_mutation=False,
                requires_service="romm",
            ),
            ToolDefinition(
                name="romm_search_roms",
                description="Search for ROMs in RomM",
                parameters=[
                    ToolParameter(
                        name="query",
                        description="Search query (game title)",
                        type="string",
                        required=True,
                    ),
                ],
                category="gaming",
                is_mutation=False,
                requires_service="romm",
            ),
            ToolDefinition(
                name="romm_get_collections",
                description="Get list of ROM collections",
                parameters=[],
                category="gaming",
                is_mutation=False,
                requires_service="romm",
            ),
            ToolDefinition(
                name="romm_get_users",
                description="Get list of users in RomM",
                parameters=[],
                category="users",
                is_mutation=False,
                requires_service="romm",
            ),
            ToolDefinition(
                name="romm_get_statistics",
                description="Get RomM library statistics",
                parameters=[],
                category="gaming",
                is_mutation=False,
                requires_service="romm",
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute a RomM tool."""
        if not self.service_config:
            return {"success": False, "error": "RomM service not configured"}

        try:
            from src.adapters.romm import RommAdapter

            class ServiceConfigProxy:
                def __init__(self, config: dict):
                    self._config = config
                    self.api_key = config.get("api_key")
                    # Support both 'base_url' and 'url' keys for compatibility
                    self.base_url = config.get("base_url") or config.get("url", "")
                    self.username = config.get("username")
                    self.password = config.get("password")
                    self.port = config.get("port")
                    self.config = config.get("config") or config.get("extra_config", {})

                def get_config_value(self, key: str, default=None):
                    return self.config.get(key, default)

            service_proxy = ServiceConfigProxy(self.service_config)
            adapter = RommAdapter(service_proxy)

            if tool_name == "romm_get_platforms":
                return await self._get_platforms(adapter)
            elif tool_name == "romm_get_roms":
                return await self._get_roms(adapter, arguments)
            elif tool_name == "romm_search_roms":
                return await self._search_roms(adapter, arguments)
            elif tool_name == "romm_get_collections":
                return await self._get_collections(adapter)
            elif tool_name == "romm_get_users":
                return await self._get_users(adapter)
            elif tool_name == "romm_get_statistics":
                return await self._get_statistics(adapter)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    async def _get_platforms(self, adapter) -> dict:
        """Get platforms from RomM."""
        platforms = await adapter.get_platforms()

        return {"success": True, "result": {"count": len(platforms), "platforms": platforms}}

    async def _get_roms(self, adapter, arguments: dict) -> dict:
        """Get ROMs from RomM."""
        platform_id = arguments.get("platform_id")
        limit = arguments.get("limit", 50)
        roms = await adapter.get_roms(platform_id=platform_id, limit=limit)

        return {"success": True, "result": {"count": len(roms), "roms": roms}}

    async def _search_roms(self, adapter, arguments: dict) -> dict:
        """Search for ROMs."""
        query = arguments.get("query")
        results = await adapter.search_roms(query)

        return {"success": True, "result": {"query": query, "count": len(results), "results": results}}

    async def _get_collections(self, adapter) -> dict:
        """Get collections from RomM."""
        collections = await adapter.get_collections()

        return {"success": True, "result": {"count": len(collections), "collections": collections}}

    async def _get_users(self, adapter) -> dict:
        """Get users from RomM."""
        users = await adapter.get_users()

        return {"success": True, "result": {"count": len(users), "users": users}}

    async def _get_statistics(self, adapter) -> dict:
        """Get statistics."""
        stats = await adapter.get_statistics()

        return {"success": True, "result": stats}
