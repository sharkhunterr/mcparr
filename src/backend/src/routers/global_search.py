"""Global Search configuration API routes."""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db_session
from ..models.configuration import ConfigurationSetting
from ..models.global_search import SEARCHABLE_SERVICES, GlobalSearchConfig
from ..models.service_config import ServiceConfig

router = APIRouter(prefix="/api/global-search", tags=["global-search"])

# Default settings keys
GLOBAL_SEARCH_ENABLED_KEY = "global_search.enabled"
GLOBAL_SEARCH_HIDE_NOTIFICATIONS_KEY = "global_search.hide_notifications"


# Pydantic schemas for API
class SearchableServiceResponse(BaseModel):
    """Response for a service with search capability."""

    service_id: str
    service_name: str
    service_type: str
    search_tool: str
    enabled_for_global_search: bool
    priority: int
    service_enabled: bool

    class Config:
        from_attributes = True


class GlobalSearchConfigUpdate(BaseModel):
    """Request to update global search config for a service."""

    enabled: bool
    priority: Optional[int] = None


class GlobalSearchConfigResponse(BaseModel):
    """Response for global search configuration."""

    id: str
    service_config_id: str
    enabled: bool
    priority: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GlobalSearchSettingsResponse(BaseModel):
    """Response for global search global settings."""

    enabled: bool
    hide_notifications: bool


class GlobalSearchSettingsUpdate(BaseModel):
    """Request to update global search settings."""

    enabled: Optional[bool] = None
    hide_notifications: Optional[bool] = None


@router.get("/services", response_model=List[SearchableServiceResponse])
async def get_searchable_services(db: AsyncSession = Depends(get_db_session)):
    """Get all services that have search capability with their global search configuration."""

    # Get all services
    result = await db.execute(select(ServiceConfig))
    services = result.scalars().all()

    # Get all global search configs
    config_result = await db.execute(select(GlobalSearchConfig))
    configs = {cfg.service_config_id: cfg for cfg in config_result.scalars().all()}

    searchable_services = []
    for service in services:
        service_type = (
            service.service_type.value if hasattr(service.service_type, "value") else str(service.service_type)
        )
        service_type_lower = service_type.lower()

        # Check if this service type has search capability
        if service_type_lower in SEARCHABLE_SERVICES:
            search_info = SEARCHABLE_SERVICES[service_type_lower]
            config = configs.get(service.id)

            searchable_services.append(
                SearchableServiceResponse(
                    service_id=service.id,
                    service_name=service.name,
                    service_type=service_type,
                    search_tool=search_info["tool"],
                    enabled_for_global_search=config.enabled if config else True,  # Default to enabled
                    priority=config.priority if config else 0,
                    service_enabled=service.enabled,
                )
            )

    # Sort by priority (lower first), then by service name
    searchable_services.sort(key=lambda s: (s.priority, s.service_name))

    return searchable_services


@router.get("/config", response_model=List[GlobalSearchConfigResponse])
async def get_global_search_configs(db: AsyncSession = Depends(get_db_session)):
    """Get all global search configurations."""

    result = await db.execute(select(GlobalSearchConfig).order_by(GlobalSearchConfig.priority))
    configs = result.scalars().all()

    return [GlobalSearchConfigResponse.model_validate(cfg) for cfg in configs]


@router.put("/config/{service_id}", response_model=GlobalSearchConfigResponse)
async def update_global_search_config(
    service_id: str,
    config_update: GlobalSearchConfigUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update or create global search configuration for a service."""

    # Verify service exists
    service_result = await db.execute(select(ServiceConfig).where(ServiceConfig.id == service_id))
    service = service_result.scalar_one_or_none()

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    # Check if service type is searchable
    service_type = service.service_type.value if hasattr(service.service_type, "value") else str(service.service_type)
    if service_type.lower() not in SEARCHABLE_SERVICES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Service type '{service_type}' does not have search capability",
        )

    # Get or create config
    config_result = await db.execute(
        select(GlobalSearchConfig).where(GlobalSearchConfig.service_config_id == service_id)
    )
    config = config_result.scalar_one_or_none()

    if config:
        # Update existing config
        config.enabled = config_update.enabled
        if config_update.priority is not None:
            config.priority = config_update.priority
        config.updated_at = datetime.utcnow()
    else:
        # Create new config
        config = GlobalSearchConfig(
            id=str(uuid4()),
            service_config_id=service_id,
            enabled=config_update.enabled,
            priority=config_update.priority or 0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(config)

    await db.commit()
    await db.refresh(config)

    return GlobalSearchConfigResponse.model_validate(config)


@router.delete("/config/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_global_search_config(
    service_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete global search configuration for a service (resets to default enabled)."""

    config_result = await db.execute(
        select(GlobalSearchConfig).where(GlobalSearchConfig.service_config_id == service_id)
    )
    config = config_result.scalar_one_or_none()

    if config:
        await db.delete(config)
        await db.commit()


async def _get_or_create_setting(
    db: AsyncSession, key: str, default_value: str, description: str
) -> ConfigurationSetting:
    """Get or create a configuration setting."""
    result = await db.execute(select(ConfigurationSetting).where(ConfigurationSetting.key == key))
    setting = result.scalar_one_or_none()

    if not setting:
        from sqlalchemy.exc import IntegrityError

        try:
            setting = ConfigurationSetting(
                id=str(uuid4()),
                category="global_search",
                key=key,
                value=default_value,
                value_type="boolean",
                default_value=default_value,
                description=description,
                is_sensitive=False,
                requires_restart=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(setting)
            await db.commit()
            await db.refresh(setting)
        except IntegrityError:
            # Race condition: another request created the setting, fetch it
            await db.rollback()
            result = await db.execute(select(ConfigurationSetting).where(ConfigurationSetting.key == key))
            setting = result.scalar_one()

    return setting


@router.get("/settings", response_model=GlobalSearchSettingsResponse)
async def get_global_search_settings(db: AsyncSession = Depends(get_db_session)):
    """Get global search feature settings."""

    enabled_setting = await _get_or_create_setting(
        db, GLOBAL_SEARCH_ENABLED_KEY, "true", "Enable or disable the global search feature"
    )

    hide_notifications_setting = await _get_or_create_setting(
        db,
        GLOBAL_SEARCH_HIDE_NOTIFICATIONS_KEY,
        "false",
        "Hide global search notification banners on Tools and Services pages",
    )

    return GlobalSearchSettingsResponse(
        enabled=enabled_setting.value.lower() == "true",
        hide_notifications=hide_notifications_setting.value.lower() == "true",
    )


@router.put("/settings", response_model=GlobalSearchSettingsResponse)
async def update_global_search_settings(
    settings_update: GlobalSearchSettingsUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update global search feature settings."""

    if settings_update.enabled is not None:
        enabled_setting = await _get_or_create_setting(
            db, GLOBAL_SEARCH_ENABLED_KEY, "true", "Enable or disable the global search feature"
        )
        enabled_setting.value = "true" if settings_update.enabled else "false"
        enabled_setting.updated_at = datetime.utcnow()

    if settings_update.hide_notifications is not None:
        hide_setting = await _get_or_create_setting(
            db,
            GLOBAL_SEARCH_HIDE_NOTIFICATIONS_KEY,
            "false",
            "Hide global search notification banners on Tools and Services pages",
        )
        hide_setting.value = "true" if settings_update.hide_notifications else "false"
        hide_setting.updated_at = datetime.utcnow()

    await db.commit()

    # Fetch updated values
    enabled_result = await db.execute(
        select(ConfigurationSetting).where(ConfigurationSetting.key == GLOBAL_SEARCH_ENABLED_KEY)
    )
    enabled = enabled_result.scalar_one()

    hide_result = await db.execute(
        select(ConfigurationSetting).where(ConfigurationSetting.key == GLOBAL_SEARCH_HIDE_NOTIFICATIONS_KEY)
    )
    hide = hide_result.scalar_one()

    return GlobalSearchSettingsResponse(
        enabled=enabled.value.lower() == "true",
        hide_notifications=hide.value.lower() == "true",
    )
