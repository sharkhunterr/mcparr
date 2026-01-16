"""MCP tools for Sonarr integration."""

from typing import List

from .base import BaseTool, ToolDefinition, ToolParameter


class SonarrTools(BaseTool):
    """MCP tools for interacting with Sonarr TV series management."""

    @property
    def definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="sonarr_search_series",
                description="Search for a TV series to add to Sonarr. Returns match_score (0-100) and library status if already added.",
                parameters=[
                    ToolParameter(
                        name="query",
                        description="TV series title to search for",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum number of results to return",
                        type="number",
                        required=False,
                        default=10,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_get_series_status",
                description="Get detailed status of a specific TV series in Sonarr library (monitored, episodes, quality profile, etc.)",
                parameters=[
                    ToolParameter(
                        name="title",
                        description="TV series title to search for in Sonarr library",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="year",
                        description="First air year (helps with disambiguation)",
                        type="number",
                        required=False,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_get_releases",
                description="Get available releases/torrents for a TV series (manual search). Shows quality, language, seeders, size, and whether the release matches the profile.",
                parameters=[
                    ToolParameter(
                        name="series_id",
                        description="Sonarr series ID (get from sonarr_get_series_status or sonarr_search_series)",
                        type="number",
                        required=True,
                    ),
                    ToolParameter(
                        name="season_number",
                        description="Specific season number to search (optional, searches all if not specified)",
                        type="number",
                        required=False,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_get_queue",
                description="Get current download queue in Sonarr",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_get_calendar",
                description="Get upcoming TV episode releases from Sonarr calendar",
                parameters=[
                    ToolParameter(
                        name="days",
                        description="Number of days to look ahead",
                        type="number",
                        required=False,
                        default=7,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_get_statistics",
                description="Get Sonarr library statistics",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_get_indexers",
                description="Get list of configured indexers in Sonarr",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_test_indexer",
                description="Test a specific indexer in Sonarr by ID",
                parameters=[
                    ToolParameter(
                        name="indexer_id",
                        description="ID of the indexer to test",
                        type="number",
                        required=True,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_test_all_indexers",
                description="Test all enabled indexers in Sonarr",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_check_queue_match",
                description="Check if a TV series/episode is currently downloading in Sonarr queue with fuzzy title matching. Returns detailed download status including progress percentage, download client, file name, quality, episode info, and estimated completion time. Use this to check download status of a specific series or episode.",
                parameters=[
                    ToolParameter(
                        name="title",
                        description="TV series title to search for (fuzzy match)",
                        type="string",
                        required=False,
                    ),
                    ToolParameter(
                        name="series_id",
                        description="Sonarr series ID for exact match",
                        type="number",
                        required=False,
                    ),
                    ToolParameter(
                        name="tvdb_id",
                        description="TVDB ID for exact match",
                        type="number",
                        required=False,
                    ),
                    ToolParameter(
                        name="season",
                        description="Filter results to specific season number",
                        type="number",
                        required=False,
                    ),
                    ToolParameter(
                        name="episode",
                        description="Filter results to specific episode number (requires season)",
                        type="number",
                        required=False,
                    ),
                ],
                category="media",
                is_mutation=False,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_get_quality_profiles",
                description="Get available quality profiles in Sonarr. Use this to get profile IDs before adding a series.",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_get_root_folders",
                description="Get available root folders in Sonarr. Use this to get folder paths before adding a series.",
                parameters=[],
                category="media",
                is_mutation=False,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_add_series",
                description="Add a TV series to Sonarr library. Requires TVDB ID, quality profile ID, and root folder path.",
                parameters=[
                    ToolParameter(
                        name="tvdb_id",
                        description="TVDB ID of the series (get from sonarr_search_series)",
                        type="number",
                        required=True,
                    ),
                    ToolParameter(
                        name="quality_profile_id",
                        description="Quality profile ID (get from sonarr_get_quality_profiles)",
                        type="number",
                        required=True,
                    ),
                    ToolParameter(
                        name="root_folder_path",
                        description="Root folder path (get from sonarr_get_root_folders)",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="monitored",
                        description="Whether to monitor the series for new episodes",
                        type="boolean",
                        required=False,
                        default=True,
                    ),
                    ToolParameter(
                        name="season_folder",
                        description="Whether to use season folders",
                        type="boolean",
                        required=False,
                        default=True,
                    ),
                    ToolParameter(
                        name="search_for_missing",
                        description="Whether to search for missing episodes immediately",
                        type="boolean",
                        required=False,
                        default=True,
                    ),
                    ToolParameter(
                        name="series_type",
                        description="Series type",
                        type="string",
                        required=False,
                        default="standard",
                        enum=["standard", "daily", "anime"],
                    ),
                    ToolParameter(
                        name="monitor",
                        description="Which episodes to monitor",
                        type="string",
                        required=False,
                        default="all",
                        enum=["all", "future", "missing", "existing", "pilot", "firstSeason", "none"],
                    ),
                ],
                category="media",
                is_mutation=True,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_delete_series",
                description="Delete a TV series from Sonarr library.",
                parameters=[
                    ToolParameter(
                        name="series_id",
                        description="Sonarr series ID",
                        type="number",
                        required=True,
                    ),
                    ToolParameter(
                        name="delete_files",
                        description="Also delete downloaded episode files from disk",
                        type="boolean",
                        required=False,
                        default=False,
                    ),
                    ToolParameter(
                        name="add_exclusion",
                        description="Add to import exclusion list to prevent re-adding",
                        type="boolean",
                        required=False,
                        default=False,
                    ),
                ],
                category="media",
                is_mutation=True,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_update_series",
                description="Update a TV series settings in Sonarr (monitored status, quality profile, series type, etc.)",
                parameters=[
                    ToolParameter(
                        name="series_id",
                        description="Sonarr series ID",
                        type="number",
                        required=True,
                    ),
                    ToolParameter(
                        name="monitored",
                        description="Whether to monitor the series",
                        type="boolean",
                        required=False,
                    ),
                    ToolParameter(
                        name="quality_profile_id",
                        description="New quality profile ID",
                        type="number",
                        required=False,
                    ),
                    ToolParameter(
                        name="series_type",
                        description="Series type",
                        type="string",
                        required=False,
                        enum=["standard", "daily", "anime"],
                    ),
                    ToolParameter(
                        name="season_folder",
                        description="Whether to use season folders",
                        type="boolean",
                        required=False,
                    ),
                ],
                category="media",
                is_mutation=True,
                requires_service="sonarr",
            ),
            ToolDefinition(
                name="sonarr_trigger_search",
                description="Trigger an automatic search for missing episodes of a TV series. Optionally search a specific season. Returns download result if content is found and grabbed.",
                parameters=[
                    ToolParameter(
                        name="series_id",
                        description="Sonarr series ID",
                        type="number",
                        required=True,
                    ),
                    ToolParameter(
                        name="season_number",
                        description="Specific season number to search (searches all missing if not specified)",
                        type="number",
                        required=False,
                    ),
                ],
                category="media",
                is_mutation=True,
                requires_service="sonarr",
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute a Sonarr tool."""
        if not self.service_config:
            return {"success": False, "error": "Sonarr service not configured"}

        try:
            from src.adapters.sonarr import SonarrAdapter

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
            adapter = SonarrAdapter(service_proxy)

            if tool_name == "sonarr_search_series":
                return await self._search_series(adapter, arguments)
            elif tool_name == "sonarr_get_series_status":
                return await self._get_series_status(adapter, arguments)
            elif tool_name == "sonarr_get_releases":
                return await self._get_releases(adapter, arguments)
            elif tool_name == "sonarr_get_queue":
                return await self._get_queue(adapter)
            elif tool_name == "sonarr_get_calendar":
                return await self._get_calendar(adapter, arguments)
            elif tool_name == "sonarr_get_statistics":
                return await self._get_statistics(adapter)
            elif tool_name == "sonarr_get_indexers":
                return await self._get_indexers(adapter)
            elif tool_name == "sonarr_test_indexer":
                return await self._test_indexer(adapter, arguments)
            elif tool_name == "sonarr_test_all_indexers":
                return await self._test_all_indexers(adapter)
            elif tool_name == "sonarr_check_queue_match":
                return await self._check_queue_match(adapter, arguments)
            elif tool_name == "sonarr_get_quality_profiles":
                return await self._get_quality_profiles(adapter)
            elif tool_name == "sonarr_get_root_folders":
                return await self._get_root_folders(adapter)
            elif tool_name == "sonarr_add_series":
                return await self._add_series(adapter, arguments)
            elif tool_name == "sonarr_delete_series":
                return await self._delete_series(adapter, arguments)
            elif tool_name == "sonarr_update_series":
                return await self._update_series(adapter, arguments)
            elif tool_name == "sonarr_trigger_search":
                return await self._trigger_search(adapter, arguments)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    async def _search_series(self, adapter, arguments: dict) -> dict:
        """Search for a series."""
        query = arguments.get("query")
        limit = int(arguments.get("limit", 10))
        results = await adapter.search_series(query)

        return {"success": True, "result": {"query": query, "count": len(results), "results": results[:limit]}}

    async def _get_series_status(self, adapter, arguments: dict) -> dict:
        """Get detailed status of a series in Sonarr library."""
        title = arguments.get("title")
        year = arguments.get("year")

        result = await adapter.get_series_by_title(title, year)

        if not result.get("found"):
            return {
                "success": True,
                "result": {
                    "found": False,
                    "title": title,
                    "message": result.get("message", f"Series '{title}' not found in Sonarr library"),
                },
            }

        return {"success": True, "result": result}

    async def _get_releases(self, adapter, arguments: dict) -> dict:
        """Get available releases/torrents for a series (manual search)."""
        series_id = arguments.get("series_id")
        if not series_id:
            return {"success": False, "error": "series_id is required"}

        season_number = arguments.get("season_number")
        result = await adapter.get_releases(int(series_id), season_number=season_number)

        if result.get("error"):
            return {"success": False, "error": result.get("error")}

        return {"success": True, "result": result}

    async def _get_queue(self, adapter) -> dict:
        """Get download queue."""
        queue = await adapter.get_queue()

        return {"success": True, "result": {"count": len(queue), "queue": queue}}

    async def _get_calendar(self, adapter, arguments: dict) -> dict:
        """Get calendar."""
        days = arguments.get("days", 7)
        calendar = await adapter.get_calendar(days=days)

        return {"success": True, "result": {"days": days, "count": len(calendar), "upcoming": calendar}}

    async def _get_statistics(self, adapter) -> dict:
        """Get statistics."""
        stats = await adapter.get_statistics()

        return {"success": True, "result": stats}

    async def _get_indexers(self, adapter) -> dict:
        """Get list of indexers."""
        indexers = await adapter.get_indexers()

        return {
            "success": True,
            "result": {
                "count": len(indexers),
                "enabled_count": sum(1 for i in indexers if i.get("enable")),
                "indexers": indexers,
            },
        }

    async def _test_indexer(self, adapter, arguments: dict) -> dict:
        """Test a specific indexer."""
        indexer_id = arguments.get("indexer_id")
        if not indexer_id:
            return {"success": False, "error": "indexer_id is required"}

        result = await adapter.test_indexer(int(indexer_id))
        return {"success": result.get("success", False), "result": result}

    async def _test_all_indexers(self, adapter) -> dict:
        """Test all enabled indexers."""
        result = await adapter.test_all_indexers()
        return {"success": True, "result": result}

    async def _check_queue_match(self, adapter, arguments: dict) -> dict:
        """Check if a series/episode is in the download queue with fuzzy matching."""
        title = arguments.get("title")
        series_id = arguments.get("series_id")
        tvdb_id = arguments.get("tvdb_id")
        season = arguments.get("season")
        episode = arguments.get("episode")

        if not title and not series_id and not tvdb_id:
            return {"success": False, "error": "At least one of title, series_id, or tvdb_id is required"}

        result = await adapter.check_queue_match(
            title=title,
            series_id=int(series_id) if series_id else None,
            tvdb_id=int(tvdb_id) if tvdb_id else None,
            season=int(season) if season is not None else None,
            episode=int(episode) if episode is not None else None,
        )

        if result.get("error"):
            return {"success": False, "error": result.get("error")}

        return {"success": True, "result": result}

    async def _get_quality_profiles(self, adapter) -> dict:
        """Get available quality profiles."""
        profiles = await adapter.get_quality_profiles()

        return {
            "success": True,
            "result": {
                "count": len(profiles),
                "profiles": profiles,
            },
        }

    async def _get_root_folders(self, adapter) -> dict:
        """Get available root folders."""
        folders = await adapter.get_root_folders()

        return {
            "success": True,
            "result": {
                "count": len(folders),
                "folders": folders,
            },
        }

    async def _add_series(self, adapter, arguments: dict) -> dict:
        """Add a series to Sonarr."""
        tvdb_id = arguments.get("tvdb_id")
        quality_profile_id = arguments.get("quality_profile_id")
        root_folder_path = arguments.get("root_folder_path")

        if not tvdb_id:
            return {"success": False, "error": "tvdb_id is required"}
        if not quality_profile_id:
            return {"success": False, "error": "quality_profile_id is required"}
        if not root_folder_path:
            return {"success": False, "error": "root_folder_path is required"}

        result = await adapter.add_series(
            tvdb_id=int(tvdb_id),
            quality_profile_id=int(quality_profile_id),
            root_folder_path=root_folder_path,
            monitored=arguments.get("monitored", True),
            season_folder=arguments.get("season_folder", True),
            search_for_missing=arguments.get("search_for_missing", True),
            series_type=arguments.get("series_type", "standard"),
            monitor=arguments.get("monitor", "all"),
        )

        if result.get("error") and not result.get("success"):
            return {"success": False, "error": result.get("error"), "details": result}

        return {"success": True, "result": result}

    async def _delete_series(self, adapter, arguments: dict) -> dict:
        """Delete a series from Sonarr."""
        series_id = arguments.get("series_id")

        if not series_id:
            return {"success": False, "error": "series_id is required"}

        result = await adapter.delete_series(
            series_id=int(series_id),
            delete_files=arguments.get("delete_files", False),
            add_exclusion=arguments.get("add_exclusion", False),
        )

        if result.get("error") and not result.get("success"):
            return {"success": False, "error": result.get("error")}

        return {"success": True, "result": result}

    async def _update_series(self, adapter, arguments: dict) -> dict:
        """Update a series in Sonarr."""
        series_id = arguments.get("series_id")

        if not series_id:
            return {"success": False, "error": "series_id is required"}

        result = await adapter.update_series(
            series_id=int(series_id),
            monitored=arguments.get("monitored"),
            quality_profile_id=int(arguments["quality_profile_id"]) if arguments.get("quality_profile_id") else None,
            series_type=arguments.get("series_type"),
            season_folder=arguments.get("season_folder"),
        )

        if result.get("error") and not result.get("success"):
            return {"success": False, "error": result.get("error")}

        return {"success": True, "result": result}

    async def _trigger_search(self, adapter, arguments: dict) -> dict:
        """Trigger an automatic search for a series."""
        series_id = arguments.get("series_id")

        if not series_id:
            return {"success": False, "error": "series_id is required"}

        season_number = arguments.get("season_number")

        result = await adapter.trigger_search(
            series_id=int(series_id),
            season_number=int(season_number) if season_number is not None else None,
        )

        if result.get("error") and not result.get("success"):
            return {"success": False, "error": result.get("error")}

        return {"success": True, "result": result}
