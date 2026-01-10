"""MCP tools for Deluge integration."""

from typing import List

from .base import BaseTool, ToolDefinition, ToolParameter


class DelugeTools(BaseTool):
    """MCP tools for interacting with Deluge torrent client."""

    @property
    def definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="deluge_get_torrents",
                description="Get list of all torrents in Deluge",
                parameters=[],
                category="downloads",
                is_mutation=False,
                requires_service="deluge",
            ),
            ToolDefinition(
                name="deluge_add_torrent",
                description="Add a torrent by magnet link or URL",
                parameters=[
                    ToolParameter(
                        name="magnet_or_url",
                        description="Magnet link or torrent URL to add",
                        type="string",
                        required=True,
                    ),
                ],
                category="downloads",
                is_mutation=True,
                requires_service="deluge",
            ),
            ToolDefinition(
                name="deluge_pause_torrent",
                description="Pause a torrent",
                parameters=[
                    ToolParameter(
                        name="torrent_id",
                        description="ID of the torrent to pause",
                        type="string",
                        required=True,
                    ),
                ],
                category="downloads",
                is_mutation=True,
                requires_service="deluge",
            ),
            ToolDefinition(
                name="deluge_resume_torrent",
                description="Resume a paused torrent",
                parameters=[
                    ToolParameter(
                        name="torrent_id",
                        description="ID of the torrent to resume",
                        type="string",
                        required=True,
                    ),
                ],
                category="downloads",
                is_mutation=True,
                requires_service="deluge",
            ),
            ToolDefinition(
                name="deluge_remove_torrent",
                description="Remove a torrent",
                parameters=[
                    ToolParameter(
                        name="torrent_id",
                        description="ID of the torrent to remove",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="remove_data",
                        description="Also remove downloaded data",
                        type="boolean",
                        required=False,
                        default=False,
                    ),
                ],
                category="downloads",
                is_mutation=True,
                requires_service="deluge",
            ),
            ToolDefinition(
                name="deluge_get_statistics",
                description="Get Deluge statistics",
                parameters=[],
                category="downloads",
                is_mutation=False,
                requires_service="deluge",
            ),
            ToolDefinition(
                name="deluge_search_torrents",
                description="Search torrents by name with fuzzy matching",
                parameters=[
                    ToolParameter(
                        name="query",
                        description="Search term for torrent name",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="status_filter",
                        description="Filter by status (Downloading, Seeding, Paused)",
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
                category="downloads",
                is_mutation=False,
                requires_service="deluge",
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute a Deluge tool."""
        if not self.service_config:
            return {"success": False, "error": "Deluge service not configured"}

        try:
            from src.adapters.deluge import DelugeAdapter

            class ServiceConfigProxy:
                def __init__(self, config: dict):
                    self._config = config
                    self.password = config.get("password")
                    # Support both 'base_url' and 'url' keys for compatibility
                    self.base_url = config.get("base_url") or config.get("url", "")
                    self.external_url = config.get("external_url")  # Public URL for user links
                    self.port = config.get("port")
                    self.config = config.get("config") or config.get("extra_config", {})

                def get_config_value(self, key: str, default=None):
                    return self.config.get(key, default)

            service_proxy = ServiceConfigProxy(self.service_config)
            adapter = DelugeAdapter(service_proxy)

            if tool_name == "deluge_get_torrents":
                return await self._get_torrents(adapter)
            elif tool_name == "deluge_add_torrent":
                return await self._add_torrent(adapter, arguments)
            elif tool_name == "deluge_pause_torrent":
                return await self._pause_torrent(adapter, arguments)
            elif tool_name == "deluge_resume_torrent":
                return await self._resume_torrent(adapter, arguments)
            elif tool_name == "deluge_remove_torrent":
                return await self._remove_torrent(adapter, arguments)
            elif tool_name == "deluge_get_statistics":
                return await self._get_statistics(adapter)
            elif tool_name == "deluge_search_torrents":
                return await self._search_torrents(adapter, arguments)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    async def _get_torrents(self, adapter) -> dict:
        """Get torrents from Deluge."""
        torrents = await adapter.get_torrents()

        return {"success": True, "result": {"count": len(torrents), "torrents": torrents}}

    async def _add_torrent(self, adapter, arguments: dict) -> dict:
        """Add a torrent."""
        magnet_or_url = arguments.get("magnet_or_url")
        result = await adapter.add_torrent(magnet_or_url)

        return {"success": result.get("success", False), "result": result}

    async def _pause_torrent(self, adapter, arguments: dict) -> dict:
        """Pause a torrent."""
        torrent_id = arguments.get("torrent_id")
        success = await adapter.pause_torrent(torrent_id)

        return {"success": success, "result": {"torrent_id": torrent_id, "action": "paused" if success else "failed"}}

    async def _resume_torrent(self, adapter, arguments: dict) -> dict:
        """Resume a torrent."""
        torrent_id = arguments.get("torrent_id")
        success = await adapter.resume_torrent(torrent_id)

        return {"success": success, "result": {"torrent_id": torrent_id, "action": "resumed" if success else "failed"}}

    async def _remove_torrent(self, adapter, arguments: dict) -> dict:
        """Remove a torrent."""
        torrent_id = arguments.get("torrent_id")
        remove_data = arguments.get("remove_data", False)
        success = await adapter.remove_torrent(torrent_id, remove_data=remove_data)

        return {
            "success": success,
            "result": {
                "torrent_id": torrent_id,
                "action": "removed" if success else "failed",
                "data_removed": remove_data if success else False,
            },
        }

    async def _get_statistics(self, adapter) -> dict:
        """Get statistics."""
        stats = await adapter.get_statistics()

        return {"success": True, "result": stats}

    async def _search_torrents(self, adapter, arguments: dict) -> dict:
        """Search torrents by name."""
        query = arguments.get("query")
        status_filter = arguments.get("status_filter")
        limit = arguments.get("limit", 20)

        results = await adapter.search_torrents(query, status_filter=status_filter, limit=limit)

        result = {"query": query, "count": len(results), "results": results}
        if status_filter:
            result["status_filter"] = status_filter

        return {"success": True, "result": result}
