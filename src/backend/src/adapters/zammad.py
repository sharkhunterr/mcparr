"""Zammad helpdesk system adapter."""

from typing import Dict, Any, List, Optional
import httpx
from datetime import datetime
from enum import Enum

from .base import (
    TokenAuthAdapter,
    ServiceCapability,
    ConnectionTestResult,
    AdapterError,
    AuthenticationError
)


class TicketState(Enum):
    """Zammad ticket states."""
    NEW = "new"
    OPEN = "open"
    PENDING_REMINDER = "pending reminder"
    PENDING_CLOSE = "pending close"
    CLOSED = "closed"


class TicketPriority(Enum):
    """Zammad ticket priorities."""
    LOW = "1 low"
    NORMAL = "2 normal"
    HIGH = "3 high"


class ZammadAdapter(TokenAuthAdapter):
    """Adapter for Zammad helpdesk system."""

    @property
    def service_type(self) -> str:
        return "zammad"

    @property
    def supported_capabilities(self) -> List[ServiceCapability]:
        return [
            ServiceCapability.TICKET_SYSTEM,
            ServiceCapability.USER_MANAGEMENT,
            ServiceCapability.API_ACCESS
        ]

    @property
    def token_config_key(self) -> str:
        return "zammad_token"

    def _format_token_header(self, token: str) -> Dict[str, str]:
        """Format Zammad token header.

        Zammad supports multiple auth formats:
        - API Token: "Token token={api_token}" (most common for integrations)
        - Bearer: "Bearer {jwt_token}" (for OAuth/JWT)

        We detect format based on token structure.
        """
        # JWT tokens typically have 3 parts separated by dots
        if token.count('.') == 2:
            # Looks like a JWT token
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        else:
            # Standard Zammad API token
            return {
                "Authorization": f"Token token={token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

    async def test_connection(self) -> ConnectionTestResult:
        """Test connection to Zammad."""
        start_time = datetime.utcnow()

        try:
            # Test basic connectivity and auth
            response = await self._make_request("GET", "/api/v1/users/me")

            end_time = datetime.utcnow()
            response_time = int((end_time - start_time).total_seconds() * 1000)

            data = response.json()

            if "id" in data and "email" in data:
                return ConnectionTestResult(
                    success=True,
                    message="Successfully connected to Zammad",
                    response_time_ms=response_time,
                    details={
                        "status": "connected",
                        "user_id": data.get("id"),
                        "user_email": data.get("email")
                    }
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message="Connected but response doesn't appear to be from Zammad",
                    response_time_ms=response_time,
                    details={"status": "invalid_response"}
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return ConnectionTestResult(
                    success=False,
                    message="Authentication failed - check token",
                    details={"status": "auth_failed", "status_code": 401}
                )
            elif e.response.status_code == 403:
                return ConnectionTestResult(
                    success=False,
                    message="Access denied - insufficient permissions",
                    details={"status": "access_denied", "status_code": 403}
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message=f"HTTP error: {e.response.status_code}",
                    details={"status": "http_error", "status_code": e.response.status_code}
                )
        except httpx.RequestError as e:
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                details={"status": "connection_failed", "error": str(e)}
            )
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Unexpected error: {str(e)}",
                details={"status": "unexpected_error", "error": str(e)}
            )

    async def get_service_info(self) -> Dict[str, Any]:
        """Get Zammad service information."""
        try:
            # Get current user info
            user_response = await self._make_request("GET", "/api/v1/users/me")
            user_data = user_response.json()

            # Get version info if available
            version_data = await self._safe_request("GET", "/api/v1/version")

            return {
                "service": "zammad",
                "version": version_data.get("version") if version_data else "unknown",
                "current_user": {
                    "id": user_data.get("id"),
                    "email": user_data.get("email"),
                    "firstname": user_data.get("firstname"),
                    "lastname": user_data.get("lastname"),
                    "roles": user_data.get("roles", [])
                },
                "api_version": "v1"
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid Zammad token")
            raise AdapterError(f"HTTP error: {e.response.status_code}")
        except Exception as e:
            raise AdapterError(f"Failed to get service info: {str(e)}")

    def _get_field_value(self, ticket: dict, field: str) -> Optional[str]:
        """Extract field value from ticket - handles both expanded (string) and non-expanded (object) format.

        With expand=true: {"state": "new", "priority": "2 normal", "group": "Users"}
        Without expand: {"state": {"id": 1, "name": "new"}, "priority": {"id": 2, "name": "2 normal"}}
        """
        value = ticket.get(field)
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return value.get("name")
        return None

    async def get_tickets(
        self,
        page: int = 1,
        per_page: int = 25,
        state: Optional[TicketState] = None
    ) -> Dict[str, Any]:
        """Get tickets from Zammad."""
        try:
            params = {"page": str(page), "per_page": str(per_page), "expand": "true"}

            response = await self._make_request("GET", "/api/v1/tickets", params=params)
            data = response.json()

            # Filter by state if specified
            tickets = data if isinstance(data, list) else []
            if state:
                tickets = [t for t in tickets if self._get_field_value(t, "state") == state.value]

            # Process tickets to add user-friendly information
            processed_tickets = []
            for ticket in tickets:
                processed_ticket = {
                    "id": ticket.get("id"),
                    "number": ticket.get("number"),
                    "title": ticket.get("title"),
                    "state": self._get_field_value(ticket, "state"),
                    "priority": self._get_field_value(ticket, "priority"),
                    "group": self._get_field_value(ticket, "group"),
                    "customer_id": ticket.get("customer_id"),
                    "owner_id": ticket.get("owner_id"),
                    "created_at": ticket.get("created_at"),
                    "updated_at": ticket.get("updated_at"),
                    "close_at": ticket.get("close_at"),
                    "article_count": ticket.get("article_count", 0)
                }
                processed_tickets.append(processed_ticket)

            return {
                "tickets": processed_tickets,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": len(processed_tickets)
                }
            }

        except Exception as e:
            self.logger.error(f"Failed to get tickets: {e}")
            return {"tickets": [], "pagination": {"page": page, "per_page": per_page, "total": 0}}

    async def get_ticket_by_id(self, ticket_id: int, expand: bool = True) -> Optional[Dict[str, Any]]:
        """Get a specific ticket by ID."""
        try:
            params = {"expand": "true"} if expand else {}
            response = await self._make_request("GET", f"/api/v1/tickets/{ticket_id}", params=params)
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            self.logger.warning(f"Failed to get ticket {ticket_id}: {e}")
            return None

    async def create_ticket(self, ticket_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new ticket."""
        try:
            response = await self._make_request("POST", "/api/v1/tickets", json=ticket_data)
            return response.json()

        except httpx.HTTPStatusError as e:
            error_body = ""
            try:
                error_body = e.response.text
            except Exception:
                pass
            self.logger.error(f"Failed to create ticket: HTTP {e.response.status_code} - {error_body}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to create ticket: {e}")
            return None

    async def update_ticket(self, ticket_id: int, ticket_data: Dict[str, Any]) -> bool:
        """Update a ticket."""
        try:
            response = await self._make_request("PUT", f"/api/v1/tickets/{ticket_id}", json=ticket_data)
            return response.status_code == 200

        except Exception as e:
            self.logger.error(f"Failed to update ticket {ticket_id}: {e}")
            return False

    async def get_users(self, page: int = 1, per_page: int = 25) -> List[Dict[str, Any]]:
        """Get Zammad users."""
        try:
            params = {"page": str(page), "per_page": str(per_page)}
            response = await self._make_request("GET", "/api/v1/users", params=params)
            data = response.json()

            users = []
            for user in data if isinstance(data, list) else []:
                users.append({
                    "id": user.get("id"),
                    "email": user.get("email"),
                    "firstname": user.get("firstname"),
                    "lastname": user.get("lastname"),
                    "login": user.get("login"),
                    "phone": user.get("phone"),
                    "active": user.get("active"),
                    "verified": user.get("verified"),
                    "roles": user.get("roles", []),
                    "groups": user.get("groups", []),
                    "created_at": user.get("created_at"),
                    "updated_at": user.get("updated_at")
                })

            return users

        except Exception as e:
            self.logger.warning(f"Failed to get users: {e}")
            return []

    async def get_groups(self) -> List[Dict[str, Any]]:
        """Get Zammad groups."""
        try:
            response = await self._make_request("GET", "/api/v1/groups")
            data = response.json()

            groups = []
            for group in data if isinstance(data, list) else []:
                groups.append({
                    "id": group.get("id"),
                    "name": group.get("name"),
                    "assignment_timeout": group.get("assignment_timeout"),
                    "follow_up_possible": group.get("follow_up_possible"),
                    "follow_up_assignment": group.get("follow_up_assignment"),
                    "active": group.get("active"),
                    "note": group.get("note"),
                    "created_at": group.get("created_at"),
                    "updated_at": group.get("updated_at")
                })

            return groups

        except Exception as e:
            self.logger.warning(f"Failed to get groups: {e}")
            return []

    async def get_ticket_articles(self, ticket_id: int) -> List[Dict[str, Any]]:
        """Get articles (comments) for a ticket."""
        try:
            response = await self._make_request("GET", f"/api/v1/ticket_articles/by_ticket/{ticket_id}")
            data = response.json()

            articles = []
            for article in data if isinstance(data, list) else []:
                # Handle type field - can be string or object
                article_type = article.get("type")
                if isinstance(article_type, dict):
                    article_type = article_type.get("name")

                # Handle sender field - can be string or object
                sender = article.get("sender")
                if isinstance(sender, dict):
                    sender = sender.get("name")

                articles.append({
                    "id": article.get("id"),
                    "ticket_id": article.get("ticket_id"),
                    "type": article_type,
                    "sender": sender,
                    "from": article.get("from"),
                    "to": article.get("to"),
                    "subject": article.get("subject"),
                    "body": article.get("body"),
                    "content_type": article.get("content_type"),
                    "internal": article.get("internal", False),
                    "created_by_id": article.get("created_by_id"),
                    "created_by": article.get("created_by"),
                    "created_at": article.get("created_at"),
                    "updated_at": article.get("updated_at")
                })

            return articles

        except Exception as e:
            self.logger.warning(f"Failed to get articles for ticket {ticket_id}: {e}")
            return []

    async def create_article(self, ticket_id: int, body: str, internal: bool = False) -> Optional[Dict[str, Any]]:
        """Create an article (comment) for a ticket."""
        try:
            article_data = {
                "ticket_id": ticket_id,
                "body": body,
                "type": "note",
                "internal": internal,
            }
            response = await self._make_request("POST", "/api/v1/ticket_articles", json=article_data)
            return response.json()

        except Exception as e:
            self.logger.error(f"Failed to create article for ticket {ticket_id}: {e}")
            return None

    async def search_tickets(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for tickets."""
        try:
            params = {"query": f"title:*{query}* OR body:*{query}*", "limit": str(limit)}
            response = await self._make_request("GET", "/api/v1/tickets/search", params=params)
            data = response.json()

            return data if isinstance(data, list) else []

        except Exception as e:
            self.logger.warning(f"Failed to search tickets: {e}")
            return []

    async def get_ticket_by_number(self, ticket_number: str) -> Optional[Dict[str, Any]]:
        """Get a ticket by its number (e.g., '20001')."""
        try:
            params = {"query": f"number:{ticket_number}", "expand": "true", "limit": "1"}
            response = await self._make_request("GET", "/api/v1/tickets/search", params=params)
            data = response.json()

            if isinstance(data, list) and len(data) > 0:
                return data[0]
            return None

        except Exception as e:
            self.logger.warning(f"Failed to get ticket by number {ticket_number}: {e}")
            return None

    async def get_statistics(self) -> Dict[str, Any]:
        """Get ticket statistics."""
        try:
            # Get recent tickets
            tickets_data = await self.get_tickets(per_page=100)
            tickets = tickets_data.get("tickets", [])

            # Calculate statistics
            total_tickets = len(tickets)
            new_tickets = sum(1 for t in tickets if t.get("state") == "new")
            open_tickets = sum(1 for t in tickets if t.get("state") == "open")
            closed_tickets = sum(1 for t in tickets if t.get("state") == "closed")
            pending_tickets = total_tickets - new_tickets - open_tickets - closed_tickets

            # Get users count
            users = await self.get_users(per_page=100)

            # Get groups count
            groups = await self.get_groups()

            return {
                "total_tickets": total_tickets,
                "new_tickets": new_tickets,
                "open_tickets": open_tickets,
                "pending_tickets": pending_tickets,
                "closed_tickets": closed_tickets,
                "total_users": len(users),
                "total_groups": len(groups),
                "recent_tickets": tickets[:10]
            }

        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                "total_tickets": 0,
                "new_tickets": 0,
                "open_tickets": 0,
                "pending_tickets": 0,
                "closed_tickets": 0,
                "total_users": 0,
                "total_groups": 0,
                "recent_tickets": []
            }

    def validate_config(self) -> List[str]:
        """Validate Zammad-specific configuration."""
        errors = super().validate_config()

        # Check for required token
        if not self.get_config_value(self.token_config_key):
            errors.append("Zammad token is required")

        return errors