"""MCP tools for WikiJS wiki/documentation integration."""

from typing import List

from .base import BaseTool, ToolDefinition, ToolParameter


class WikiJSTools(BaseTool):
    """MCP tools for interacting with WikiJS wiki/documentation server."""

    @property
    def definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="wikijs_get_pages",
                description="Get list of wiki pages from WikiJS, ordered by most recently updated",
                parameters=[
                    ToolParameter(
                        name="limit",
                        description="Maximum number of pages to return",
                        type="number",
                        required=False,
                        default=50,
                    ),
                    ToolParameter(
                        name="locale",
                        description="Locale/language filter (e.g., 'en', 'fr')",
                        type="string",
                        required=False,
                        default="en",
                    ),
                ],
                category="system",
                is_mutation=False,
                requires_service="wikijs",
            ),
            ToolDefinition(
                name="wikijs_get_page",
                description="Get detailed content of a specific wiki page by its ID",
                parameters=[
                    ToolParameter(
                        name="page_id",
                        description="ID of the page to retrieve",
                        type="number",
                        required=True,
                    ),
                ],
                category="system",
                is_mutation=False,
                requires_service="wikijs",
            ),
            ToolDefinition(
                name="wikijs_search",
                description="Search for wiki pages by keyword or phrase",
                parameters=[
                    ToolParameter(
                        name="query",
                        description="Search query",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="locale",
                        description="Locale/language to search in",
                        type="string",
                        required=False,
                        default="en",
                    ),
                ],
                category="system",
                is_mutation=False,
                requires_service="wikijs",
            ),
            ToolDefinition(
                name="wikijs_get_page_tree",
                description="Get the hierarchical tree structure of wiki pages",
                parameters=[
                    ToolParameter(
                        name="parent_id",
                        description="Parent page ID to start from (0 for root)",
                        type="number",
                        required=False,
                        default=0,
                    ),
                    ToolParameter(
                        name="locale",
                        description="Locale/language filter",
                        type="string",
                        required=False,
                        default="en",
                    ),
                ],
                category="system",
                is_mutation=False,
                requires_service="wikijs",
            ),
            ToolDefinition(
                name="wikijs_get_tags",
                description="Get all tags used in the wiki",
                parameters=[],
                category="system",
                is_mutation=False,
                requires_service="wikijs",
            ),
            ToolDefinition(
                name="wikijs_get_users",
                description="Get list of users in WikiJS",
                parameters=[],
                category="users",
                is_mutation=False,
                requires_service="wikijs",
            ),
            ToolDefinition(
                name="wikijs_get_statistics",
                description="Get WikiJS statistics (page count, user count, etc.)",
                parameters=[],
                category="system",
                is_mutation=False,
                requires_service="wikijs",
            ),
            ToolDefinition(
                name="wikijs_create_page",
                description="Create a new wiki page in WikiJS",
                parameters=[
                    ToolParameter(
                        name="path",
                        description="Path for the page (e.g., 'docs/getting-started')",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="title",
                        description="Title of the page",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="content",
                        description="Markdown content of the page",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="description",
                        description="Short description of the page",
                        type="string",
                        required=False,
                        default="",
                    ),
                    ToolParameter(
                        name="locale",
                        description="Locale/language for the page",
                        type="string",
                        required=False,
                        default="en",
                    ),
                    ToolParameter(
                        name="tags",
                        description="Tags for the page (comma-separated)",
                        type="string",
                        required=False,
                        default="",
                    ),
                ],
                category="system",
                is_mutation=True,
                requires_service="wikijs",
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute a WikiJS tool."""
        if not self.service_config:
            return {"success": False, "error": "WikiJS service not configured"}

        try:
            from src.adapters.wikijs import WikiJSAdapter

            class ServiceConfigProxy:
                def __init__(self, config: dict):
                    self._config = config
                    self.api_key = config.get("api_key")
                    self.username = config.get("username")
                    self.password = config.get("password")
                    # Support both 'base_url' and 'url' keys for compatibility
                    self.base_url = config.get("base_url") or config.get("url", "")
                    self.external_url = config.get("external_url")  # Public URL for user links
                    self.port = config.get("port")
                    self.config = config.get("config") or config.get("extra_config", {})

                def get_config_value(self, key: str, default=None):
                    return self.config.get(key, default)

            service_proxy = ServiceConfigProxy(self.service_config)
            adapter = WikiJSAdapter(service_proxy)

            if tool_name == "wikijs_get_pages":
                return await self._get_pages(adapter, arguments)
            elif tool_name == "wikijs_get_page":
                return await self._get_page(adapter, arguments)
            elif tool_name == "wikijs_search":
                return await self._search(adapter, arguments)
            elif tool_name == "wikijs_get_page_tree":
                return await self._get_page_tree(adapter, arguments)
            elif tool_name == "wikijs_get_tags":
                return await self._get_tags(adapter)
            elif tool_name == "wikijs_get_users":
                return await self._get_users(adapter)
            elif tool_name == "wikijs_get_statistics":
                return await self._get_statistics(adapter)
            elif tool_name == "wikijs_create_page":
                return await self._create_page(adapter, arguments)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    async def _get_pages(self, adapter, arguments: dict) -> dict:
        """Get pages from WikiJS."""
        limit = arguments.get("limit", 50)
        locale = arguments.get("locale", "en")

        pages = await adapter.get_pages(limit=limit, locale=locale)

        return {"success": True, "result": {"count": len(pages), "locale": locale, "pages": pages}}

    async def _get_page(self, adapter, arguments: dict) -> dict:
        """Get a specific page from WikiJS."""
        page_id = arguments.get("page_id")

        if not page_id:
            return {"success": False, "error": "page_id is required"}

        page = await adapter.get_page(int(page_id))

        if page:
            return {"success": True, "result": page}
        else:
            return {"success": False, "error": f"Page not found: {page_id}"}

    async def _search(self, adapter, arguments: dict) -> dict:
        """Search in WikiJS."""
        query = arguments.get("query")
        locale = arguments.get("locale", "en")

        if not query:
            return {"success": False, "error": "query is required"}

        results = await adapter.search(query, locale=locale)

        return {
            "success": True,
            "result": {
                "query": query,
                "locale": locale,
                "total": results.get("total", 0),
                "suggestions": results.get("suggestions", []),
                "results": results.get("results", []),
            },
        }

    async def _get_page_tree(self, adapter, arguments: dict) -> dict:
        """Get page tree from WikiJS."""
        parent_id = int(arguments.get("parent_id", 0))
        locale = arguments.get("locale", "en")

        tree = await adapter.get_page_tree(parent_id=parent_id, locale=locale)

        return {"success": True, "result": {"parent_id": parent_id, "locale": locale, "count": len(tree), "tree": tree}}

    async def _get_tags(self, adapter) -> dict:
        """Get tags from WikiJS."""
        tags = await adapter.get_tags()

        return {"success": True, "result": {"count": len(tags), "tags": tags}}

    async def _get_users(self, adapter) -> dict:
        """Get users from WikiJS."""
        users = await adapter.get_users()

        return {"success": True, "result": {"count": len(users), "users": users}}

    async def _get_statistics(self, adapter) -> dict:
        """Get statistics from WikiJS."""
        stats = await adapter.get_statistics()

        return {"success": True, "result": stats}

    async def _create_page(self, adapter, arguments: dict) -> dict:
        """Create a page in WikiJS."""
        path = arguments.get("path")
        title = arguments.get("title")
        content = arguments.get("content")
        description = arguments.get("description", "")
        locale = arguments.get("locale", "en")
        tags_str = arguments.get("tags", "")

        if not path or not title or not content:
            return {"success": False, "error": "path, title, and content are required"}

        # Parse tags from comma-separated string
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

        result = await adapter.create_page(
            path=path, title=title, content=content, description=description, locale=locale, tags=tags
        )

        return {
            "success": result.get("success", False),
            "result": result if result.get("success") else None,
            "error": result.get("error") if not result.get("success") else None,
        }
