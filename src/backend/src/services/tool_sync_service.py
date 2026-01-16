"""Tool synchronization service for cleaning orphan tool permissions."""

from typing import Set, Tuple

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.group import GroupToolPermission


class ToolSyncService:
    """Service for synchronizing tool permissions with available tools.

    Automatically removes permissions for tools that no longer exist,
    ensuring the database stays in sync with the tool registry.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_available_tools(self) -> Set[str]:
        """Get all available tool names from the registry."""
        from ..routers.openapi_tools import get_all_tool_definitions
        return set(get_all_tool_definitions().keys())

    async def get_orphan_tools(self) -> Set[str]:
        """Find tools in database that no longer exist in the registry.

        Returns:
            Set of orphan tool names
        """
        # Get tools from database
        result = await self.db.execute(
            select(GroupToolPermission.tool_name).distinct()
        )
        db_tools = {row[0] for row in result.fetchall()}

        # Get available tools from registry
        available_tools = self._get_available_tools()

        # Find orphan tools (in DB but not available), excluding wildcard
        orphan_tools = {t for t in db_tools if t != "*" and t not in available_tools}

        return orphan_tools

    async def cleanup_orphan_tools(self) -> Tuple[int, Set[str]]:
        """Remove permissions for tools that no longer exist.

        Returns:
            Tuple of (number of deleted permissions, set of deleted tool names)
        """
        orphan_tools = await self.get_orphan_tools()

        if not orphan_tools:
            logger.debug("No orphan tools found, database is in sync")
            return 0, set()

        # Delete orphan permissions
        result = await self.db.execute(
            delete(GroupToolPermission).where(
                GroupToolPermission.tool_name.in_(orphan_tools)
            )
        )

        deleted_count = result.rowcount
        await self.db.commit()

        logger.info(
            f"Cleaned up {deleted_count} orphan tool permissions: {sorted(orphan_tools)}"
        )

        return deleted_count, orphan_tools

    async def get_sync_status(self) -> dict:
        """Get synchronization status between DB and registry.

        Returns:
            Dict with sync status information
        """
        # Get tools from database
        result = await self.db.execute(
            select(GroupToolPermission.tool_name).distinct()
        )
        db_tools = {row[0] for row in result.fetchall()}

        # Get available tools from registry
        available_tools = self._get_available_tools()

        # Calculate differences
        orphan_tools = {t for t in db_tools if t != "*" and t not in available_tools}
        missing_tools = available_tools - db_tools

        return {
            "db_tool_count": len(db_tools),
            "registry_tool_count": len(available_tools),
            "orphan_tools": sorted(orphan_tools),
            "orphan_count": len(orphan_tools),
            "in_sync": len(orphan_tools) == 0,
        }


async def cleanup_orphan_tools(db: AsyncSession) -> Tuple[int, Set[str]]:
    """Convenience function to cleanup orphan tools."""
    service = ToolSyncService(db)
    return await service.cleanup_orphan_tools()


async def get_tool_sync_status(db: AsyncSession) -> dict:
    """Convenience function to get sync status."""
    service = ToolSyncService(db)
    return await service.get_sync_status()
