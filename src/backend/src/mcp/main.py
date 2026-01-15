#!/usr/bin/env python3
"""MCP Server entry point for MCParr AI Gateway.

This script runs the MCP server as a standalone process using stdio transport.
It's designed to be configured in Open WebUI or other MCP clients.

Usage:
    python -m src.mcp.main

Environment Variables:
    DATABASE_URL: SQLite database URL (default: sqlite+aiosqlite:///./mcparr.db)
"""

import asyncio
import os
import sys

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


async def load_service_configs():
    """Load service configurations from database."""
    from sqlalchemy import select

    from src.database.connection import get_db_session
    from src.models import ServiceConfig

    configs = []
    async for session in get_db_session():
        result = await session.execute(select(ServiceConfig).where(ServiceConfig.enabled == True))
        services = result.scalars().all()

        for service in services:
            configs.append(
                {
                    "id": str(service.id),
                    "name": service.name,
                    "service_type": service.service_type,
                    "base_url": service.base_url,
                    "external_url": getattr(service, "external_url", None),
                    "port": service.port,
                    "api_key": service.api_key,
                    "username": service.username,
                    "password": service.password,
                    "config": service.config or {},
                }
            )

    return configs


async def main():
    """Main entry point for the MCP server."""
    from src.database.connection import async_session_maker
    from src.mcp.server import MCPServer

    # Create the MCP server
    server = MCPServer(db_session_factory=async_session_maker)

    # Load service configurations
    try:
        service_configs = await load_service_configs()
        print(f"Loaded {len(service_configs)} service configurations", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Could not load service configurations: {e}", file=sys.stderr)
        service_configs = []

    # Initialize the server with service configs
    await server.initialize(service_configs)

    print("MCP Server initialized. Listening on stdio...", file=sys.stderr)

    # Run the stdio server
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
