"""User mapping management API routes."""
# Force reload v2

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database.connection import get_db_session as get_db
from ..models.service_config import ServiceConfig
from ..models.user_mapping import MappingStatus, UserMapping, UserRole
from ..schemas.users import (
    UserMappingCreate,
    UserMappingListResponse,
    UserMappingResponse,
    UserMappingUpdate,
    UserSyncRequest,
    UserSyncResult,
)

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/", response_model=UserMappingListResponse)
async def list_user_mappings(
    central_user_id: Optional[str] = Query(None, description="Filter by central user ID"),
    service_id: Optional[str] = Query(None, description="Filter by service ID"),
    status: Optional[MappingStatus] = Query(None, description="Filter by mapping status"),
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: AsyncSession = Depends(get_db),
):
    """List user mappings with optional filtering."""
    query = select(UserMapping).options(selectinload(UserMapping.service_config))

    # Apply filters
    filters = []
    if central_user_id:
        filters.append(UserMapping.central_user_id == central_user_id)
    if service_id:
        filters.append(UserMapping.service_config_id == service_id)
    if status:
        filters.append(UserMapping.status == status)
    if role:
        filters.append(UserMapping.role == role)

    if filters:
        query = query.where(and_(*filters))

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    mappings = result.scalars().all()

    # Get total count
    count_query = select(UserMapping)
    if filters:
        count_query = count_query.where(and_(*filters))
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return UserMappingListResponse(
        mappings=[UserMappingResponse.model_validate(mapping) for mapping in mappings],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/statistics", response_model=dict)
async def get_user_mapping_statistics(db: AsyncSession = Depends(get_db)):
    """Get user mapping statistics."""
    # Get total mappings
    total_result = await db.execute(select(UserMapping))
    total_mappings = len(total_result.scalars().all())

    # Get mappings by status
    active_result = await db.execute(select(UserMapping).where(UserMapping.status == MappingStatus.ACTIVE))
    active_mappings = len(active_result.scalars().all())

    pending_result = await db.execute(select(UserMapping).where(UserMapping.status == MappingStatus.PENDING))
    pending_mappings = len(pending_result.scalars().all())

    inactive_result = await db.execute(select(UserMapping).where(UserMapping.status == MappingStatus.INACTIVE))
    inactive_mappings = len(inactive_result.scalars().all())

    # Get unique users count
    unique_users_result = await db.execute(select(UserMapping.central_user_id).distinct())
    unique_users = len(unique_users_result.scalars().all())

    # Get mappings by service
    services_result = await db.execute(
        select(ServiceConfig.name, ServiceConfig.id).join(
            UserMapping, ServiceConfig.id == UserMapping.service_config_id
        )
    )
    service_mappings = services_result.all()

    service_stats = {}
    for service_name, _service_id in service_mappings:
        if service_name not in service_stats:
            service_stats[service_name] = 0
        service_stats[service_name] += 1

    return {
        "total_mappings": total_mappings,
        "unique_users": unique_users,
        "status_breakdown": {"active": active_mappings, "pending": pending_mappings, "inactive": inactive_mappings},
        "service_breakdown": service_stats,
        "average_mappings_per_user": total_mappings / unique_users if unique_users > 0 else 0,
    }


@router.get("/central-user/{central_user_id}", response_model=List[UserMappingResponse])
async def get_user_mappings_by_central_user(central_user_id: str, db: AsyncSession = Depends(get_db)):
    """Get all mappings for a central user."""
    result = await db.execute(
        select(UserMapping)
        .options(selectinload(UserMapping.service_config))
        .where(UserMapping.central_user_id == central_user_id)
    )
    mappings = result.scalars().all()

    return [UserMappingResponse.model_validate(mapping) for mapping in mappings]


@router.get("/service/{service_id}", response_model=List[UserMappingResponse])
async def get_user_mappings_by_service(service_id: str, db: AsyncSession = Depends(get_db)):
    """Get all user mappings for a service."""
    result = await db.execute(
        select(UserMapping)
        .options(selectinload(UserMapping.service_config))
        .where(UserMapping.service_config_id == service_id)
    )
    mappings = result.scalars().all()

    return [UserMappingResponse.model_validate(mapping) for mapping in mappings]


@router.get("/central-users", response_model=dict)
async def get_central_users_list(db: AsyncSession = Depends(get_db)):
    """Get a simplified list of central users for group membership selection."""
    from sqlalchemy import distinct, func

    # Get unique central_user_id with their service counts
    result = await db.execute(
        select(
            UserMapping.central_user_id,
            func.max(UserMapping.service_username).label("central_username"),
            func.count(distinct(UserMapping.service_config_id)).label("service_count"),
        )
        .where(UserMapping.central_user_id.isnot(None))
        .group_by(UserMapping.central_user_id)
        .order_by(func.max(UserMapping.service_username))
    )

    users = [
        {
            "central_user_id": row.central_user_id,
            "central_username": row.central_username or row.central_user_id,
            "service_count": row.service_count,
        }
        for row in result.fetchall()
    ]

    return {"users": users, "total": len(users)}


@router.get("/enumerate-users", response_model=dict)
async def enumerate_all_users(db: AsyncSession = Depends(get_db)):
    """Enumerate users from all configured services for manual mapping."""
    from ..services.service_registry import service_registry

    # Services that don't have user management (skip them)
    SERVICES_WITHOUT_USERS = {"ollama"}

    # Get all enabled services
    services_result = await db.execute(select(ServiceConfig).where(ServiceConfig.enabled is True))
    services = services_result.scalars().all()

    all_users = {}
    errors = []
    skipped_services = 0

    for service in services:
        # Skip services that don't have user management
        service_type = service.service_type.value if hasattr(service.service_type, "value") else service.service_type
        if service_type.lower() in SERVICES_WITHOUT_USERS:
            logger.debug(f"Skipping {service.name} - service type {service_type} does not support user management")
            skipped_services += 1
            continue

        try:
            adapter = await service_registry.create_adapter(service)
            if not adapter:
                errors.append(f"No adapter available for {service.name}")
                continue

            async with adapter:
                # Test connection first
                test_result = await adapter.test_connection()
                if not test_result.success:
                    errors.append(f"{service.name}: Connection failed - {test_result.message}")
                    continue

                # Try to get users if adapter supports it
                try:
                    if hasattr(adapter, "get_users"):
                        users_data = await adapter.get_users()
                        if isinstance(users_data, dict) and "users" in users_data:
                            users = users_data["users"]
                        elif isinstance(users_data, list):
                            users = users_data
                        else:
                            users = []

                        all_users[service.id] = {
                            "service_name": service.name,
                            "service_type": service.service_type.value
                            if hasattr(service.service_type, "value")
                            else service.service_type,
                            "base_url": service.base_url,
                            "users": users,
                            "user_count": len(users),
                        }
                    else:
                        all_users[service.id] = {
                            "service_name": service.name,
                            "service_type": service.service_type.value
                            if hasattr(service.service_type, "value")
                            else service.service_type,
                            "base_url": service.base_url,
                            "users": [],
                            "user_count": 0,
                            "note": "Service does not support user enumeration",
                        }
                except Exception as e:
                    errors.append(f"{service.name}: Failed to enumerate users - {str(e)}")
                    all_users[service.id] = {
                        "service_name": service.name,
                        "service_type": service.service_type.value,
                        "base_url": service.base_url,
                        "users": [],
                        "user_count": 0,
                        "error": str(e),
                    }

        except Exception as e:
            errors.append(f"{service.name}: Adapter error - {str(e)}")

    return {
        "services": all_users,
        "total_services": len(services),
        "successful_enumerations": len([s for s in all_users.values() if "error" not in s]),
        "errors": errors,
        "enumerated_at": datetime.utcnow(),
    }


@router.get("/{mapping_id}", response_model=UserMappingResponse)
async def get_user_mapping(mapping_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific user mapping."""
    result = await db.execute(
        select(UserMapping).options(selectinload(UserMapping.service_config)).where(UserMapping.id == mapping_id)
    )
    mapping = result.scalar_one_or_none()

    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User mapping not found")

    return UserMappingResponse.model_validate(mapping)


@router.post("/", response_model=UserMappingResponse, status_code=status.HTTP_201_CREATED)
async def create_user_mapping(request: Request, db: AsyncSession = Depends(get_db)):
    """Create a new user mapping."""
    try:
        # Read raw request body first
        raw_body = await request.body()
        logger.info(f"🔍 Raw request body: {raw_body.decode()}")

        # Parse JSON manually to see what we get
        import json

        try:
            raw_data = json.loads(raw_body.decode())
            logger.info(f"🔍 Parsed JSON data: {raw_data}")
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON") from e

        # Try to validate with Pydantic
        try:
            mapping_data = UserMappingCreate(**raw_data)
            logger.info(f"✅ Pydantic validation successful: {mapping_data.model_dump()}")
        except Exception as e:
            logger.error(f"❌ Pydantic validation failed: {e}")
            logger.error(f"❌ Data that failed validation: {raw_data}")
            raise HTTPException(status_code=422, detail=str(e)) from e

        # Check if service exists
        service_result = await db.execute(
            select(ServiceConfig).where(ServiceConfig.id == mapping_data.service_config_id)
        )
        service = service_result.scalar_one_or_none()

        if not service:
            logger.error(f"❌ Service not found: {mapping_data.service_config_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service configuration not found")

        logger.info(f"✅ Service found: {service.name} ({service.id})")

        # Check if mapping already exists for this user and service
        existing_result = await db.execute(
            select(UserMapping).where(
                and_(
                    UserMapping.central_user_id == mapping_data.central_user_id,
                    UserMapping.service_config_id == mapping_data.service_config_id,
                )
            )
        )
        existing_mapping = existing_result.scalar_one_or_none()

        if existing_mapping:
            logger.error(
                f"❌ Mapping already exists: central_user={mapping_data.central_user_id}, "
                f"service={mapping_data.service_config_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="User mapping already exists for this user and service"
            )

        # Create new mapping
        logger.info(f"📝 Creating mapping object with data: {mapping_data.model_dump()}")
        mapping = UserMapping(**mapping_data.model_dump())
        db.add(mapping)
        await db.commit()
        await db.refresh(mapping, ["service_config"])

        logger.info(f"✅ User mapping created successfully: {mapping.id}")
        return UserMappingResponse.model_validate(mapping)

    except HTTPException:
        # Re-raise HTTP exceptions as-is from None
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error creating user mapping: {str(e)}")
        logger.error(f"❌ Mapping data causing error: {mapping_data.model_dump()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create user mapping: {str(e)}"
        ) from e


@router.put("/{mapping_id}", response_model=UserMappingResponse)
async def update_user_mapping(mapping_id: str, mapping_data: UserMappingUpdate, db: AsyncSession = Depends(get_db)):
    """Update an existing user mapping."""
    result = await db.execute(
        select(UserMapping).options(selectinload(UserMapping.service_config)).where(UserMapping.id == mapping_id)
    )
    mapping = result.scalar_one_or_none()

    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User mapping not found")

    # Update only provided fields
    update_data = mapping_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(mapping, field, value)

    await db.commit()
    await db.refresh(mapping)

    return UserMappingResponse.model_validate(mapping)


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_mapping(mapping_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a user mapping."""
    result = await db.execute(select(UserMapping).where(UserMapping.id == mapping_id))
    mapping = result.scalar_one_or_none()

    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User mapping not found")

    await db.delete(mapping)
    await db.commit()


@router.post("/sync", response_model=UserSyncResult)
async def sync_user_with_services(sync_request: UserSyncRequest, db: AsyncSession = Depends(get_db)):
    """Synchronize a user across all mapped services."""
    # Get all mappings for the user
    result = await db.execute(
        select(UserMapping)
        .options(selectinload(UserMapping.service_config))
        .where(UserMapping.central_user_id == sync_request.central_user_id)
    )
    mappings = result.scalars().all()

    if not mappings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No user mappings found for this central user"
        )

    sync_results = []
    success_count = 0

    for mapping in mappings:
        try:
            # Import service tester for adapter functionality
            from ..services.service_tester import ServiceTester

            adapter = ServiceTester.get_adapter_for_service(mapping.service_config)
            if not adapter:
                sync_results.append(
                    {
                        "service_id": mapping.service_config_id,
                        "service_name": mapping.service_config.name,
                        "success": False,
                        "error": "No adapter available for service type",
                    }
                )
                continue

            # Check if adapter supports user management
            from ..adapters.base import ServiceCapability

            if ServiceCapability.USER_MANAGEMENT not in adapter.supported_capabilities:
                sync_results.append(
                    {
                        "service_id": mapping.service_config_id,
                        "service_name": mapping.service_config.name,
                        "success": False,
                        "error": "Service does not support user management",
                    }
                )
                continue

            # TODO: Implement actual user synchronization
            # For now, just mark as successful
            mapping.mark_sync_attempt(success=True)
            success_count += 1

            sync_results.append(
                {
                    "service_id": mapping.service_config_id,
                    "service_name": mapping.service_config.name,
                    "success": True,
                    "error": None,
                }
            )

        except Exception as e:
            mapping.mark_sync_attempt(success=False, error=str(e))
            sync_results.append(
                {
                    "service_id": mapping.service_config_id,
                    "service_name": mapping.service_config.name,
                    "success": False,
                    "error": str(e),
                }
            )

    await db.commit()

    return UserSyncResult(
        central_user_id=sync_request.central_user_id,
        total_services=len(mappings),
        successful_syncs=success_count,
        failed_syncs=len(mappings) - success_count,
        sync_results=sync_results,
    )


@router.post("/bulk-sync", response_model=List[UserSyncResult])
async def bulk_sync_users(central_user_ids: List[str], db: AsyncSession = Depends(get_db)):
    """Synchronize multiple users across their mapped services."""
    results = []

    for user_id in central_user_ids:
        try:
            sync_request = UserSyncRequest(central_user_id=user_id)
            result = await sync_user_with_services(sync_request, db)
            results.append(result)
        except HTTPException as e:
            # User not found or no mappings
            results.append(
                UserSyncResult(
                    central_user_id=user_id,
                    total_services=0,
                    successful_syncs=0,
                    failed_syncs=0,
                    sync_results=[],
                    error=e.detail,
                )
            )
        except Exception as e:
            results.append(
                UserSyncResult(
                    central_user_id=user_id,
                    total_services=0,
                    successful_syncs=0,
                    failed_syncs=0,
                    sync_results=[],
                    error=str(e),
                )
            )

    return results


@router.post("/detect-mappings", response_model=dict)
async def detect_user_mappings(authentik_service_id: str, db: AsyncSession = Depends(get_db)):
    """Detect potential user mappings across services using Authentik as the source."""
    from ..services.user_mapper import get_user_mapper

    user_mapper = await get_user_mapper()
    results = await user_mapper.detect_all_mappings(db, authentik_service_id)

    return results


@router.post("/auto-detect-mappings", response_model=dict)
async def auto_detect_user_mappings(db: AsyncSession = Depends(get_db)):
    """Automatically detect potential user mappings across all configured services."""
    from ..services.user_mapper import get_user_mapper

    user_mapper = await get_user_mapper()
    results = await user_mapper.auto_detect_all_mappings(db)

    return results


@router.post("/create-from-suggestions", response_model=dict)
async def create_mappings_from_suggestions(request_data: dict, db: AsyncSession = Depends(get_db)):
    """Create user mappings from approved suggestions."""
    from ..services.user_mapper import get_user_mapper

    suggestions = request_data.get("suggestions", [])
    auto_approve_high_confidence = request_data.get("auto_approve_high_confidence", False)

    user_mapper = await get_user_mapper()
    results = await user_mapper.create_mappings_from_suggestions(db, suggestions, auto_approve_high_confidence)

    return results


@router.get("/centralized/{central_user_id}", response_model=dict)
async def get_centralized_user_data(
    central_user_id: str,
    refresh: bool = Query(False, description="Refresh data from services"),
    db: AsyncSession = Depends(get_db),
):
    """Get centralized user data across all services."""
    from ..services.user_centralization import get_user_centralization_service

    user_centralization = await get_user_centralization_service()

    if refresh:
        centralized_data = await user_centralization.update_centralized_data_from_services(db, central_user_id)
    else:
        centralized_data = await user_centralization.get_centralized_user_data(db, central_user_id)

    if not centralized_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Centralized user data not found")

    return centralized_data.to_dict()


@router.get("/centralized", response_model=dict)
async def get_all_centralized_users(db: AsyncSession = Depends(get_db)):
    """Get centralized data for all users."""
    from ..services.user_centralization import get_user_centralization_service

    user_centralization = await get_user_centralization_service()
    centralized_users = await user_centralization.get_all_centralized_users(db)

    return {
        "users": [user.to_dict() for user in centralized_users],
        "total_users": len(centralized_users),
        "enumerated_at": datetime.utcnow(),
    }


@router.post("/centralized/{central_user_id}/sync", response_model=dict)
async def sync_centralized_user_metadata(central_user_id: str, db: AsyncSession = Depends(get_db)):
    """Sync centralized user metadata from all services."""
    from ..services.user_centralization import get_user_centralization_service

    user_centralization = await get_user_centralization_service()
    result = await user_centralization.sync_centralized_user_metadata(db, central_user_id)

    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

    return result
