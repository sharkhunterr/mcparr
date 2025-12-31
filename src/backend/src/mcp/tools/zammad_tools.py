"""MCP tools for Zammad integration."""

from typing import List

from .base import BaseTool, ToolDefinition, ToolParameter


class ZammadTools(BaseTool):
    """MCP tools for interacting with Zammad ticketing system."""

    @property
    def definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="zammad_get_tickets",
                description="Get list of support tickets with optional filtering",
                parameters=[
                    ToolParameter(
                        name="status",
                        description="Filter by ticket status",
                        type="string",
                        required=False,
                        enum=["open", "closed", "pending", "all"],
                        default="open",
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum number of tickets to return",
                        type="number",
                        required=False,
                        default=20,
                    ),
                ],
                category="support",
                is_mutation=False,
                requires_service="zammad",
            ),
            ToolDefinition(
                name="zammad_get_ticket_details",
                description="Get detailed information about a specific ticket including all articles/messages",
                parameters=[
                    ToolParameter(
                        name="ticket_id",
                        description="ID or number of the ticket (e.g., 1 or 20001)",
                        type="number",
                        required=True,
                    ),
                ],
                category="support",
                is_mutation=False,
                requires_service="zammad",
            ),
            ToolDefinition(
                name="zammad_search_tickets",
                description="Search for tickets by keyword in subject or content",
                parameters=[
                    ToolParameter(
                        name="query",
                        description="Search query",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="limit",
                        description="Maximum number of results",
                        type="number",
                        required=False,
                        default=10,
                    ),
                ],
                category="support",
                is_mutation=False,
                requires_service="zammad",
            ),
            ToolDefinition(
                name="zammad_create_ticket",
                description="Create a new support ticket",
                parameters=[
                    ToolParameter(
                        name="title",
                        description="Ticket subject/title",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="body",
                        description="Ticket description/content",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="group",
                        description="Support group to assign the ticket to",
                        type="string",
                        required=False,
                        default="Users",
                    ),
                    ToolParameter(
                        name="priority",
                        description="Ticket priority",
                        type="string",
                        required=False,
                        enum=["low", "normal", "high"],
                        default="normal",
                    ),
                ],
                category="support",
                is_mutation=True,
                requires_service="zammad",
            ),
            ToolDefinition(
                name="zammad_add_comment",
                description="Add a comment/reply to an existing ticket",
                parameters=[
                    ToolParameter(
                        name="ticket_id",
                        description="ID of the ticket",
                        type="number",
                        required=True,
                    ),
                    ToolParameter(
                        name="comment",
                        description="Comment content",
                        type="string",
                        required=True,
                    ),
                    ToolParameter(
                        name="internal",
                        description="Whether the comment is internal (not visible to customer)",
                        type="boolean",
                        required=False,
                        default=False,
                    ),
                ],
                category="support",
                is_mutation=True,
                requires_service="zammad",
            ),
            ToolDefinition(
                name="zammad_update_ticket_status",
                description="Update the status of a ticket",
                parameters=[
                    ToolParameter(
                        name="ticket_id",
                        description="ID of the ticket",
                        type="number",
                        required=True,
                    ),
                    ToolParameter(
                        name="status",
                        description="New status for the ticket",
                        type="string",
                        required=True,
                        enum=["open", "closed", "pending"],
                    ),
                ],
                category="support",
                is_mutation=True,
                requires_service="zammad",
            ),
            ToolDefinition(
                name="zammad_get_ticket_stats",
                description="Get statistics about tickets (open count, avg response time, etc.)",
                parameters=[],
                category="support",
                is_mutation=False,
                requires_service="zammad",
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute a Zammad tool."""
        if not self.service_config:
            return {"success": False, "error": "Zammad service not configured"}

        try:
            from src.adapters.zammad import ZammadAdapter

            # Create a mock ServiceConfig object for the adapter
            class ServiceConfigProxy:
                def __init__(self, config: dict):
                    self._config = config
                    self.api_key = config.get("api_key")
                    # Support both 'base_url' and 'url' keys for compatibility
                    self.base_url = config.get("base_url") or config.get("url", "")
                    self.port = config.get("port")
                    self.config = config.get("config") or config.get("extra_config", {})

                def get_config_value(self, key: str, default=None):
                    return self.config.get(key, default)

            service_proxy = ServiceConfigProxy(self.service_config)
            adapter = ZammadAdapter(service_proxy)

            if tool_name == "zammad_get_tickets":
                return await self._get_tickets(adapter, arguments)
            elif tool_name == "zammad_get_ticket_details":
                return await self._get_ticket_details(adapter, arguments)
            elif tool_name == "zammad_search_tickets":
                return await self._search_tickets(adapter, arguments)
            elif tool_name == "zammad_create_ticket":
                return await self._create_ticket(adapter, arguments)
            elif tool_name == "zammad_add_comment":
                return await self._add_comment(adapter, arguments)
            elif tool_name == "zammad_update_ticket_status":
                return await self._update_ticket_status(adapter, arguments)
            elif tool_name == "zammad_get_ticket_stats":
                return await self._get_ticket_stats(adapter)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    async def _get_tickets(self, adapter, arguments: dict) -> dict:
        """Get list of tickets."""
        limit = arguments.get("limit", 20)

        # Get tickets from adapter (uses per_page parameter)
        result = await adapter.get_tickets(per_page=limit)
        tickets = result.get("tickets", [])

        return {"success": True, "result": {"count": len(tickets), "tickets": tickets}}

    async def _get_ticket_details(self, adapter, arguments: dict) -> dict:
        """Get ticket details with articles."""
        ticket_id_or_number = arguments.get("ticket_id")

        # First try to get by ID
        ticket = await adapter.get_ticket_by_id(ticket_id_or_number)

        # If not found by ID, try to find by ticket number
        if ticket is None:
            ticket = await adapter.get_ticket_by_number(str(ticket_id_or_number))

        if ticket is None:
            return {"success": False, "error": f"Ticket {ticket_id_or_number} not found (searched by ID and number)"}

        # Use the actual ticket ID for fetching articles
        actual_ticket_id = ticket.get("id")
        articles = await adapter.get_ticket_articles(actual_ticket_id)

        return {
            "success": True,
            "result": {
                "ticket": {
                    "id": ticket.get("id"),
                    "number": ticket.get("number"),
                    "title": ticket.get("title"),
                    "state": ticket.get("state"),
                    "priority": ticket.get("priority"),
                    "created_at": ticket.get("created_at"),
                    "updated_at": ticket.get("updated_at"),
                    "customer": ticket.get("customer"),
                    "owner": ticket.get("owner"),
                    "group": ticket.get("group"),
                },
                "articles": [
                    {
                        "id": article.get("id"),
                        "type": article.get("type"),
                        "sender": article.get("sender"),
                        "subject": article.get("subject"),
                        "body": article.get("body"),
                        "internal": article.get("internal", False),
                        "created_at": article.get("created_at"),
                        "from": article.get("from"),
                    }
                    for article in articles
                ],
            },
        }

    async def _search_tickets(self, adapter, arguments: dict) -> dict:
        """Search for tickets."""
        query = arguments.get("query")
        limit = arguments.get("limit", 10)

        tickets = await adapter.search_tickets(query, limit=limit)

        return {
            "success": True,
            "result": {
                "query": query,
                "count": len(tickets),
                "tickets": [
                    {
                        "id": ticket.get("id"),
                        "number": ticket.get("number"),
                        "title": ticket.get("title"),
                        "state": ticket.get("state"),
                        "created_at": ticket.get("created_at"),
                    }
                    for ticket in tickets
                ],
            },
        }

    async def _create_ticket(self, adapter, arguments: dict) -> dict:
        """Create a new ticket."""
        title = arguments.get("title")
        body = arguments.get("body")
        group = arguments.get("group", "Users")
        priority = arguments.get("priority", "normal")

        # Map priority to Zammad priority ID (1=low, 2=normal, 3=high)
        priority_map = {"low": 1, "normal": 2, "high": 3}
        priority_id = priority_map.get(priority, 2)

        # Get current user to use as customer (required by Zammad API)
        # First try to get current user info
        try:
            user_info = await adapter.get_service_info()
            customer_id = user_info.get("current_user", {}).get("id")
        except Exception:
            customer_id = None

        # Build ticket data structure for Zammad API
        ticket_data = {
            "title": title,
            "group": group,
            "priority_id": priority_id,
            "article": {
                "subject": title,
                "body": body,
                "type": "note",
                "internal": False,
            },
        }

        # Add customer_id if available (required for ticket creation)
        if customer_id:
            ticket_data["customer_id"] = customer_id

        ticket = await adapter.create_ticket(ticket_data)

        if not ticket:
            return {"success": False, "error": "Failed to create ticket - check Zammad API logs for details"}

        return {
            "success": True,
            "result": {
                "message": f"Ticket #{ticket.get('number')} created successfully",
                "ticket_id": ticket.get("id"),
                "ticket_number": ticket.get("number"),
            },
        }

    async def _add_comment(self, adapter, arguments: dict) -> dict:
        """Add a comment to a ticket."""
        ticket_id = arguments.get("ticket_id")
        comment = arguments.get("comment")
        internal = arguments.get("internal", False)

        article = await adapter.create_article(
            ticket_id=ticket_id,
            body=comment,
            internal=internal,
        )

        if not article:
            return {"success": False, "error": f"Failed to add comment to ticket #{ticket_id}"}

        return {
            "success": True,
            "result": {
                "message": f"Comment added to ticket #{ticket_id}",
                "article_id": article.get("id"),
                "internal": internal,
            },
        }

    async def _update_ticket_status(self, adapter, arguments: dict) -> dict:
        """Update ticket status."""
        ticket_id = arguments.get("ticket_id")
        status = arguments.get("status")

        # Map status to Zammad state_id (1=new, 2=open, 3=pending reminder, 4=closed)
        status_map = {
            "new": 1,
            "open": 2,
            "pending": 3,
            "closed": 4,
        }
        state_id = status_map.get(status.lower(), 2)

        success = await adapter.update_ticket(ticket_id, {"state_id": state_id})

        if not success:
            return {"success": False, "error": f"Failed to update ticket #{ticket_id} status"}

        return {
            "success": True,
            "result": {
                "message": f"Ticket #{ticket_id} status updated to {status}",
                "ticket_id": ticket_id,
                "new_status": status,
            },
        }

    async def _get_ticket_stats(self, adapter) -> dict:
        """Get ticket statistics."""
        stats = await adapter.get_statistics()

        return {
            "success": True,
            "result": {
                "new_tickets": stats.get("new_tickets", 0),
                "open_tickets": stats.get("open_tickets", 0),
                "pending_tickets": stats.get("pending_tickets", 0),
                "closed_tickets": stats.get("closed_tickets", 0),
                "total_tickets": stats.get("total_tickets", 0),
                "total_users": stats.get("total_users", 0),
                "total_groups": stats.get("total_groups", 0),
            },
        }
