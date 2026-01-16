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
                description="Search for ROMs in RomM by game title",
                parameters=[
                    ToolParameter(
                        name="query",
                        description="Search query (game title)",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="platform_slug",
                        description="Filter by platform (e.g., 'psx', 'n64', 'snes')",
                        type="string",
                        required=False,
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum results to return (default: 20)",
                        type="number",
                        required=False,
                        default=20,
                    ),
                ],
                category="gaming",
                is_mutation=False,
                requires_service="romm",
            ),
            ToolDefinition(
                name="romm_get_collections",
                description="Get list of ROM collections with optional filtering",
                parameters=[
                    ToolParameter(
                        name="name",
                        description="Filter collections by name (partial match)",
                        type="string",
                        required=False,
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum collections to return (default: 50)",
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
            ToolDefinition(
                name="romm_get_recently_added",
                description="Get recently added ROMs sorted by date (newest first)",
                parameters=[
                    ToolParameter(
                        name="limit",
                        description="Maximum number of ROMs to return (default: 20)",
                        type="number",
                        required=False,
                        default=20,
                    ),
                    ToolParameter(
                        name="days",
                        description="Number of days to look back (default: 30, use 0 for no limit)",
                        type="number",
                        required=False,
                        default=30,
                    ),
                ],
                category="gaming",
                is_mutation=False,
                requires_service="romm",
            ),
            ToolDefinition(
                name="romm_scan_platform",
                description="Trigger a scan to detect new or changed ROMs. Can scan a specific platform or all platforms.",
                parameters=[
                    ToolParameter(
                        name="platform_name",
                        description="Platform name or slug to scan (e.g., 'PlayStation', 'psx', 'Nintendo 64'). Leave empty to scan all platforms.",
                        type="string",
                        required=False,
                    ),
                ],
                category="gaming",
                is_mutation=True,
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
                    self.external_url = config.get("external_url")  # Public URL for user links
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
                return await self._get_collections(adapter, arguments)
            elif tool_name == "romm_get_users":
                return await self._get_users(adapter)
            elif tool_name == "romm_get_statistics":
                return await self._get_statistics(adapter)
            elif tool_name == "romm_get_recently_added":
                return await self._get_recently_added(adapter, arguments)
            elif tool_name == "romm_scan_platform":
                return await self._scan_platform(adapter, arguments)
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
        platform_slug = arguments.get("platform_slug")
        limit = arguments.get("limit", 20)

        results = await adapter.search_roms(query, platform_slug=platform_slug, limit=limit)

        result = {"query": query, "count": len(results), "results": results}
        if platform_slug:
            result["platform_filter"] = platform_slug

        return {"success": True, "result": result}

    async def _get_collections(self, adapter, arguments: dict) -> dict:
        """Get collections from RomM."""
        name_filter = arguments.get("name")
        limit = arguments.get("limit", 50)

        collections = await adapter.get_collections(name_filter=name_filter, limit=limit)

        result = {"count": len(collections), "collections": collections}
        if name_filter:
            result["filter"] = name_filter

        return {"success": True, "result": result}

    async def _get_users(self, adapter) -> dict:
        """Get users from RomM."""
        users = await adapter.get_users()

        return {"success": True, "result": {"count": len(users), "users": users}}

    async def _get_statistics(self, adapter) -> dict:
        """Get statistics."""
        stats = await adapter.get_statistics()

        return {"success": True, "result": stats}

    async def _get_recently_added(self, adapter, arguments: dict) -> dict:
        """Get recently added ROMs."""
        limit = int(arguments.get("limit", 20))
        days = int(arguments.get("days", 30))

        roms = await adapter.get_recently_added(limit=limit, days=days)

        return {
            "success": True,
            "result": {
                "count": len(roms),
                "limit": limit,
                "days": days,
                "roms": roms,
            },
        }

    async def _resolve_platform_id(self, adapter, platform_name: str) -> tuple:
        """Resolve platform name or slug to platform ID.

        Returns (platform_id, platform_name) tuple or (None, None) if no filter.
        """
        if not platform_name:
            return None, None

        platforms = await adapter.get_platforms()
        if not platforms:
            raise ValueError("No platforms found in RomM")

        search_name = platform_name.lower()

        # Try exact match on name or slug
        platform = next(
            (p for p in platforms if p.get("name", "").lower() == search_name or p.get("slug", "").lower() == search_name),
            None
        )

        # Try partial match
        if not platform:
            platform = next(
                (p for p in platforms if search_name in p.get("name", "").lower() or search_name in p.get("slug", "").lower()),
                None
            )

        if not platform:
            available = ", ".join(f"{p.get('name')} ({p.get('slug')})" for p in platforms)
            raise ValueError(f"Platform '{platform_name}' not found. Available platforms: {available}")

        return platform["id"], platform["name"]

    async def _scan_platform(self, adapter, arguments: dict) -> dict:
        """Trigger a platform scan in RomM."""
        platform_name = arguments.get("platform_name")

        # Resolve platform name to ID if provided
        platform_id = None
        if platform_name:
            platform_id, resolved_name = await self._resolve_platform_id(adapter, platform_name)

        result = await adapter.scan_platform(platform_id=platform_id)

        if result.get("error") and not result.get("success"):
            return {"success": False, "error": result.get("error"), "available_platforms": result.get("available_platforms")}

        return {"success": True, "result": result}
