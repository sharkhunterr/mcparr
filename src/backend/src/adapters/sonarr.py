"""Sonarr TV series management adapter."""

from datetime import datetime
from typing import Any, Dict, List

import httpx

from .base import ConnectionTestResult, ServiceCapability, TokenAuthAdapter


class SonarrAdapter(TokenAuthAdapter):
    """Adapter for Sonarr TV series download management."""

    @property
    def service_type(self) -> str:
        return "sonarr"

    def _get_series_url(self, series_id: int) -> str:
        """Generate Sonarr web UI URL for a series."""
        if series_id:
            return f"{self.public_url}/series/{series_id}"
        return ""

    def _get_tvdb_url(self, tvdb_id: int) -> str:
        """Generate TVDB external URL."""
        if tvdb_id:
            return f"https://thetvdb.com/?id={tvdb_id}&tab=series"
        return ""

    def _get_imdb_url(self, imdb_id: str) -> str:
        """Generate IMDB external URL."""
        if imdb_id:
            return f"https://www.imdb.com/title/{imdb_id}"
        return ""

    @property
    def supported_capabilities(self) -> List[ServiceCapability]:
        return [ServiceCapability.MEDIA_CONTENT, ServiceCapability.API_ACCESS]

    @property
    def token_config_key(self) -> str:
        return "sonarr_api_key"

    def _format_token_header(self, token: str) -> Dict[str, str]:
        """Format Sonarr API key header."""
        return {"X-Api-Key": token, "Content-Type": "application/json", "Accept": "application/json"}

    async def test_connection(self) -> ConnectionTestResult:
        """Test connection to Sonarr."""
        start_time = datetime.utcnow()

        try:
            response = await self._make_request("GET", "/api/v3/system/status")
            end_time = datetime.utcnow()
            response_time = int((end_time - start_time).total_seconds() * 1000)

            data = response.json()

            if "version" in data:
                return ConnectionTestResult(
                    success=True,
                    message="Successfully connected to Sonarr",
                    response_time_ms=response_time,
                    details={
                        "status": "connected",
                        "version": data.get("version"),
                        "app_name": data.get("appName", "Sonarr"),
                        "branch": data.get("branch"),
                    },
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message="Connected but response doesn't appear to be from Sonarr",
                    response_time_ms=response_time,
                    details={"status": "invalid_response"},
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return ConnectionTestResult(
                    success=False,
                    message="Authentication failed - check API key",
                    details={"status": "auth_failed", "status_code": 401},
                )
            return ConnectionTestResult(
                success=False,
                message=f"HTTP error: {e.response.status_code}",
                details={"status": "http_error", "status_code": e.response.status_code},
            )
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                details={"status": "connection_failed", "error": str(e)},
            )

    async def get_service_info(self) -> Dict[str, Any]:
        """Get Sonarr service information."""
        try:
            response = await self._make_request("GET", "/api/v3/system/status")
            data = response.json()

            return {
                "service": "sonarr",
                "version": data.get("version"),
                "app_name": data.get("appName", "Sonarr"),
                "branch": data.get("branch"),
                "build_time": data.get("buildTime"),
                "runtime_version": data.get("runtimeVersion"),
                "status": "online",
            }
        except Exception as e:
            return {"service": "sonarr", "version": "unknown", "status": "error", "error": str(e)}

    async def get_series(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of TV series in Sonarr."""
        try:
            response = await self._make_request("GET", "/api/v3/series")
            series_list = response.json()

            return [
                {
                    "id": series.get("id"),
                    "title": series.get("title"),
                    "year": series.get("year"),
                    "tvdb_id": series.get("tvdbId"),
                    "imdb_id": series.get("imdbId"),
                    "status": series.get("status"),
                    "monitored": series.get("monitored", False),
                    "season_count": series.get("seasonCount", 0),
                    "episode_count": series.get("episodeCount", 0),
                    "episode_file_count": series.get("episodeFileCount", 0),
                    "path": series.get("path"),
                    "size_on_disk": series.get("sizeOnDisk", 0),
                    "network": series.get("network"),
                    "url": self._get_series_url(series.get("id")),
                    "tvdb_url": self._get_tvdb_url(series.get("tvdbId")),
                    "imdb_url": self._get_imdb_url(series.get("imdbId")),
                }
                for series in series_list[:limit]
            ]
        except Exception as e:
            self.logger.error(f"Failed to get series: {e}")
            return []

    def _calculate_match_score(self, query: str, title: str) -> int:
        """Calculate a match score (0-100) between query and title."""
        if not query or not title:
            return 0

        query_lower = query.lower().strip()
        title_lower = title.lower().strip()

        # Exact match
        if query_lower == title_lower:
            return 100

        # Title starts with query
        if title_lower.startswith(query_lower):
            return 90

        # Query is contained in title
        if query_lower in title_lower:
            base_score = 70
            # Bonus for shorter titles (more specific match)
            length_ratio = len(query_lower) / len(title_lower)
            return min(89, int(base_score + length_ratio * 19))

        # Word-based matching
        query_words = set(query_lower.split())
        title_words = set(title_lower.split())

        if query_words and title_words:
            common_words = query_words & title_words
            if common_words:
                word_score = len(common_words) / max(len(query_words), len(title_words))
                return int(40 + word_score * 29)

        return 20  # Low score for partial/fuzzy matches

    async def search_series(self, query: str) -> List[Dict[str, Any]]:
        """Search for series to add with match scoring."""
        try:
            response = await self._make_request("GET", "/api/v3/series/lookup", params={"term": query})
            results = response.json()

            # Get quality profiles for library series
            quality_profiles = {}
            try:
                profiles_response = await self._make_request("GET", "/api/v3/qualityprofile")
                for profile in profiles_response.json():
                    quality_profiles[profile.get("id")] = profile.get("name")
            except Exception:
                pass

            formatted_results = []
            for series in results[:20]:
                match_score = self._calculate_match_score(query, series.get("title", ""))
                in_library = series.get("id") is not None

                result = {
                    "title": series.get("title"),
                    "year": series.get("year"),
                    "tvdb_id": series.get("tvdbId"),
                    "imdb_id": series.get("imdbId"),
                    "overview": series.get("overview", "")[:200],
                    "network": series.get("network"),
                    "season_count": series.get("seasonCount", 0),
                    "in_library": in_library,
                    "match_score": match_score,
                    "tvdb_url": self._get_tvdb_url(series.get("tvdbId")),
                    "imdb_url": self._get_imdb_url(series.get("imdbId")),
                }

                # If in library, add more details
                if in_library:
                    result["sonarr_id"] = series.get("id")
                    result["monitored"] = series.get("monitored", False)
                    result["status"] = series.get("status")
                    result["episode_count"] = series.get("episodeCount", 0)
                    result["episode_file_count"] = series.get("episodeFileCount", 0)
                    profile_id = series.get("qualityProfileId")
                    if profile_id and profile_id in quality_profiles:
                        result["quality_profile"] = quality_profiles[profile_id]
                    result["url"] = self._get_series_url(series.get("id"))

                formatted_results.append(result)

            # Sort by match_score descending
            formatted_results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
            return formatted_results
        except Exception as e:
            self.logger.error(f"Failed to search series: {e}")
            return []

    async def get_series_by_title(self, title: str, year: int = None) -> Dict[str, Any]:
        """Get a specific series from Sonarr library by title."""
        try:
            response = await self._make_request("GET", "/api/v3/series")
            series_list = response.json()

            # Get quality profiles
            quality_profiles = {}
            try:
                profiles_response = await self._make_request("GET", "/api/v3/qualityprofile")
                for profile in profiles_response.json():
                    quality_profiles[profile.get("id")] = profile.get("name")
            except Exception:
                pass

            title.lower().strip()
            best_match = None
            best_score = 0

            for series in series_list:
                series.get("title", "").lower().strip()
                series_year = series.get("year")

                # Calculate match score
                score = self._calculate_match_score(title, series.get("title", ""))

                # Year matching bonus
                if year and series_year:
                    if series_year == year:
                        score += 10
                    elif abs(series_year - year) <= 1:
                        score += 5

                if score > best_score:
                    best_score = score
                    best_match = series

            if not best_match or best_score < 50:
                return {
                    "found": False,
                    "message": f"Series '{title}' not found in Sonarr library",
                    "suggestion": "Use sonarr_search_series to find and add the series first",
                }

            profile_id = best_match.get("qualityProfileId")
            profile_name = quality_profiles.get(profile_id, "Unknown")

            return {
                "found": True,
                "match_score": min(best_score, 100),
                "sonarr_id": best_match.get("id"),
                "title": best_match.get("title"),
                "year": best_match.get("year"),
                "status": best_match.get("status"),
                "monitored": best_match.get("monitored", False),
                "season_count": best_match.get("seasonCount", 0),
                "episode_count": best_match.get("episodeCount", 0),
                "episode_file_count": best_match.get("episodeFileCount", 0),
                "missing_episodes": best_match.get("episodeCount", 0) - best_match.get("episodeFileCount", 0),
                "size_on_disk": best_match.get("sizeOnDisk", 0),
                "size_on_disk_gb": round(best_match.get("sizeOnDisk", 0) / (1024**3), 2),
                "quality_profile_id": profile_id,
                "quality_profile": profile_name,
                "path": best_match.get("path"),
                "tvdb_id": best_match.get("tvdbId"),
                "imdb_id": best_match.get("imdbId"),
                "network": best_match.get("network"),
                "url": self._get_series_url(best_match.get("id")),
                "tvdb_url": self._get_tvdb_url(best_match.get("tvdbId")),
                "imdb_url": self._get_imdb_url(best_match.get("imdbId")),
            }
        except Exception as e:
            self.logger.error(f"Failed to get series by title: {e}")
            return {"found": False, "error": str(e)}

    async def get_releases(self, series_id: int, season_number: int = None, episode_id: int = None) -> Dict[str, Any]:
        """Get available releases/torrents for a series (manual search)."""
        try:
            params = {"seriesId": series_id}
            if season_number is not None:
                params["seasonNumber"] = season_number
            if episode_id is not None:
                params["episodeId"] = episode_id

            response = await self._make_request("GET", "/api/v3/release", params=params, timeout=120.0)
            releases = response.json()

            formatted_releases = []
            approved_count = 0
            rejected_count = 0

            for release in releases[:50]:  # Limit to 50 releases
                is_approved = release.get("approved", False)
                if is_approved:
                    approved_count += 1
                else:
                    rejected_count += 1

                formatted_release = {
                    "title": release.get("title"),
                    "indexer": release.get("indexer"),
                    "quality": release.get("quality", {}).get("quality", {}).get("name"),
                    "quality_weight": release.get("qualityWeight", 0),
                    "language": [lang.get("name") for lang in release.get("languages", [])],
                    "size": release.get("size", 0),
                    "size_gb": round(release.get("size", 0) / (1024**3), 2),
                    "seeders": release.get("seeders"),
                    "leechers": release.get("leechers"),
                    "protocol": release.get("protocol"),
                    "approved": is_approved,
                    "temporarily_rejected": release.get("temporarilyRejected", False),
                    "rejections": release.get("rejections", []),
                    "season_number": release.get("seasonNumber"),
                    "full_season": release.get("fullSeason", False),
                    "episode_numbers": release.get("episodeNumbers", []),
                    "age_days": release.get("ageMinutes", 0) // 1440,
                }
                formatted_releases.append(formatted_release)

            return {
                "series_id": series_id,
                "season_number": season_number,
                "episode_id": episode_id,
                "total_releases": len(releases),
                "shown_releases": len(formatted_releases),
                "approved_count": approved_count,
                "rejected_count": rejected_count,
                "releases": formatted_releases,
                "summary": {
                    "has_approved_releases": approved_count > 0,
                    "best_seeders": max((r.get("seeders") or 0 for r in formatted_releases), default=0),
                    "indexers_with_results": list({r.get("indexer") for r in formatted_releases if r.get("indexer")}),
                },
            }
        except Exception as e:
            self.logger.error(f"Failed to get releases: {e}")
            return {"error": str(e), "series_id": series_id}

    async def get_queue(self) -> List[Dict[str, Any]]:
        """Get download queue."""
        try:
            response = await self._make_request(
                "GET",
                "/api/v3/queue",
                params={"includeSeries": "true", "includeEpisode": "true"},
            )
            data = response.json()

            return [
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "series_title": item.get("series", {}).get("title"),
                    "episode_title": item.get("episode", {}).get("title"),
                    "season": item.get("episode", {}).get("seasonNumber"),
                    "episode": item.get("episode", {}).get("episodeNumber"),
                    "status": item.get("status"),
                    "progress": (1 - item.get("sizeleft", 0) / item.get("size", 1)) * 100 if item.get("size") else 0,
                    "download_client": item.get("downloadClient"),
                    "estimated_completion": item.get("estimatedCompletionTime"),
                }
                for item in data.get("records", [])
            ]
        except Exception as e:
            self.logger.error(f"Failed to get queue: {e}")
            return []

    async def get_calendar(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming episodes."""
        try:
            from datetime import timedelta

            start = datetime.utcnow()
            end = start + timedelta(days=days)

            response = await self._make_request(
                "GET",
                "/api/v3/calendar",
                params={"start": start.isoformat(), "end": end.isoformat(), "includeSeries": "true"},
            )
            episodes = response.json()

            return [
                {
                    "id": ep.get("id"),
                    "series_id": ep.get("seriesId"),
                    "series_title": ep.get("series", {}).get("title"),
                    "title": ep.get("title"),
                    "season": ep.get("seasonNumber"),
                    "episode": ep.get("episodeNumber"),
                    "air_date": ep.get("airDateUtc"),
                    "has_file": ep.get("hasFile", False),
                    "url": self._get_series_url(ep.get("seriesId")),
                }
                for ep in episodes
            ]
        except Exception as e:
            self.logger.error(f"Failed to get calendar: {e}")
            return []

    async def get_statistics(self) -> Dict[str, Any]:
        """Get Sonarr statistics."""
        try:
            series = await self.get_series(limit=10000)
            queue = await self.get_queue()

            total_series = len(series)
            monitored = sum(1 for s in series if s.get("monitored"))
            total_episodes = sum(s.get("episode_count", 0) for s in series)
            total_files = sum(s.get("episode_file_count", 0) for s in series)
            total_size = sum(s.get("size_on_disk", 0) for s in series)

            return {
                "total_series": total_series,
                "monitored_series": monitored,
                "total_episodes": total_episodes,
                "episodes_with_files": total_files,
                "missing_episodes": total_episodes - total_files,
                "queue_count": len(queue),
                "total_size_gb": round(total_size / (1024**3), 2),
            }
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                "total_series": 0,
                "monitored_series": 0,
                "total_episodes": 0,
                "episodes_with_files": 0,
                "missing_episodes": 0,
                "queue_count": 0,
                "total_size_gb": 0,
            }

    async def get_indexers(self) -> List[Dict[str, Any]]:
        """Get list of configured indexers in Sonarr."""
        try:
            response = await self._make_request("GET", "/api/v3/indexer")
            indexers = response.json()

            return [
                {
                    "id": indexer.get("id"),
                    "name": indexer.get("name"),
                    "protocol": indexer.get("protocol"),
                    # Support both old 'enable' and newer 'enableRss'/'enableAutomaticSearch' fields
                    "enable": indexer.get("enable", False)
                    or indexer.get("enableRss", False)
                    or indexer.get("enableAutomaticSearch", False),
                    "enableRss": indexer.get("enableRss", False),
                    "enableAutomaticSearch": indexer.get("enableAutomaticSearch", False),
                    "enableInteractiveSearch": indexer.get("enableInteractiveSearch", False),
                    "priority": indexer.get("priority", 25),
                    "supports_rss": indexer.get("supportsRss", False),
                    "supports_search": indexer.get("supportsSearch", False),
                    "implementation": indexer.get("implementation"),
                    "config_contract": indexer.get("configContract"),
                }
                for indexer in indexers
            ]
        except Exception as e:
            self.logger.error(f"Failed to get indexers: {e}")
            return []

    async def test_indexer(self, indexer_id: int) -> Dict[str, Any]:
        """Test a specific indexer by ID."""
        try:
            # First get the indexer config
            response = await self._make_request("GET", f"/api/v3/indexer/{indexer_id}")
            indexer_config = response.json()
            indexer_name = indexer_config.get("name", f"Indexer {indexer_id}")

            # Then test it
            await self._make_request("POST", "/api/v3/indexer/test", json=indexer_config, timeout=60.0)

            return {
                "success": True,
                "indexer_id": indexer_id,
                "indexer_name": indexer_name,
                "message": "Indexer test passed",
            }
        except httpx.HTTPStatusError as e:
            error_msg = "Test failed"
            try:
                error_data = e.response.json()
                if isinstance(error_data, list) and error_data:
                    error_msg = error_data[0].get("errorMessage", str(e))
                elif isinstance(error_data, dict):
                    error_msg = error_data.get("message", str(e))
            except Exception:
                error_msg = str(e)

            return {"success": False, "indexer_id": indexer_id, "error": error_msg}
        except Exception as e:
            return {"success": False, "indexer_id": indexer_id, "error": str(e)}

    async def test_all_indexers(self) -> Dict[str, Any]:
        """Test all enabled indexers."""
        indexers = await self.get_indexers()
        # Filter enabled indexers - check both 'enable' (v3) and 'enableRss'/'enableAutomaticSearch' fields
        enabled_indexers = [
            i for i in indexers if i.get("enable") or i.get("enableRss") or i.get("enableAutomaticSearch")
        ]

        # If no enabled indexers but we have indexers, test all of them
        if not enabled_indexers and indexers:
            enabled_indexers = indexers

        results = []
        for indexer in enabled_indexers:
            result = await self.test_indexer(indexer["id"])
            result["indexer_name"] = indexer.get("name")
            results.append(result)

        success_count = sum(1 for r in results if r.get("success"))
        return {
            "total_tested": len(results),
            "success_count": success_count,
            "failed_count": len(results) - success_count,
            "total_indexers": len(indexers),
            "results": results,
        }

    def _calculate_fuzzy_match_score(self, query: str, target: str) -> int:
        """Calculate fuzzy match score between two strings (0-100).

        Uses word-based and substring matching for better results.
        """
        if not query or not target:
            return 0

        query_lower = query.lower().strip()
        target_lower = target.lower().strip()

        # Exact match
        if query_lower == target_lower:
            return 100

        # Target starts with query
        if target_lower.startswith(query_lower):
            return 95

        # Query starts with target (useful for abbreviated titles)
        if query_lower.startswith(target_lower):
            return 90

        # Query is contained in target
        if query_lower in target_lower:
            base_score = 75
            length_ratio = len(query_lower) / len(target_lower)
            return min(89, int(base_score + length_ratio * 14))

        # Target is contained in query
        if target_lower in query_lower:
            base_score = 65
            length_ratio = len(target_lower) / len(query_lower)
            return min(79, int(base_score + length_ratio * 14))

        # Word-based matching
        # Remove common words and punctuation for better matching
        import re

        def clean_words(text: str) -> set:
            text = re.sub(r"[^\w\s]", " ", text)
            stop_words = {"the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "with", "at", "by", "is", "it"}
            return {w for w in text.lower().split() if w and w not in stop_words}

        query_words = clean_words(query_lower)
        target_words = clean_words(target_lower)

        if query_words and target_words:
            common_words = query_words & target_words
            if common_words:
                # Calculate overlap ratio
                total_words = len(query_words | target_words)
                overlap_ratio = len(common_words) / total_words
                return int(30 + overlap_ratio * 49)

        # Very low score for no meaningful match
        return 10

    async def check_queue_match(
        self,
        title: str = None,
        series_id: int = None,
        tvdb_id: int = None,
        season: int = None,
        episode: int = None,
    ) -> Dict[str, Any]:
        """Check if a series/episode is in the download queue with fuzzy title matching.

        Args:
            title: Series title to search for (fuzzy match)
            series_id: Sonarr series ID (exact match)
            tvdb_id: TVDB ID (exact match)
            season: Optional season number to filter results
            episode: Optional episode number to filter results

        Returns detailed queue item info including match score, download progress,
        client, and status.
        """
        try:
            # Get detailed queue with series/episode info
            response = await self._make_request(
                "GET",
                "/api/v3/queue",
                params={"includeSeries": "true", "includeEpisode": "true", "pageSize": 500},
            )
            data = response.json()
            records = data.get("records", [])

            if not records:
                return {
                    "found": False,
                    "message": "Download queue is empty",
                    "queue_count": 0,
                }

            matches = []

            for item in records:
                series = item.get("series", {})
                episode_info = item.get("episode", {})
                item_series_id = series.get("id")
                item_tvdb_id = series.get("tvdbId")
                item_title = series.get("title", "")
                item_year = series.get("year")
                item_season = episode_info.get("seasonNumber")
                item_episode = episode_info.get("episodeNumber")

                match_score = 0
                match_type = None

                # Check exact ID matches first
                if series_id and item_series_id == series_id:
                    match_score = 100
                    match_type = "series_id"
                elif tvdb_id and item_tvdb_id == tvdb_id:
                    match_score = 100
                    match_type = "tvdb_id"
                elif title:
                    # Fuzzy title matching
                    match_score = self._calculate_fuzzy_match_score(title, item_title)
                    match_type = "title"

                # Apply season/episode filter if provided
                if match_score >= 30:
                    if season is not None and item_season != season:
                        continue
                    if episode is not None and item_episode != episode:
                        continue

                if match_score >= 30:  # Minimum threshold for inclusion
                    # Calculate progress
                    size = item.get("size", 0)
                    size_left = item.get("sizeleft", 0)
                    progress = ((size - size_left) / size * 100) if size > 0 else 0

                    # Get status message
                    status = item.get("status", "unknown")
                    tracked_status = item.get("trackedDownloadStatus", "")
                    status_messages = item.get("statusMessages", [])

                    # Extract any error/warning messages
                    messages = []
                    for msg in status_messages:
                        if isinstance(msg, dict):
                            messages.extend(msg.get("messages", []))
                        elif isinstance(msg, str):
                            messages.append(msg)

                    matches.append(
                        {
                            "match_score": match_score,
                            "match_type": match_type,
                            "queue_id": item.get("id"),
                            "series": {
                                "id": item_series_id,
                                "tvdb_id": item_tvdb_id,
                                "title": item_title,
                                "year": item_year,
                                "url": self._get_series_url(item_series_id),
                                "tvdb_url": self._get_tvdb_url(item_tvdb_id),
                            },
                            "episode": {
                                "id": episode_info.get("id"),
                                "title": episode_info.get("title"),
                                "season": item_season,
                                "episode": item_episode,
                                "episode_code": f"S{item_season:02d}E{item_episode:02d}" if item_season and item_episode else None,
                                "air_date": episode_info.get("airDateUtc"),
                            },
                            "download": {
                                "title": item.get("title"),  # Release/torrent name
                                "status": status,
                                "tracked_status": tracked_status,
                                "progress_percent": round(progress, 1),
                                "size_bytes": size,
                                "size_left_bytes": size_left,
                                "size_gb": round(size / (1024**3), 2) if size else 0,
                                "download_client": item.get("downloadClient"),
                                "indexer": item.get("indexer"),
                                "protocol": item.get("protocol"),
                                "estimated_completion": item.get("estimatedCompletionTime"),
                                "added": item.get("added"),
                                "messages": messages if messages else None,
                            },
                            "quality": {
                                "name": item.get("quality", {}).get("quality", {}).get("name"),
                                "source": item.get("quality", {}).get("quality", {}).get("source"),
                                "resolution": item.get("quality", {}).get("quality", {}).get("resolution"),
                            },
                        }
                    )

            # Sort by match score descending, then by season/episode
            matches.sort(key=lambda x: (x["match_score"], x["episode"].get("season", 0), x["episode"].get("episode", 0)), reverse=True)

            if not matches:
                search_term = title or f"series_id:{series_id}" or f"tvdb_id:{tvdb_id}"
                filter_info = ""
                if season is not None:
                    filter_info = f" (Season {season}"
                    if episode is not None:
                        filter_info += f", Episode {episode}"
                    filter_info += ")"
                return {
                    "found": False,
                    "message": f"No matching item found in queue for '{search_term}'{filter_info}",
                    "queue_count": len(records),
                }

            # Return best match and all matches above threshold
            best_match = matches[0]
            return {
                "found": True,
                "best_match": best_match,
                "all_matches": matches[:10],  # Limit to top 10
                "total_matches": len(matches),
                "queue_count": len(records),
            }

        except Exception as e:
            self.logger.error(f"Failed to check queue match: {e}")
            return {"found": False, "error": str(e)}
