"""MCP Server implementation for MCParr AI Gateway.

This server implements the Model Context Protocol (MCP) to allow AI models
to interact with homelab services through defined tools.
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Any, List, Optional
from uuid import uuid4

from .tools.base import ToolRegistry


class MCPServer:
    """MCP Server that exposes homelab tools to AI models."""

    PROTOCOL_VERSION = "2024-11-05"
    SERVER_NAME = "mcparr-ai-gateway"
    SERVER_VERSION = "1.0.0"

    def __init__(self, db_session_factory=None):
        """Initialize MCP server.

        Args:
            db_session_factory: Async session factory for database operations
        """
        self.registry = ToolRegistry()
        self.db_session_factory = db_session_factory
        self._initialized = False
        self._session_id = str(uuid4())

    async def initialize(self, service_configs: Optional[List[dict]] = None) -> None:
        """Initialize the server and register tools.

        Args:
            service_configs: List of enabled service configurations from database
        """
        from .tools.deluge_tools import DelugeTools
        from .tools.jackett_tools import JackettTools
        from .tools.komga_tools import KomgaTools
        from .tools.openwebui_tools import OpenWebUITools
        from .tools.overseerr_tools import OverseerrTools
        from .tools.plex_tools import PlexTools
        from .tools.prowlarr_tools import ProwlarrTools
        from .tools.radarr_tools import RadarrTools
        from .tools.romm_tools import RommTools
        from .tools.sonarr_tools import SonarrTools
        from .tools.system_tools import SystemTools
        from .tools.tautulli_tools import TautulliTools
        from .tools.zammad_tools import ZammadTools

        # Build service config lookup from enabled services only
        configs_by_type = {}
        if service_configs:
            for config in service_configs:
                service_type = config.get("service_type", "").lower()
                if service_type:
                    configs_by_type[service_type] = config

        # System tools are always available (no service required)
        self.registry.register(SystemTools)

        # Only register tools for enabled services
        if "plex" in configs_by_type:
            self.registry.register(PlexTools, configs_by_type.get("plex"))
        if "overseerr" in configs_by_type:
            self.registry.register(OverseerrTools, configs_by_type.get("overseerr"))
        if "zammad" in configs_by_type:
            self.registry.register(ZammadTools, configs_by_type.get("zammad"))
        if "tautulli" in configs_by_type:
            self.registry.register(TautulliTools, configs_by_type.get("tautulli"))
        if "openwebui" in configs_by_type:
            self.registry.register(OpenWebUITools, configs_by_type.get("openwebui"))
        if "radarr" in configs_by_type:
            self.registry.register(RadarrTools, configs_by_type.get("radarr"))
        if "sonarr" in configs_by_type:
            self.registry.register(SonarrTools, configs_by_type.get("sonarr"))
        if "prowlarr" in configs_by_type:
            self.registry.register(ProwlarrTools, configs_by_type.get("prowlarr"))
        if "jackett" in configs_by_type:
            self.registry.register(JackettTools, configs_by_type.get("jackett"))
        if "deluge" in configs_by_type:
            self.registry.register(DelugeTools, configs_by_type.get("deluge"))
        if "komga" in configs_by_type:
            self.registry.register(KomgaTools, configs_by_type.get("komga"))
        if "romm" in configs_by_type:
            self.registry.register(RommTools, configs_by_type.get("romm"))

        self._initialized = True

    async def handle_message(self, message: dict) -> dict:
        """Handle an incoming MCP message.

        Args:
            message: Parsed JSON-RPC message

        Returns:
            JSON-RPC response
        """
        method = message.get("method")
        params = message.get("params", {})
        msg_id = message.get("id")

        try:
            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "tools/list":
                result = await self._handle_tools_list(params)
            elif method == "tools/call":
                result = await self._handle_tools_call(params)
            elif method == "ping":
                result = {"pong": True}
            else:
                return self._error_response(msg_id, -32601, f"Method not found: {method}")

            return self._success_response(msg_id, result)

        except Exception as e:
            return self._error_response(msg_id, -32603, str(e))

    async def _handle_initialize(self, params: dict) -> dict:
        """Handle initialize request."""
        params.get("clientInfo", {})

        return {
            "protocolVersion": self.PROTOCOL_VERSION,
            "capabilities": {
                "tools": {"listChanged": False},  # We don't support dynamic tool changes
            },
            "serverInfo": {
                "name": self.SERVER_NAME,
                "version": self.SERVER_VERSION,
            },
        }

    async def _handle_tools_list(self, params: dict) -> dict:
        """Handle tools/list request."""
        tools = self.registry.list_tools_mcp_schema()
        return {"tools": tools}

    async def _handle_tools_call(self, params: dict) -> dict:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            raise ValueError("Tool name is required")

        # Get tool definition for metadata
        definition = self.registry.get_definition(tool_name)

        # Log the request if we have a database session
        request_id = None
        if self.db_session_factory:
            request_id = await self._log_request_start(
                tool_name=tool_name,
                arguments=arguments,
                category=definition.category if definition else "unknown",
                is_mutation=definition.is_mutation if definition else False,
            )

        # Execute the tool
        start_time = datetime.utcnow()
        result = await self.registry.execute(tool_name, arguments)
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Enrich result with tool chain suggestions
        enriched_result = result.copy()
        if self.db_session_factory and result.get("success", False):
            try:
                from src.services.tool_chain_service import enrich_tool_result_with_chains
                async with self.db_session_factory() as session:
                    enriched_result = await enrich_tool_result_with_chains(
                        session, tool_name, result, arguments,
                        session_id=self._session_id
                    )
            except Exception as e:
                print(f"Failed to enrich result with chains: {e}", file=sys.stderr)

        # Log the result (with enriched data)
        if self.db_session_factory and request_id:
            await self._log_request_complete(
                request_id=request_id,
                result=enriched_result,
                duration_ms=duration_ms,
            )

        # Format response according to MCP spec
        if result.get("success", False):
            # Include chain info in the response
            response_data = enriched_result.get("result", {})
            if enriched_result.get("chain_context"):
                response_data["chain_context"] = enriched_result["chain_context"]
            if enriched_result.get("next_tools_to_call"):
                response_data["next_tools_to_call"] = enriched_result["next_tools_to_call"]
            if enriched_result.get("message_to_display"):
                response_data["message_to_display"] = enriched_result["message_to_display"]
            if enriched_result.get("ai_instruction"):
                response_data["ai_instruction"] = enriched_result["ai_instruction"]

            return {
                "content": [{"type": "text", "text": json.dumps(response_data, indent=2, default=str)}],
                "isError": False,
            }
        else:
            return {
                "content": [{"type": "text", "text": f"Error: {result.get('error', 'Unknown error')}"}],
                "isError": True,
            }

    async def _log_request_start(
        self,
        tool_name: str,
        arguments: dict,
        category: str,
        is_mutation: bool,
    ) -> Optional[str]:
        """Log the start of an MCP request."""
        try:
            from src.models import McpRequest, McpRequestStatus, McpToolCategory

            async with self.db_session_factory() as session:
                request = McpRequest(
                    session_id=self._session_id,
                    tool_name=tool_name,
                    tool_category=McpToolCategory(category)
                    if category in [e.value for e in McpToolCategory]
                    else McpToolCategory.SYSTEM,
                    input_params=arguments,
                    status=McpRequestStatus.PROCESSING,
                    is_mutation=is_mutation,
                    started_at=datetime.utcnow(),
                )
                session.add(request)
                await session.commit()
                await session.refresh(request)
                return str(request.id)
        except Exception as e:
            # Don't fail the request if logging fails
            print(f"Failed to log MCP request start: {e}", file=sys.stderr)
            return None

    async def _log_request_complete(
        self,
        request_id: str,
        result: dict,
        duration_ms: int,
    ) -> None:
        """Log the completion of an MCP request."""
        try:
            from sqlalchemy import select

            from src.models import McpRequest

            async with self.db_session_factory() as session:
                stmt = select(McpRequest).where(McpRequest.id == request_id)
                db_result = await session.execute(stmt)
                request = db_result.scalar_one_or_none()

                if request:
                    if result.get("success", False):
                        request.mark_completed(result.get("result", {}))
                    else:
                        request.mark_failed(
                            error_message=result.get("error", "Unknown error"),
                            error_type=result.get("error_type", "Error"),
                        )
                    request.duration_ms = duration_ms
                    await session.commit()
        except Exception as e:
            print(f"Failed to log MCP request completion: {e}", file=sys.stderr)

    def _success_response(self, msg_id: Any, result: Any) -> dict:
        """Create a JSON-RPC success response."""
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result,
        }

    def _error_response(self, msg_id: Any, code: int, message: str) -> dict:
        """Create a JSON-RPC error response."""
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": code,
                "message": message,
            },
        }

    async def run_stdio(self) -> None:
        """Run the MCP server using stdio transport."""
        import sys

        while True:
            try:
                # Read line from stdin
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)

                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                # Parse JSON-RPC message
                try:
                    message = json.loads(line)
                except json.JSONDecodeError as e:
                    response = self._error_response(None, -32700, f"Parse error: {e}")
                    print(json.dumps(response), flush=True)
                    continue

                # Handle the message
                response = await self.handle_message(message)

                # Send response
                print(json.dumps(response), flush=True)

            except Exception as e:
                response = self._error_response(None, -32603, f"Internal error: {e}")
                print(json.dumps(response), flush=True)
