"""Group management API routes for access control."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database.connection import get_db_session as get_db
from ..models.group import Group, GroupMembership, GroupToolPermission
from ..models.user_mapping import UserMapping
from ..schemas.groups import (
    BulkMembershipUpdate,
    BulkPermissionUpdate,
    GroupCreate,
    GroupDetailResponse,
    GroupListResponse,
    GroupMembershipCreate,
    GroupMembershipResponse,
    GroupResponse,
    GroupToolPermissionCreate,
    GroupToolPermissionResponse,
    GroupToolPermissionUpdate,
    GroupUpdate,
    PermissionCheckRequest,
    PermissionCheckResponse,
    UserGroupsResponse,
)

router = APIRouter(prefix="/api/groups", tags=["groups"])


# --- Non-parameterized routes (must come before /{group_id}) ---


@router.get("/available-tools", response_model=dict)
async def get_available_tools(db: AsyncSession = Depends(get_db)):
    """Get all available tools from registered services for permission assignment."""
    from ..routers.openapi_tools import get_tool_registry

    registry = await get_tool_registry(db)
    tools_by_service = {}

    for tool_def in registry.list_tools():
        service_type = tool_def.requires_service or "system"
        if service_type not in tools_by_service:
            tools_by_service[service_type] = []
        tools_by_service[service_type].append(
            {"name": tool_def.name, "description": tool_def.description, "category": tool_def.category}
        )

    return {"tools_by_service": tools_by_service, "total_tools": sum(len(tools) for tools in tools_by_service.values())}


@router.post("/check-permission", response_model=PermissionCheckResponse)
async def check_user_permission(check_request: PermissionCheckRequest, db: AsyncSession = Depends(get_db)):
    """Check if a user has permission to access a specific tool."""
    from ..services.permission_service import PermissionService

    permission_service = PermissionService(db)
    result = await permission_service.check_permission(
        central_user_id=check_request.central_user_id,
        tool_name=check_request.tool_name,
        service_type=check_request.service_type,
    )

    return PermissionCheckResponse(
        has_access=result.has_access,
        central_user_id=check_request.central_user_id,
        tool_name=check_request.tool_name,
        service_type=check_request.service_type,
        granted_by_group=result.granted_by_group,
        granted_by_group_id=result.granted_by_group_id,
    )


@router.get("/tool/{tool_name}/groups", response_model=dict)
async def get_tool_groups_api(
    tool_name: str, service_type: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)
):
    """Get all groups that have permission for a specific tool."""
    from ..services.permission_service import PermissionService

    permission_service = PermissionService(db)
    groups = await permission_service.get_tool_groups(tool_name, service_type)

    return {"tool_name": tool_name, "service_type": service_type, "groups": groups, "total_groups": len(groups)}


@router.get("/tools-with-groups", response_model=dict)
async def get_all_tools_with_groups(db: AsyncSession = Depends(get_db)):
    """Get all tools with their associated groups (for displaying in the UI)."""
    # Get all tool permissions with their groups
    result = await db.execute(
        select(GroupToolPermission, Group)
        .join(Group, GroupToolPermission.group_id == Group.id)
        .where(and_(GroupToolPermission.enabled is True, Group.enabled is True))
    )
    rows = result.all()

    # Build a mapping of tool_name -> list of groups
    tool_groups: dict = {}
    for permission, group in rows:
        if permission.tool_name not in tool_groups:
            tool_groups[permission.tool_name] = []
        tool_groups[permission.tool_name].append(
            {
                "id": str(group.id),
                "name": group.name,
                "color": group.color,
                "icon": group.icon,
                "priority": group.priority,
                "is_wildcard": permission.tool_name == "*",
            }
        )

    return {"tool_groups": tool_groups, "total_tools_with_groups": len(tool_groups)}


@router.get("/user/{central_user_id}", response_model=UserGroupsResponse)
async def get_user_groups(central_user_id: str, db: AsyncSession = Depends(get_db)):
    """Get all groups a user belongs to."""
    # Get all memberships for this user
    memberships_result = await db.execute(
        select(GroupMembership).where(
            and_(GroupMembership.central_user_id == central_user_id, GroupMembership.enabled is True)
        )
    )
    memberships = memberships_result.scalars().all()

    if not memberships:
        return UserGroupsResponse(central_user_id=central_user_id, groups=[], total_groups=0)

    # Get the actual groups
    group_ids = [m.group_id for m in memberships]
    groups_result = await db.execute(
        select(Group)
        .options(selectinload(Group.memberships), selectinload(Group.tool_permissions))
        .where(and_(Group.id.in_(group_ids), Group.enabled is True))
        .order_by(Group.priority.desc())
    )
    groups = groups_result.scalars().all()

    return UserGroupsResponse(
        central_user_id=central_user_id,
        groups=[GroupResponse.model_validate(g) for g in groups],
        total_groups=len(groups),
    )


# --- Group CRUD ---


@router.get("/", response_model=GroupListResponse)
async def list_groups(
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: AsyncSession = Depends(get_db),
):
    """List all groups with optional filtering."""
    query = select(Group).options(selectinload(Group.memberships), selectinload(Group.tool_permissions))

    if enabled is not None:
        query = query.where(Group.enabled == enabled)

    query = query.order_by(Group.priority.desc(), Group.name).offset(skip).limit(limit)

    result = await db.execute(query)
    groups = result.scalars().all()

    # Get total count
    count_query = select(func.count(Group.id))
    if enabled is not None:
        count_query = count_query.where(Group.enabled == enabled)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return GroupListResponse(
        groups=[GroupResponse.model_validate(g) for g in groups], total=total, skip=skip, limit=limit
    )


@router.get("/{group_id}", response_model=GroupDetailResponse)
async def get_group(group_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific group with all details."""
    result = await db.execute(
        select(Group)
        .options(selectinload(Group.memberships), selectinload(Group.tool_permissions))
        .where(Group.id == group_id)
    )
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    # Get usernames for members
    usernames = {}
    if group.memberships:
        user_ids = [m.central_user_id for m in group.memberships]
        users_result = await db.execute(
            select(UserMapping.central_user_id, UserMapping.central_username)
            .where(UserMapping.central_user_id.in_(user_ids))
            .distinct()
        )
        for user_id, username in users_result.all():
            usernames[user_id] = username

    return GroupDetailResponse.model_validate(group, usernames)


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(group_data: GroupCreate, db: AsyncSession = Depends(get_db)):
    """Create a new group."""
    # Check if name already exists
    existing = await db.execute(select(Group).where(Group.name == group_data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Group with this name already exists")

    group = Group(**group_data.model_dump())
    db.add(group)
    await db.commit()
    await db.refresh(group, ["memberships", "tool_permissions"])

    logger.info(f"Created group: {group.name} ({group.id})")
    return GroupResponse.model_validate(group)


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(group_id: str, group_data: GroupUpdate, db: AsyncSession = Depends(get_db)):
    """Update an existing group."""
    result = await db.execute(
        select(Group)
        .options(selectinload(Group.memberships), selectinload(Group.tool_permissions))
        .where(Group.id == group_id)
    )
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    # Check name uniqueness if being changed
    if group_data.name and group_data.name != group.name:
        existing = await db.execute(select(Group).where(Group.name == group_data.name))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Group with this name already exists")

    # Update fields
    update_data = group_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)

    await db.commit()
    await db.refresh(group)

    logger.info(f"Updated group: {group.name} ({group.id})")
    return GroupResponse.model_validate(group)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(group_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a group."""
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    if group.is_system:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete system groups")

    await db.delete(group)
    await db.commit()
    logger.info(f"Deleted group: {group.name} ({group.id})")


# --- Group Memberships ---


@router.get("/{group_id}/members", response_model=List[GroupMembershipResponse])
async def list_group_members(group_id: str, enabled: Optional[bool] = Query(None), db: AsyncSession = Depends(get_db)):
    """List all members of a group."""
    # Verify group exists
    group_result = await db.execute(select(Group).where(Group.id == group_id))
    if not group_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Group not found")

    query = select(GroupMembership).where(GroupMembership.group_id == group_id)
    if enabled is not None:
        query = query.where(GroupMembership.enabled == enabled)

    result = await db.execute(query)
    memberships = result.scalars().all()

    # Get usernames
    usernames = {}
    if memberships:
        user_ids = [m.central_user_id for m in memberships]
        users_result = await db.execute(
            select(UserMapping.central_user_id, UserMapping.central_username)
            .where(UserMapping.central_user_id.in_(user_ids))
            .distinct()
        )
        for user_id, username in users_result.all():
            usernames[user_id] = username

    return [GroupMembershipResponse.model_validate(m, usernames.get(m.central_user_id)) for m in memberships]


@router.post("/{group_id}/members", response_model=GroupMembershipResponse, status_code=status.HTTP_201_CREATED)
async def add_group_member(group_id: str, membership_data: GroupMembershipCreate, db: AsyncSession = Depends(get_db)):
    """Add a user to a group."""
    # Verify group exists
    group_result = await db.execute(select(Group).where(Group.id == group_id))
    if not group_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Group not found")

    # Check if membership already exists
    existing = await db.execute(
        select(GroupMembership).where(
            and_(
                GroupMembership.group_id == group_id, GroupMembership.central_user_id == membership_data.central_user_id
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a member of this group")

    membership = GroupMembership(group_id=group_id, **membership_data.model_dump())
    db.add(membership)
    await db.commit()
    await db.refresh(membership)

    # Get username
    username_result = await db.execute(
        select(UserMapping.central_username)
        .where(UserMapping.central_user_id == membership_data.central_user_id)
        .limit(1)
    )
    username = username_result.scalar()

    logger.info(f"Added user {membership_data.central_user_id} to group {group_id}")
    return GroupMembershipResponse.model_validate(membership, username)


@router.delete("/{group_id}/members/{central_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_group_member(group_id: str, central_user_id: str, db: AsyncSession = Depends(get_db)):
    """Remove a user from a group."""
    result = await db.execute(
        select(GroupMembership).where(
            and_(GroupMembership.group_id == group_id, GroupMembership.central_user_id == central_user_id)
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    await db.delete(membership)
    await db.commit()
    logger.info(f"Removed user {central_user_id} from group {group_id}")


@router.post("/{group_id}/members/bulk", response_model=dict)
async def bulk_update_members(group_id: str, bulk_data: BulkMembershipUpdate, db: AsyncSession = Depends(get_db)):
    """Bulk add or remove members from a group."""
    # Verify group exists
    group_result = await db.execute(select(Group).where(Group.id == group_id))
    if not group_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Group not found")

    added = 0
    removed = 0
    errors = []

    for user_id in bulk_data.central_user_ids:
        try:
            if bulk_data.action == "add":
                # Check if already exists
                existing = await db.execute(
                    select(GroupMembership).where(
                        and_(GroupMembership.group_id == group_id, GroupMembership.central_user_id == user_id)
                    )
                )
                if not existing.scalar_one_or_none():
                    membership = GroupMembership(group_id=group_id, central_user_id=user_id)
                    db.add(membership)
                    added += 1
            elif bulk_data.action == "remove":
                result = await db.execute(
                    select(GroupMembership).where(
                        and_(GroupMembership.group_id == group_id, GroupMembership.central_user_id == user_id)
                    )
                )
                membership = result.scalar_one_or_none()
                if membership:
                    await db.delete(membership)
                    removed += 1
        except Exception as e:
            errors.append({"user_id": user_id, "error": str(e)})

    await db.commit()

    return {"action": bulk_data.action, "added": added, "removed": removed, "errors": errors}


# --- Tool Permissions ---


@router.get("/{group_id}/permissions", response_model=List[GroupToolPermissionResponse])
async def list_group_permissions(
    group_id: str,
    service_type: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all tool permissions for a group."""
    # Verify group exists
    group_result = await db.execute(select(Group).where(Group.id == group_id))
    if not group_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Group not found")

    query = select(GroupToolPermission).where(GroupToolPermission.group_id == group_id)
    if service_type:
        query = query.where(GroupToolPermission.service_type == service_type)
    if enabled is not None:
        query = query.where(GroupToolPermission.enabled == enabled)

    result = await db.execute(query)
    permissions = result.scalars().all()

    return [GroupToolPermissionResponse.model_validate(p) for p in permissions]


@router.post("/{group_id}/permissions", response_model=GroupToolPermissionResponse, status_code=status.HTTP_201_CREATED)
async def add_tool_permission(
    group_id: str, permission_data: GroupToolPermissionCreate, db: AsyncSession = Depends(get_db)
):
    """Add a tool permission to a group."""
    # Verify group exists
    group_result = await db.execute(select(Group).where(Group.id == group_id))
    if not group_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Group not found")

    # Check if permission already exists
    existing = await db.execute(
        select(GroupToolPermission).where(
            and_(
                GroupToolPermission.group_id == group_id,
                GroupToolPermission.tool_name == permission_data.tool_name,
                GroupToolPermission.service_type == permission_data.service_type,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Permission already exists for this tool")

    permission = GroupToolPermission(group_id=group_id, **permission_data.model_dump())
    db.add(permission)
    await db.commit()
    await db.refresh(permission)

    logger.info(f"Added permission for tool {permission_data.tool_name} to group {group_id}")
    return GroupToolPermissionResponse.model_validate(permission)


@router.put("/{group_id}/permissions/{permission_id}", response_model=GroupToolPermissionResponse)
async def update_tool_permission(
    group_id: str, permission_id: str, permission_data: GroupToolPermissionUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a tool permission."""
    result = await db.execute(
        select(GroupToolPermission).where(
            and_(GroupToolPermission.id == permission_id, GroupToolPermission.group_id == group_id)
        )
    )
    permission = result.scalar_one_or_none()

    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    update_data = permission_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(permission, field, value)

    await db.commit()
    await db.refresh(permission)

    return GroupToolPermissionResponse.model_validate(permission)


@router.delete("/{group_id}/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool_permission(group_id: str, permission_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a tool permission."""
    result = await db.execute(
        select(GroupToolPermission).where(
            and_(GroupToolPermission.id == permission_id, GroupToolPermission.group_id == group_id)
        )
    )
    permission = result.scalar_one_or_none()

    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    await db.delete(permission)
    await db.commit()
    logger.info(f"Deleted permission {permission_id} from group {group_id}")


@router.post("/{group_id}/permissions/bulk", response_model=dict)
async def bulk_update_permissions(group_id: str, bulk_data: BulkPermissionUpdate, db: AsyncSession = Depends(get_db)):
    """Bulk add or update tool permissions for a group."""
    # Verify group exists
    group_result = await db.execute(select(Group).where(Group.id == group_id))
    if not group_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Group not found")

    added = 0
    updated = 0
    errors = []

    for tool_name in bulk_data.tool_names:
        try:
            # Check if permission exists
            existing_result = await db.execute(
                select(GroupToolPermission).where(
                    and_(
                        GroupToolPermission.group_id == group_id,
                        GroupToolPermission.tool_name == tool_name,
                        GroupToolPermission.service_type == bulk_data.service_type,
                    )
                )
            )
            existing = existing_result.scalar_one_or_none()

            if existing:
                existing.enabled = bulk_data.enabled
                updated += 1
            else:
                permission = GroupToolPermission(
                    group_id=group_id,
                    tool_name=tool_name,
                    service_type=bulk_data.service_type,
                    enabled=bulk_data.enabled,
                )
                db.add(permission)
                added += 1
        except Exception as e:
            errors.append({"tool_name": tool_name, "error": str(e)})

    await db.commit()

    return {"added": added, "updated": updated, "errors": errors}
