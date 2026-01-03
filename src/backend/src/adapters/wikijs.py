"""WikiJS wiki/documentation server adapter.

WikiJS uses GraphQL API for all operations.
Documentation: https://docs.requarks.io/dev/api
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from .base import (
    AdapterError,
    ConnectionTestResult,
    ServiceCapability,
    TokenAuthAdapter,
)


class WikiJSAdapter(TokenAuthAdapter):
    """Adapter for WikiJS wiki/documentation server.

    Uses Bearer token authentication via API token generated in WikiJS admin.
    All API operations use GraphQL queries to /graphql endpoint.
    """

    @property
    def service_type(self) -> str:
        return "wikijs"

    def _get_page_url(self, locale: str, path: str) -> str:
        """Generate WikiJS web UI URL for a page."""
        if locale and path:
            return f"{self.public_url}/{locale}/{path}"
        return ""

    def _get_page_edit_url(self, page_id: int) -> str:
        """Generate WikiJS web UI URL to edit a page."""
        if page_id:
            return f"{self.public_url}/e/{page_id}"
        return ""

    @property
    def supported_capabilities(self) -> List[ServiceCapability]:
        return [
            ServiceCapability.API_ACCESS,
            ServiceCapability.USER_MANAGEMENT,
        ]

    @property
    def token_config_key(self) -> str:
        return "wikijs_api_token"

    def _format_token_header(self, token: str) -> Dict[str, str]:
        """Format WikiJS Bearer token header."""
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}

    def _get_auth_header(self) -> Dict[str, str]:
        """Get auth header with Bearer token."""
        api_token = self.service_config.api_key or self.get_config_value("api_key")
        if api_token:
            return self._format_token_header(api_token)

        return {"Content-Type": "application/json", "Accept": "application/json"}

    async def _graphql_request(
        self, query: str, variables: Optional[Dict[str, Any]] = None, timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Make GraphQL request to WikiJS API."""
        url = f"{self.base_url.rstrip('/')}/graphql"
        headers = self._get_auth_header()

        payload = {"query": query, "variables": variables or {}}

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

            # Check for GraphQL errors
            if "errors" in result and result["errors"]:
                error_msg = result["errors"][0].get("message", "GraphQL error")
                raise AdapterError(f"WikiJS API error: {error_msg}")

            return result.get("data", {})

    async def test_connection(self) -> ConnectionTestResult:
        """Test connection to WikiJS."""
        start_time = datetime.utcnow()

        try:
            # Query system info to test connection
            query = """
            query {
                system {
                    info {
                        currentVersion
                        latestVersion
                        hostname
                        operatingSystem
                    }
                }
            }
            """
            data = await self._graphql_request(query)
            end_time = datetime.utcnow()
            response_time = int((end_time - start_time).total_seconds() * 1000)

            system_info = data.get("system", {}).get("info", {})

            return ConnectionTestResult(
                success=True,
                message="Successfully connected to WikiJS",
                response_time_ms=response_time,
                details={
                    "status": "connected",
                    "version": system_info.get("currentVersion"),
                    "hostname": system_info.get("hostname"),
                    "os": system_info.get("operatingSystem"),
                },
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return ConnectionTestResult(
                    success=False,
                    message="Authentication failed - check API token",
                    details={"status": "auth_failed", "status_code": 401},
                )
            return ConnectionTestResult(
                success=False,
                message=f"HTTP error: {e.response.status_code}",
                details={"status": "http_error", "status_code": e.response.status_code},
            )
        except AdapterError as e:
            return ConnectionTestResult(success=False, message=str(e), details={"status": "api_error"})
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                details={"status": "connection_failed", "error": str(e)},
            )

    async def get_service_info(self) -> Dict[str, Any]:
        """Get WikiJS service information."""
        try:
            query = """
            query {
                system {
                    info {
                        currentVersion
                        latestVersion
                        hostname
                        operatingSystem
                        platform
                        nodeVersion
                    }
                    flags {
                        key
                        value
                    }
                }
                site {
                    config {
                        title
                        description
                    }
                }
            }
            """
            data = await self._graphql_request(query)
            system_info = data.get("system", {}).get("info", {})
            site_config = data.get("site", {}).get("config", {})

            return {
                "service": "wikijs",
                "version": system_info.get("currentVersion", "unknown"),
                "latest_version": system_info.get("latestVersion"),
                "hostname": system_info.get("hostname"),
                "os": system_info.get("operatingSystem"),
                "platform": system_info.get("platform"),
                "node_version": system_info.get("nodeVersion"),
                "site_title": site_config.get("title"),
                "site_description": site_config.get("description"),
                "status": "online",
            }
        except Exception as e:
            return {"service": "wikijs", "version": "unknown", "status": "error", "error": str(e)}

    async def get_users(self) -> List[Dict[str, Any]]:
        """Get list of users."""
        try:
            query = """
            query {
                users {
                    list {
                        id
                        name
                        email
                        providerKey
                        isSystem
                        isActive
                        createdAt
                        lastLoginAt
                    }
                }
            }
            """
            data = await self._graphql_request(query)
            users = data.get("users", {}).get("list", [])

            return [
                {
                    "id": str(user.get("id")),
                    "username": user.get("name"),
                    "email": user.get("email"),
                    "name": user.get("name"),
                    "provider": user.get("providerKey"),
                    "is_system": user.get("isSystem", False),
                    "is_active": user.get("isActive", True),
                    "created_at": user.get("createdAt"),
                    "last_login": user.get("lastLoginAt"),
                }
                for user in users
                if not user.get("isSystem", False)  # Exclude system users
            ]
        except Exception as e:
            self.logger.error(f"Failed to get users: {e}")
            return []

    async def get_pages(self, limit: int = 50, order_by: str = "UPDATED", locale: str = "en") -> List[Dict[str, Any]]:
        """Get list of wiki pages."""
        try:
            # WikiJS 2.x schema - PageListItem has limited fields
            query = """
            query($limit: Int, $orderBy: PageOrderBy, $locale: String) {
                pages {
                    list(limit: $limit, orderBy: $orderBy, locale: $locale) {
                        id
                        path
                        title
                        description
                        createdAt
                        updatedAt
                        isPublished
                        locale
                        tags
                    }
                }
            }
            """
            variables = {"limit": limit, "orderBy": order_by, "locale": locale}
            data = await self._graphql_request(query, variables)
            pages = data.get("pages", {}).get("list", [])

            return [
                {
                    "id": page.get("id"),
                    "path": page.get("path"),
                    "title": page.get("title"),
                    "description": page.get("description"),
                    "locale": page.get("locale"),
                    "is_published": page.get("isPublished", True),
                    "tags": page.get("tags", []),  # tags is already a string array
                    "created_at": page.get("createdAt"),
                    "updated_at": page.get("updatedAt"),
                    "url": self._get_page_url(page.get("locale"), page.get("path")),
                }
                for page in pages
            ]
        except Exception as e:
            self.logger.error(f"Failed to get pages: {e}")
            return []

    async def get_page(self, page_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific page with full content."""
        try:
            query = """
            query($id: Int!) {
                pages {
                    single(id: $id) {
                        id
                        path
                        title
                        description
                        content
                        render
                        createdAt
                        updatedAt
                        authorName
                        isPublished
                        isPrivate
                        locale
                        tags {
                            tag
                        }
                        toc
                    }
                }
            }
            """
            data = await self._graphql_request(query, {"id": page_id})
            page = data.get("pages", {}).get("single")

            if not page:
                return None

            return {
                "id": page.get("id"),
                "path": page.get("path"),
                "title": page.get("title"),
                "description": page.get("description"),
                "content": page.get("content"),
                "render": page.get("render"),
                "author": page.get("authorName"),
                "locale": page.get("locale"),
                "is_published": page.get("isPublished", True),
                "is_private": page.get("isPrivate", False),
                "tags": [t.get("tag") for t in page.get("tags", [])],
                "toc": page.get("toc"),
                "created_at": page.get("createdAt"),
                "updated_at": page.get("updatedAt"),
            }
        except Exception as e:
            self.logger.error(f"Failed to get page {page_id}: {e}")
            return None

    async def search(self, query: str, locale: str = "en") -> List[Dict[str, Any]]:
        """Search wiki content."""
        try:
            gql_query = """
            query($query: String!, $locale: String) {
                pages {
                    search(query: $query, locale: $locale) {
                        results {
                            id
                            path
                            title
                            description
                            locale
                        }
                        suggestions
                        totalHits
                    }
                }
            }
            """
            data = await self._graphql_request(gql_query, {"query": query, "locale": locale})
            search_results = data.get("pages", {}).get("search", {})

            return {
                "total": search_results.get("totalHits", 0),
                "suggestions": search_results.get("suggestions", []),
                "results": [
                    {
                        "id": r.get("id"),
                        "path": r.get("path"),
                        "title": r.get("title"),
                        "description": r.get("description"),
                        "locale": r.get("locale"),
                    }
                    for r in search_results.get("results", [])
                ],
            }
        except Exception as e:
            self.logger.error(f"Failed to search: {e}")
            return {"total": 0, "suggestions": [], "results": []}

    async def get_page_tree(self, parent_id: int = 0, locale: str = "en") -> List[Dict[str, Any]]:
        """Get page tree structure."""
        try:
            # WikiJS 2.x: parent is optional Int, not String
            # If parent_id is 0, don't pass it to get root tree
            if parent_id > 0:
                query = """
                query($parent: Int, $locale: String!) {
                    pages {
                        tree(parent: $parent, mode: ALL, locale: $locale, includeAncestors: false) {
                            id
                            path
                            title
                            isPrivate
                            isFolder
                            depth
                            pageId
                        }
                    }
                }
                """
                variables = {"parent": parent_id, "locale": locale}
            else:
                query = """
                query($locale: String!) {
                    pages {
                        tree(mode: ALL, locale: $locale, includeAncestors: false) {
                            id
                            path
                            title
                            isPrivate
                            isFolder
                            depth
                            pageId
                        }
                    }
                }
                """
                variables = {"locale": locale}

            data = await self._graphql_request(query, variables)
            tree = data.get("pages", {}).get("tree", [])

            return [
                {
                    "id": item.get("id"),
                    "path": item.get("path"),
                    "title": item.get("title"),
                    "is_private": item.get("isPrivate", False),
                    "is_folder": item.get("isFolder", False),
                    "depth": item.get("depth", 0),
                    "page_id": item.get("pageId"),
                }
                for item in tree
            ]
        except Exception as e:
            self.logger.error(f"Failed to get page tree: {e}")
            return []

    async def get_tags(self) -> List[Dict[str, Any]]:
        """Get all tags."""
        try:
            query = """
            query {
                pages {
                    tags {
                        id
                        tag
                        title
                        createdAt
                        updatedAt
                    }
                }
            }
            """
            data = await self._graphql_request(query)
            tags = data.get("pages", {}).get("tags", [])

            return [
                {
                    "id": tag.get("id"),
                    "tag": tag.get("tag"),
                    "title": tag.get("title"),
                    "created_at": tag.get("createdAt"),
                    "updated_at": tag.get("updatedAt"),
                }
                for tag in tags
            ]
        except Exception as e:
            self.logger.error(f"Failed to get tags: {e}")
            return []

    async def get_statistics(self) -> Dict[str, Any]:
        """Get WikiJS statistics."""
        try:
            # Get page count without locale filter to count all pages
            query = """
            query {
                pages {
                    list(limit: 10000, orderBy: UPDATED) {
                        id
                        isPublished
                        locale
                    }
                }
            }
            """
            data = await self._graphql_request(query)
            pages = data.get("pages", {}).get("list", [])

            users = await self.get_users()
            tags = await self.get_tags()

            # Count pages by locale
            locales = {}
            for p in pages:
                loc = p.get("locale", "unknown")
                locales[loc] = locales.get(loc, 0) + 1

            return {
                "total_pages": len(pages),
                "total_users": len(users),
                "total_tags": len(tags),
                "active_users": len([u for u in users if u.get("is_active")]),
                "published_pages": len([p for p in pages if p.get("isPublished")]),
                "pages_by_locale": locales,
            }
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                "total_pages": 0,
                "total_users": 0,
                "total_tags": 0,
                "active_users": 0,
                "published_pages": 0,
                "pages_by_locale": {},
            }

    async def create_page(
        self,
        path: str,
        title: str,
        content: str,
        description: str = "",
        locale: str = "en",
        is_published: bool = True,
        is_private: bool = False,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new wiki page."""
        try:
            mutation = """
            mutation(
                $content: String!
                $description: String!
                $editor: String!
                $isPrivate: Boolean!
                $isPublished: Boolean!
                $locale: String!
                $path: String!
                $tags: [String]!
                $title: String!
            ) {
                pages {
                    create(
                        content: $content
                        description: $description
                        editor: "markdown"
                        isPrivate: $isPrivate
                        isPublished: $isPublished
                        locale: $locale
                        path: $path
                        tags: $tags
                        title: $title
                    ) {
                        responseResult {
                            succeeded
                            errorCode
                            message
                        }
                        page {
                            id
                            path
                            title
                        }
                    }
                }
            }
            """
            variables = {
                "content": content,
                "description": description,
                "editor": "markdown",
                "isPrivate": is_private,
                "isPublished": is_published,
                "locale": locale,
                "path": path,
                "tags": tags or [],
                "title": title,
            }
            data = await self._graphql_request(mutation, variables)
            result = data.get("pages", {}).get("create", {})
            response = result.get("responseResult", {})

            if response.get("succeeded"):
                page = result.get("page", {})
                return {
                    "success": True,
                    "page": {"id": page.get("id"), "path": page.get("path"), "title": page.get("title")},
                }
            else:
                return {
                    "success": False,
                    "error": response.get("message", "Failed to create page"),
                    "error_code": response.get("errorCode"),
                }
        except Exception as e:
            self.logger.error(f"Failed to create page: {e}")
            return {"success": False, "error": str(e)}
