"""Service Group management API routes for organizing services."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database.connection import get_db_session as get_db
from ..models.service_config import ServiceConfig, ServiceType
from ..models.service_group import ServiceGroup, ServiceGroupMembership
from ..schemas.service_groups import (
    AvailableService,
    AvailableServicesResponse,
    BulkServiceUpdate,
    ServiceGroupCreate,
    ServiceGroupDetailResponse,
    ServiceGroupListResponse,
    ServiceGroupMembershipCreate,
    ServiceGroupMembershipResponse,
    ServiceGroupResponse,
    ServiceGroupUpdate,
)

router = APIRouter(prefix="/api/service-groups", tags=["service-groups"])


# --- Non-parameterized routes (must come before /{group_id}) ---


@router.get("/available-services", response_model=AvailableServicesResponse)
async def get_available_services(db: AsyncSession = Depends(get_db)):
    """Get all available service types with their configuration status."""
    # Get all configured services
    result = await db.execute(select(ServiceConfig.service_type, ServiceConfig.name))
    configured = {row[0]: row[1] for row in result.all()}

    # Build list of all possible service types
    services = []
    for service_type in ServiceType:
        # Skip internal types
        if service_type.value in ("system",):
            continue

        display_names = {
            "plex": "Plex",
            "tautulli": "Tautulli",
            "overseerr": "Overseerr",
            "radarr": "Radarr",
            "sonarr": "Sonarr",
            "prowlarr": "Prowlarr",
            "jackett": "Jackett",
            "deluge": "Deluge",
            "komga": "Komga",
            "romm": "RomM",
            "audiobookshelf": "Audiobookshelf",
            "openwebui": "Open WebUI",
            "wikijs": "Wiki.js",
            "zammad": "Zammad",
            "authentik": "Authentik",
        }

        services.append(
            AvailableService(
                service_type=service_type.value,
                display_name=display_names.get(service_type.value, service_type.value.capitalize()),
                configured=service_type.value in configured,
                tool_count=0,  # TODO: Get actual tool count per service
            )
        )

    # Sort: configured first, then alphabetically
    services.sort(key=lambda s: (not s.configured, s.display_name))

    return AvailableServicesResponse(services=services, total=len(services))


# --- Service Group CRUD ---


@router.get("/", response_model=ServiceGroupListResponse)
async def list_service_groups(
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: AsyncSession = Depends(get_db),
):
    """List all service groups with optional filtering."""
    query = select(ServiceGroup).options(selectinload(ServiceGroup.memberships))

    if enabled is not None:
        query = query.where(ServiceGroup.enabled == enabled)

    query = query.order_by(ServiceGroup.priority.desc(), ServiceGroup.name).offset(skip).limit(limit)

    result = await db.execute(query)
    groups = result.scalars().all()

    # Get total count
    count_query = select(func.count(ServiceGroup.id))
    if enabled is not None:
        count_query = count_query.where(ServiceGroup.enabled == enabled)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return ServiceGroupListResponse(
        groups=[ServiceGroupResponse.model_validate(g) for g in groups], total=total, skip=skip, limit=limit
    )


@router.get("/{group_id}", response_model=ServiceGroupDetailResponse)
async def get_service_group(group_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific service group with all details."""
    result = await db.execute(
        select(ServiceGroup).options(selectinload(ServiceGroup.memberships)).where(ServiceGroup.id == group_id)
    )
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service group not found")

    # Get service info for members
    service_infos = {}
    if group.memberships:
        service_types = [m.service_type for m in group.memberships]
        services_result = await db.execute(
            select(ServiceConfig.service_type, ServiceConfig.name).where(ServiceConfig.service_type.in_(service_types))
        )
        for service_type, name in services_result.all():
            service_infos[service_type] = {"name": name, "configured": True}

    return ServiceGroupDetailResponse.model_validate(group, service_infos)


@router.post("/", response_model=ServiceGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_service_group(group_data: ServiceGroupCreate, db: AsyncSession = Depends(get_db)):
    """Create a new service group."""
    # Check if name already exists
    existing = await db.execute(select(ServiceGroup).where(ServiceGroup.name == group_data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Service group with this name already exists")

    # Create group without service_types (we'll add those as memberships)
    group_dict = group_data.model_dump(exclude={"service_types"})
    group = ServiceGroup(**group_dict)
    db.add(group)
    await db.flush()  # Get the ID

    # Add initial service memberships if provided
    if group_data.service_types:
        for service_type in group_data.service_types:
            membership = ServiceGroupMembership(group_id=group.id, service_type=service_type)
            db.add(membership)

    await db.commit()
    await db.refresh(group, ["memberships"])

    logger.info(f"Created service group: {group.name} ({group.id})")
    return ServiceGroupResponse.model_validate(group)


@router.put("/{group_id}", response_model=ServiceGroupResponse)
async def update_service_group(group_id: str, group_data: ServiceGroupUpdate, db: AsyncSession = Depends(get_db)):
    """Update an existing service group."""
    result = await db.execute(
        select(ServiceGroup).options(selectinload(ServiceGroup.memberships)).where(ServiceGroup.id == group_id)
    )
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service group not found")

    # Check name uniqueness if being changed
    if group_data.name and group_data.name != group.name:
        existing = await db.execute(select(ServiceGroup).where(ServiceGroup.name == group_data.name))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Service group with this name already exists"
            )

    # Update fields
    update_data = group_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)

    await db.commit()
    await db.refresh(group)

    logger.info(f"Updated service group: {group.name} ({group.id})")
    return ServiceGroupResponse.model_validate(group)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service_group(group_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a service group."""
    result = await db.execute(select(ServiceGroup).where(ServiceGroup.id == group_id))
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service group not found")

    if group.is_system:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete system service groups")

    await db.delete(group)
    await db.commit()
    logger.info(f"Deleted service group: {group.name} ({group.id})")


# --- Service Group Memberships ---


@router.get("/{group_id}/services", response_model=List[ServiceGroupMembershipResponse])
async def list_group_services(
    group_id: str, enabled: Optional[bool] = Query(None), db: AsyncSession = Depends(get_db)
):
    """List all services in a group."""
    # Verify group exists
    group_result = await db.execute(select(ServiceGroup).where(ServiceGroup.id == group_id))
    if not group_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Service group not found")

    query = select(ServiceGroupMembership).where(ServiceGroupMembership.group_id == group_id)
    if enabled is not None:
        query = query.where(ServiceGroupMembership.enabled == enabled)

    result = await db.execute(query)
    memberships = result.scalars().all()

    # Get service info
    service_infos = {}
    if memberships:
        service_types = [m.service_type for m in memberships]
        services_result = await db.execute(
            select(ServiceConfig.service_type, ServiceConfig.name).where(ServiceConfig.service_type.in_(service_types))
        )
        for service_type, name in services_result.all():
            service_infos[service_type] = {"name": name, "configured": True}

    return [ServiceGroupMembershipResponse.model_validate(m, service_infos.get(m.service_type)) for m in memberships]


@router.post("/{group_id}/services", response_model=ServiceGroupMembershipResponse, status_code=status.HTTP_201_CREATED)
async def add_service_to_group(
    group_id: str, membership_data: ServiceGroupMembershipCreate, db: AsyncSession = Depends(get_db)
):
    """Add a service to a group."""
    # Verify group exists
    group_result = await db.execute(select(ServiceGroup).where(ServiceGroup.id == group_id))
    if not group_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Service group not found")

    # Check if membership already exists
    existing = await db.execute(
        select(ServiceGroupMembership).where(
            and_(
                ServiceGroupMembership.group_id == group_id,
                ServiceGroupMembership.service_type == membership_data.service_type,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Service is already in this group")

    membership = ServiceGroupMembership(group_id=group_id, **membership_data.model_dump())
    db.add(membership)
    await db.commit()
    await db.refresh(membership)

    # Get service info
    service_info = None
    service_result = await db.execute(
        select(ServiceConfig.name).where(ServiceConfig.service_type == membership_data.service_type).limit(1)
    )
    name = service_result.scalar()
    if name:
        service_info = {"name": name, "configured": True}

    logger.info(f"Added service {membership_data.service_type} to group {group_id}")
    return ServiceGroupMembershipResponse.model_validate(membership, service_info)


@router.delete("/{group_id}/services/{service_type}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_service_from_group(group_id: str, service_type: str, db: AsyncSession = Depends(get_db)):
    """Remove a service from a group."""
    result = await db.execute(
        select(ServiceGroupMembership).where(
            and_(ServiceGroupMembership.group_id == group_id, ServiceGroupMembership.service_type == service_type)
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(status_code=404, detail="Service not found in this group")

    await db.delete(membership)
    await db.commit()
    logger.info(f"Removed service {service_type} from group {group_id}")


@router.post("/{group_id}/services/bulk", response_model=dict)
async def bulk_update_group_services(group_id: str, bulk_data: BulkServiceUpdate, db: AsyncSession = Depends(get_db)):
    """Bulk add or remove services from a group."""
    # Verify group exists
    group_result = await db.execute(select(ServiceGroup).where(ServiceGroup.id == group_id))
    if not group_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Service group not found")

    added = 0
    removed = 0
    errors = []

    if bulk_data.action == "add":
        for service_type in bulk_data.service_types:
            # Check if already exists
            existing = await db.execute(
                select(ServiceGroupMembership).where(
                    and_(ServiceGroupMembership.group_id == group_id, ServiceGroupMembership.service_type == service_type)
                )
            )
            if existing.scalar_one_or_none():
                errors.append(f"{service_type}: already in group")
                continue

            membership = ServiceGroupMembership(group_id=group_id, service_type=service_type)
            db.add(membership)
            added += 1

    elif bulk_data.action == "remove":
        for service_type in bulk_data.service_types:
            result = await db.execute(
                select(ServiceGroupMembership).where(
                    and_(ServiceGroupMembership.group_id == group_id, ServiceGroupMembership.service_type == service_type)
                )
            )
            membership = result.scalar_one_or_none()
            if not membership:
                errors.append(f"{service_type}: not in group")
                continue

            await db.delete(membership)
            removed += 1
    else:
        raise HTTPException(status_code=400, detail="Action must be 'add' or 'remove'")

    await db.commit()
    logger.info(f"Bulk service update for group {group_id}: added={added}, removed={removed}")

    return {"added": added, "removed": removed, "errors": errors}
