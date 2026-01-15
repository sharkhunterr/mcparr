"""Permission service for checking group-based tool access."""

from dataclasses import dataclass
from typing import List, Optional

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.group import Group, GroupMembership, GroupToolPermission


@dataclass
class PermissionCheckResult:
    """Result of a permission check."""

    has_access: bool
    granted_by_group: Optional[str] = None
    granted_by_group_id: Optional[str] = None
    denial_reason: Optional[str] = None


class PermissionService:
    """Service for checking user permissions based on group memberships."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _is_tool_restricted(self, tool_name: str, service_type: Optional[str] = None) -> bool:
        """
        Check if a tool is restricted (associated with any group).
        A tool is restricted if any group has a permission for it.
        """
        # Check for exact tool match or wildcard permissions
        result = await self.db.execute(
            select(func.count(GroupToolPermission.id)).where(
                and_(
                    GroupToolPermission.enabled == True,
                    # Match tool name or wildcard
                    ((GroupToolPermission.tool_name == tool_name) | (GroupToolPermission.tool_name == "*")),
                )
            )
        )
        count = result.scalar()
        return count > 0

    async def check_permission(
        self, central_user_id: str, tool_name: str, service_type: Optional[str] = None
    ) -> PermissionCheckResult:
        """
        Check if a user has permission to access a specific tool.

        Permission resolution:
        1. If the tool is not restricted (not associated with any group), allow access
        2. If the user has no groups, allow access to non-restricted tools
        3. Get all active groups the user belongs to
        4. Order by priority (highest first)
        5. Check each group's tool permissions
        6. Return access granted by the highest priority group with matching permission
        """
        # First check if the tool is restricted at all
        tool_is_restricted = await self._is_tool_restricted(tool_name, service_type)

        if not tool_is_restricted:
            logger.debug(f"Tool {tool_name} is not restricted by any group, access granted")
            return PermissionCheckResult(has_access=True, granted_by_group=None, granted_by_group_id=None)

        # Get user's active group memberships
        memberships_result = await self.db.execute(
            select(GroupMembership).where(
                and_(GroupMembership.central_user_id == central_user_id, GroupMembership.enabled == True)
            )
        )
        memberships = memberships_result.scalars().all()

        if not memberships:
            # User has no groups but tool is restricted - deny access
            logger.debug(f"User {central_user_id} has no group memberships and tool {tool_name} is restricted")
            return PermissionCheckResult(
                has_access=False, denial_reason="User is not a member of any group with access to this tool"
            )

        # Get all groups with their permissions, ordered by priority
        group_ids = [m.group_id for m in memberships]
        groups_result = await self.db.execute(
            select(Group)
            .options(selectinload(Group.tool_permissions))
            .where(and_(Group.id.in_(group_ids), Group.enabled == True))
            .order_by(Group.priority.desc())
        )
        groups = groups_result.scalars().all()

        if not groups:
            logger.debug(f"No enabled groups found for user {central_user_id}")
            return PermissionCheckResult(has_access=False, denial_reason="User's groups are all disabled")

        # Check each group's permissions in priority order
        for group in groups:
            for permission in group.tool_permissions:
                if not permission.enabled:
                    continue

                if permission.matches_tool(tool_name, service_type):
                    logger.debug(
                        f"User {central_user_id} granted access to {tool_name} "
                        f"by group {group.name} (priority {group.priority})"
                    )
                    return PermissionCheckResult(
                        has_access=True, granted_by_group=group.name, granted_by_group_id=str(group.id)
                    )

        logger.debug(f"User {central_user_id} denied access to {tool_name}: no matching permission")
        return PermissionCheckResult(has_access=False, denial_reason=f"No group grants access to tool '{tool_name}'")

    async def get_user_allowed_tools(self, central_user_id: str) -> List[str]:
        """Get all tools a user has access to based on their groups."""
        # Get user's active group memberships
        memberships_result = await self.db.execute(
            select(GroupMembership).where(
                and_(GroupMembership.central_user_id == central_user_id, GroupMembership.enabled == True)
            )
        )
        memberships = memberships_result.scalars().all()

        if not memberships:
            return []

        # Get all groups with their permissions
        group_ids = [m.group_id for m in memberships]
        groups_result = await self.db.execute(
            select(Group)
            .options(selectinload(Group.tool_permissions))
            .where(and_(Group.id.in_(group_ids), Group.enabled == True))
        )
        groups = groups_result.scalars().all()

        # Collect all allowed tools
        allowed_tools = set()
        has_wildcard = False

        for group in groups:
            for permission in group.tool_permissions:
                if not permission.enabled:
                    continue
                if permission.tool_name == "*":
                    has_wildcard = True
                else:
                    allowed_tools.add(permission.tool_name)

        if has_wildcard:
            # User has access to all tools
            return ["*"]

        return list(allowed_tools)

    async def get_tool_groups(self, tool_name: str, service_type: Optional[str] = None) -> List[dict]:
        """Get all groups that have access to a specific tool."""
        # Get all groups with permissions for this tool
        result = await self.db.execute(
            select(Group).options(selectinload(Group.tool_permissions)).where(Group.enabled == True)
        )
        groups = result.scalars().all()

        matching_groups = []
        for group in groups:
            for permission in group.tool_permissions:
                if not permission.enabled:
                    continue
                if permission.matches_tool(tool_name, service_type):
                    matching_groups.append(
                        {
                            "id": group.id,
                            "name": group.name,
                            "color": group.color,
                            "icon": group.icon,
                            "priority": group.priority,
                            "is_wildcard": permission.tool_name == "*",
                        }
                    )
                    break  # Only add group once even if multiple permissions match

        return matching_groups


async def check_tool_permission(
    db: AsyncSession, central_user_id: str, tool_name: str, service_type: Optional[str] = None
) -> PermissionCheckResult:
    """Convenience function to check tool permission."""
    service = PermissionService(db)
    return await service.check_permission(central_user_id, tool_name, service_type)
