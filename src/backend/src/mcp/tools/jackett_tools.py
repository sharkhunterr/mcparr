"""MCP tools for Jackett integration."""

from typing import List

from .base import BaseTool, ToolDefinition, ToolParameter


class JackettTools(BaseTool):
    """MCP tools for interacting with Jackett torrent indexer proxy."""

    @property
    def definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="jackett_get_indexers",
                description="Get list of all indexers configured in Jackett",
                parameters=[
                    ToolParameter(
                        name="configured_only",
                        description="Only return configured/enabled indexers",
                        type="boolean",
                        required=False,
                        default=True,
                    ),
                ],
                category="indexers",
                is_mutation=False,
                requires_service="jackett",
            ),
            ToolDefinition(
                name="jackett_search",
                description="Search across Jackett indexers for torrents",
                parameters=[
                    ToolParameter(
                        name="query",
                        description="Search query",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="indexers",
                        description="Specific indexers to search (comma-separated)",
                        type="string",
                        required=False,
                    ),
                    ToolParameter(
                        name="categories",
                        description="Category IDs to filter (comma-separated)",
                        type="string",
                        required=False,
                    ),
                ],
                category="indexers",
                is_mutation=False,
                requires_service="jackett",
            ),
            ToolDefinition(
                name="jackett_test_indexer",
                description="Test a specific indexer connection",
                parameters=[
                    ToolParameter(
                        name="indexer_id",
                        description="ID of the indexer to test",
                        type="string",
                        required=True,
                    ),
                ],
                category="indexers",
                is_mutation=False,
                requires_service="jackett",
            ),
            ToolDefinition(
                name="jackett_get_statistics",
                description="Get Jackett statistics",
                parameters=[],
                category="indexers",
                is_mutation=False,
                requires_service="jackett",
            ),
            ToolDefinition(
                name="jackett_test_all_indexers",
                description="Test all configured indexers in Jackett",
                parameters=[],
                category="indexers",
                is_mutation=False,
                requires_service="jackett",
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute a Jackett tool."""
        if not self.service_config:
            return {"success": False, "error": "Jackett service not configured"}

        try:
            from src.adapters.jackett import JackettAdapter

            class ServiceConfigProxy:
                def __init__(self, config: dict):
                    self._config = config
                    self.api_key = config.get("api_key")
                    self.base_url = config.get("base_url") or config.get("url", "")
                    self.external_url = config.get("external_url")  # Public URL for user links
                    self.port = config.get("port")
                    self.config = config.get("config", config.get("extra_config", {}))

                def get_config_value(self, key: str, default=None):
                    return self.config.get(key, default)

            service_proxy = ServiceConfigProxy(self.service_config)
            adapter = JackettAdapter(service_proxy)

            if tool_name == "jackett_get_indexers":
                return await self._get_indexers(adapter, arguments)
            elif tool_name == "jackett_search":
                return await self._search(adapter, arguments)
            elif tool_name == "jackett_test_indexer":
                return await self._test_indexer(adapter, arguments)
            elif tool_name == "jackett_get_statistics":
                return await self._get_statistics(adapter)
            elif tool_name == "jackett_test_all_indexers":
                return await self._test_all_indexers(adapter)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    async def _get_indexers(self, adapter, arguments: dict) -> dict:
        """Get indexers from Jackett."""
        configured_only = arguments.get("configured_only", True)

        if configured_only:
            indexers = await adapter.get_configured_indexers()
        else:
            indexers = await adapter.get_indexers()

        return {"success": True, "result": {"count": len(indexers), "indexers": indexers}}

    async def _search(self, adapter, arguments: dict) -> dict:
        """Search across indexers."""
        query = arguments.get("query")
        indexers_str = arguments.get("indexers")
        categories_str = arguments.get("categories")

        indexers = None
        if indexers_str:
            indexers = [i.strip() for i in indexers_str.split(",")]

        categories = None
        if categories_str:
            categories = [int(c.strip()) for c in categories_str.split(",")]

        results = await adapter.search(query, indexers=indexers, categories=categories)

        return {"success": True, "result": {"query": query, "count": len(results), "results": results}}

    async def _test_indexer(self, adapter, arguments: dict) -> dict:
        """Test a specific indexer."""
        indexer_id = arguments.get("indexer_id")
        result = await adapter.test_indexer(indexer_id)

        return {"success": True, "result": result}

    async def _get_statistics(self, adapter) -> dict:
        """Get statistics."""
        stats = await adapter.get_statistics()

        return {"success": True, "result": stats}

    async def _test_all_indexers(self, adapter) -> dict:
        """Test all configured indexers."""
        result = await adapter.test_all_indexers()
        return {"success": True, "result": result}
