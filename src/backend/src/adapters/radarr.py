"""Radarr movie management adapter."""

from datetime import datetime
from typing import Any, Dict, List

import httpx

from .base import ConnectionTestResult, ServiceCapability, TokenAuthAdapter


class RadarrAdapter(TokenAuthAdapter):
    """Adapter for Radarr movie download management."""

    @property
    def service_type(self) -> str:
        return "radarr"

    def _get_movie_url(self, movie_id: int) -> str:
        """Generate Radarr web UI URL for a movie."""
        if movie_id:
            return f"{self.public_url}/movie/{movie_id}"
        return ""

    def _get_tmdb_url(self, tmdb_id: int) -> str:
        """Generate TMDB external URL."""
        if tmdb_id:
            return f"https://www.themoviedb.org/movie/{tmdb_id}"
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
        return "radarr_api_key"

    def _format_token_header(self, token: str) -> Dict[str, str]:
        """Format Radarr API key header."""
        return {"X-Api-Key": token, "Content-Type": "application/json", "Accept": "application/json"}

    async def test_connection(self) -> ConnectionTestResult:
        """Test connection to Radarr."""
        start_time = datetime.utcnow()

        try:
            response = await self._make_request("GET", "/api/v3/system/status")
            end_time = datetime.utcnow()
            response_time = int((end_time - start_time).total_seconds() * 1000)

            data = response.json()

            if "version" in data:
                return ConnectionTestResult(
                    success=True,
                    message="Successfully connected to Radarr",
                    response_time_ms=response_time,
                    details={
                        "status": "connected",
                        "version": data.get("version"),
                        "app_name": data.get("appName", "Radarr"),
                        "branch": data.get("branch"),
                    },
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message="Connected but response doesn't appear to be from Radarr",
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
        """Get Radarr service information."""
        try:
            response = await self._make_request("GET", "/api/v3/system/status")
            data = response.json()

            return {
                "service": "radarr",
                "version": data.get("version"),
                "app_name": data.get("appName", "Radarr"),
                "branch": data.get("branch"),
                "build_time": data.get("buildTime"),
                "runtime_version": data.get("runtimeVersion"),
                "status": "online",
            }
        except Exception as e:
            return {"service": "radarr", "version": "unknown", "status": "error", "error": str(e)}

    async def get_movies(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of movies in Radarr."""
        try:
            response = await self._make_request("GET", "/api/v3/movie")
            movies = response.json()

            return [
                {
                    "id": movie.get("id"),
                    "title": movie.get("title"),
                    "year": movie.get("year"),
                    "tmdb_id": movie.get("tmdbId"),
                    "imdb_id": movie.get("imdbId"),
                    "has_file": movie.get("hasFile", False),
                    "monitored": movie.get("monitored", False),
                    "status": movie.get("status"),
                    "quality_profile_id": movie.get("qualityProfileId"),
                    "path": movie.get("path"),
                    "size_on_disk": movie.get("sizeOnDisk", 0),
                    "url": self._get_movie_url(movie.get("id")),
                    "tmdb_url": self._get_tmdb_url(movie.get("tmdbId")),
                    "imdb_url": self._get_imdb_url(movie.get("imdbId")),
                }
                for movie in movies[:limit]
            ]
        except Exception as e:
            self.logger.error(f"Failed to get movies: {e}")
            return []

    async def get_movie_by_title(self, title: str, year: int = None) -> Dict[str, Any]:
        """Get a specific movie from Radarr library by title.

        Searches for a movie in the local Radarr library (not TMDB lookup).
        Returns detailed status information about the movie.
        """
        try:
            response = await self._make_request("GET", "/api/v3/movie")
            movies = response.json()

            # Normalize search title
            search_title = title.lower().strip()

            # Score and find best match
            best_match = None
            best_score = 0

            for movie in movies:
                movie_title = (movie.get("title") or "").lower()
                movie_year = movie.get("year")

                score = 0
                # Exact match
                if movie_title == search_title:
                    score = 100
                # Title contains search term
                elif search_title in movie_title:
                    score = 50
                # Search term contains title
                elif movie_title in search_title:
                    score = 40

                # Year bonus if provided and matches
                if year and movie_year == year:
                    score += 30
                elif year and movie_year and abs(movie_year - year) <= 1:
                    score += 10

                if score > best_score:
                    best_score = score
                    best_match = movie

            if not best_match or best_score < 40:
                return {"found": False, "message": f"Movie '{title}' not found in Radarr library"}

            # Get quality profile name
            quality_profile_id = best_match.get("qualityProfileId")
            quality_profile_name = None
            try:
                profiles_response = await self._make_request("GET", "/api/v3/qualityprofile")
                profiles = profiles_response.json()
                for profile in profiles:
                    if profile.get("id") == quality_profile_id:
                        quality_profile_name = profile.get("name")
                        break
            except Exception:
                pass

            return {
                "found": True,
                "id": best_match.get("id"),
                "title": best_match.get("title"),
                "year": best_match.get("year"),
                "tmdb_id": best_match.get("tmdbId"),
                "imdb_id": best_match.get("imdbId"),
                "has_file": best_match.get("hasFile", False),
                "monitored": best_match.get("monitored", False),
                "status": best_match.get("status"),  # released, announced, inCinemas
                "is_available": best_match.get("isAvailable", False),
                "quality_profile": quality_profile_name,
                "quality_profile_id": quality_profile_id,
                "path": best_match.get("path"),
                "size_on_disk": best_match.get("sizeOnDisk", 0),
                "added": best_match.get("added"),
                "movie_file": {
                    "quality": best_match.get("movieFile", {}).get("quality", {}).get("quality", {}).get("name")
                    if best_match.get("movieFile")
                    else None,
                    "size": best_match.get("movieFile", {}).get("size") if best_match.get("movieFile") else None,
                    "date_added": best_match.get("movieFile", {}).get("dateAdded")
                    if best_match.get("movieFile")
                    else None,
                },
                "url": self._get_movie_url(best_match.get("id")),
            }
        except Exception as e:
            self.logger.error(f"Failed to get movie by title '{title}': {e}")
            return {"found": False, "error": str(e)}

    async def search_movie(self, query: str) -> List[Dict[str, Any]]:
        """Search for movies to add (TMDB lookup).

        Returns search results with title match score and local library status.
        """
        try:
            response = await self._make_request("GET", "/api/v3/movie/lookup", params={"term": query})
            results = response.json()

            # Normalize query for matching
            query_lower = query.lower().strip()

            search_results = []
            for movie in results[:20]:
                title = movie.get("title") or ""
                title_lower = title.lower()

                # Calculate title match score (0-100)
                if title_lower == query_lower:
                    match_score = 100
                elif query_lower in title_lower:
                    # Query is contained in title
                    match_score = 70 + (30 * len(query_lower) / len(title_lower))
                elif title_lower in query_lower:
                    # Title is contained in query
                    match_score = 50 + (20 * len(title_lower) / len(query_lower))
                else:
                    # Partial word matching
                    query_words = set(query_lower.split())
                    title_words = set(title_lower.split())
                    common_words = query_words & title_words
                    if common_words:
                        match_score = 30 + (40 * len(common_words) / max(len(query_words), len(title_words)))
                    else:
                        match_score = 10

                # Round to integer
                match_score = int(match_score)

                # Check if in library (has local Radarr ID)
                radarr_id = movie.get("id")
                in_library = radarr_id is not None

                result = {
                    "title": title,
                    "year": movie.get("year"),
                    "tmdb_id": movie.get("tmdbId"),
                    "imdb_id": movie.get("imdbId"),
                    "overview": movie.get("overview", "")[:200],
                    "match_score": match_score,
                    "in_library": in_library,
                    "tmdb_url": self._get_tmdb_url(movie.get("tmdbId")),
                    "imdb_url": self._get_imdb_url(movie.get("imdbId")),
                }

                # If in library, add local status
                if in_library:
                    result["radarr_id"] = radarr_id
                    result["has_file"] = movie.get("hasFile", False)
                    result["monitored"] = movie.get("monitored", False)
                    result["status"] = movie.get("status")
                    result["url"] = self._get_movie_url(radarr_id)

                search_results.append(result)

            # Sort by match score descending
            search_results.sort(key=lambda x: x["match_score"], reverse=True)

            return search_results
        except Exception as e:
            self.logger.error(f"Failed to search movies: {e}")
            return []

    async def get_releases(self, movie_id: int) -> Dict[str, Any]:
        """Get available releases/torrents for a movie (manual search).

        Returns list of available releases from indexers with quality, language,
        seeders, size, and compatibility info.
        """
        try:
            response = await self._make_request("GET", "/api/v3/release", params={"movieId": movie_id})
            releases = response.json()

            # Get quality profiles for reference
            quality_profiles = {}
            try:
                profiles_response = await self._make_request("GET", "/api/v3/qualityprofile")
                for profile in profiles_response.json():
                    quality_profiles[profile.get("id")] = profile.get("name")
            except Exception:
                pass

            formatted_releases = []
            for release in releases[:50]:  # Limit to 50 releases
                quality = release.get("quality", {}).get("quality", {})
                languages = release.get("languages", [])

                # Get rejection reasons if any
                rejections = release.get("rejections", [])

                formatted_releases.append(
                    {
                        "title": release.get("title"),
                        "indexer": release.get("indexer"),
                        "quality": quality.get("name"),
                        "quality_source": quality.get("source"),
                        "resolution": quality.get("resolution"),
                        "languages": [lang.get("name") for lang in languages if lang.get("name")],
                        "size_bytes": release.get("size", 0),
                        "size_gb": round(release.get("size", 0) / (1024**3), 2),
                        "seeders": release.get("seeders"),
                        "leechers": release.get("leechers"),
                        "age_days": release.get("ageMinutes", 0) // 1440 if release.get("ageMinutes") else None,
                        "approved": release.get("approved", False),
                        "download_allowed": release.get("downloadAllowed", False),
                        "rejections": rejections[:3] if rejections else None,  # Limit rejection reasons
                        "custom_format_score": release.get("customFormatScore"),
                        "guid": release.get("guid"),
                    }
                )

            # Summary stats
            approved_count = sum(1 for r in formatted_releases if r["approved"])
            total_seeders = sum(r.get("seeders") or 0 for r in formatted_releases)

            return {
                "movie_id": movie_id,
                "total_releases": len(formatted_releases),
                "approved_releases": approved_count,
                "rejected_releases": len(formatted_releases) - approved_count,
                "total_seeders": total_seeders,
                "releases": formatted_releases,
            }
        except Exception as e:
            self.logger.error(f"Failed to get releases for movie {movie_id}: {e}")
            return {"movie_id": movie_id, "total_releases": 0, "releases": [], "error": str(e)}

    async def get_queue(self) -> List[Dict[str, Any]]:
        """Get download queue."""
        try:
            response = await self._make_request("GET", "/api/v3/queue")
            data = response.json()

            return [
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "status": item.get("status"),
                    "progress": item.get("sizeleft", 0) / item.get("size", 1) * 100 if item.get("size") else 0,
                    "download_client": item.get("downloadClient"),
                    "estimated_completion": item.get("estimatedCompletionTime"),
                }
                for item in data.get("records", [])
            ]
        except Exception as e:
            self.logger.error(f"Failed to get queue: {e}")
            return []

    async def get_calendar(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming movies."""
        try:
            from datetime import timedelta

            start = datetime.utcnow()
            end = start + timedelta(days=days)

            response = await self._make_request(
                "GET", "/api/v3/calendar", params={"start": start.isoformat(), "end": end.isoformat()}
            )
            movies = response.json()

            return [
                {
                    "id": movie.get("id"),
                    "title": movie.get("title"),
                    "year": movie.get("year"),
                    "release_date": movie.get("inCinemas") or movie.get("physicalRelease"),
                    "has_file": movie.get("hasFile", False),
                }
                for movie in movies
            ]
        except Exception as e:
            self.logger.error(f"Failed to get calendar: {e}")
            return []

    async def get_statistics(self) -> Dict[str, Any]:
        """Get Radarr statistics."""
        try:
            movies = await self.get_movies(limit=10000)
            queue = await self.get_queue()

            total_movies = len(movies)
            movies_with_files = sum(1 for m in movies if m.get("has_file"))
            monitored = sum(1 for m in movies if m.get("monitored"))
            total_size = sum(m.get("size_on_disk", 0) for m in movies)

            return {
                "total_movies": total_movies,
                "movies_with_files": movies_with_files,
                "monitored_movies": monitored,
                "missing_movies": monitored - movies_with_files,
                "queue_count": len(queue),
                "total_size_gb": round(total_size / (1024**3), 2),
            }
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                "total_movies": 0,
                "movies_with_files": 0,
                "monitored_movies": 0,
                "missing_movies": 0,
                "queue_count": 0,
                "total_size_gb": 0,
            }

    async def get_indexers(self) -> List[Dict[str, Any]]:
        """Get list of configured indexers in Radarr."""
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

    async def check_queue_match(self, title: str = None, movie_id: int = None, tmdb_id: int = None) -> Dict[str, Any]:
        """Check if a movie is in the download queue with fuzzy title matching.

        Args:
            title: Movie title to search for (fuzzy match)
            movie_id: Radarr movie ID (exact match)
            tmdb_id: TMDB ID (exact match)

        Returns detailed queue item info including match score, download progress,
        client, and status.
        """
        try:
            # Get detailed queue with movie info
            response = await self._make_request(
                "GET",
                "/api/v3/queue",
                params={"includeMovie": "true", "pageSize": 500},
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
                movie = item.get("movie", {})
                item_movie_id = movie.get("id")
                item_tmdb_id = movie.get("tmdbId")
                item_title = movie.get("title", "")
                item_year = movie.get("year")

                match_score = 0
                match_type = None

                # Check exact ID matches first
                if movie_id and item_movie_id == movie_id:
                    match_score = 100
                    match_type = "movie_id"
                elif tmdb_id and item_tmdb_id == tmdb_id:
                    match_score = 100
                    match_type = "tmdb_id"
                elif title:
                    # Fuzzy title matching
                    match_score = self._calculate_fuzzy_match_score(title, item_title)
                    match_type = "title"

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
                            "movie": {
                                "id": item_movie_id,
                                "tmdb_id": item_tmdb_id,
                                "title": item_title,
                                "year": item_year,
                                "url": self._get_movie_url(item_movie_id),
                                "tmdb_url": self._get_tmdb_url(item_tmdb_id),
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

            # Sort by match score descending
            matches.sort(key=lambda x: x["match_score"], reverse=True)

            if not matches:
                search_term = title or f"movie_id:{movie_id}" or f"tmdb_id:{tmdb_id}"
                return {
                    "found": False,
                    "message": f"No matching item found in queue for '{search_term}'",
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
