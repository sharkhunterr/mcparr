"""Configuration management endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db_session
from src.models.configuration import ConfigurationSetting
from src.utils.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/api/v1/config")


class ConfigurationSettingResponse(BaseModel):
    """Configuration setting response model."""

    id: str
    category: str
    key: str
    value: str
    value_type: str
    default_value: str
    description: str
    is_sensitive: bool
    requires_restart: bool
    updated_at: str
    updated_by: Optional[str] = None

    @classmethod
    def from_orm(cls, setting: ConfigurationSetting):
        return cls(
            id=str(setting.id),
            category=setting.category,
            key=setting.key,
            value=setting.display_value,  # Use display_value for masking
            value_type=setting.value_type,
            default_value=setting.default_value,
            description=setting.description,
            is_sensitive=setting.is_sensitive,
            requires_restart=setting.requires_restart,
            updated_at=setting.updated_at.isoformat(),
            updated_by=setting.updated_by,
        )


class ConfigurationUpdateRequest(BaseModel):
    """Configuration update request."""

    updates: Dict[str, str]


class ConfigurationResponse(BaseModel):
    """Configuration update response."""

    updated: int
    errors: List[Dict[str, str]]
    restart_required: bool


class ConfigurationBackup(BaseModel):
    """Configuration backup model."""

    version: str
    created_at: str
    settings: List[Dict[str, Any]]


@router.get("/", response_model=List[ConfigurationSettingResponse])
async def get_configuration_settings(
    category: Optional[str] = Query(None, description="Filter by category"), db: AsyncSession = Depends(get_db_session)
) -> List[ConfigurationSettingResponse]:
    """Get all configuration settings with optional category filter."""

    logger.info(
        "Configuration settings requested",
        extra={"component": "config", "action": "list_settings", "category": category},
    )

    try:
        # Build query
        query = select(ConfigurationSetting)
        if category:
            query = query.where(ConfigurationSetting.category == category)

        query = query.order_by(ConfigurationSetting.category, ConfigurationSetting.key)

        result = await db.execute(query)
        settings = result.scalars().all()

        response = [ConfigurationSettingResponse.from_orm(setting) for setting in settings]

        logger.info(
            f"Retrieved {len(response)} configuration settings",
            extra={"component": "config", "action": "settings_retrieved", "count": len(response), "category": category},
        )

        return response

    except Exception as e:
        logger.error(
            f"Failed to retrieve configuration settings: {str(e)}",
            extra={"component": "config", "action": "list_settings_error", "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve configuration settings") from e


@router.put("/", response_model=ConfigurationResponse)
async def update_configuration_settings(
    request: ConfigurationUpdateRequest, db: AsyncSession = Depends(get_db_session)
) -> ConfigurationResponse:
    """Update multiple configuration settings."""

    logger.info(
        f"Configuration update requested for {len(request.updates)} settings",
        extra={"component": "config", "action": "update_settings", "settings_count": len(request.updates)},
    )

    updated_count = 0
    errors = []
    restart_required = False

    try:
        for key, value in request.updates.items():
            try:
                # Find setting by key
                query = select(ConfigurationSetting).where(ConfigurationSetting.key == key)
                result = await db.execute(query)
                setting = result.scalar_one_or_none()

                if not setting:
                    errors.append({"key": key, "message": f"Configuration setting '{key}' not found"})
                    continue

                # Validate value
                if not setting.validate_value(value):
                    errors.append({"key": key, "message": f"Invalid value for setting '{key}'"})
                    continue

                # Update setting
                setting.value = value
                setting.updated_by = "admin"  # Would get from auth context
                updated_count += 1

                if setting.requires_restart:
                    restart_required = True

                logger.info(
                    f"Updated configuration setting: {key}",
                    extra={
                        "component": "config",
                        "action": "setting_updated",
                        "key": key,
                        "requires_restart": setting.requires_restart,
                    },
                )

            except Exception as e:
                errors.append({"key": key, "message": str(e)})
                logger.error(
                    f"Failed to update setting {key}: {str(e)}",
                    extra={"component": "config", "action": "setting_update_error", "key": key, "error": str(e)},
                )

        # Commit changes
        await db.commit()

        response = ConfigurationResponse(updated=updated_count, errors=errors, restart_required=restart_required)

        logger.info(
            f"Configuration update completed: {updated_count} updated, {len(errors)} errors",
            extra={
                "component": "config",
                "action": "update_completed",
                "updated": updated_count,
                "errors": len(errors),
                "restart_required": restart_required,
            },
        )

        return response

    except Exception as e:
        await db.rollback()
        logger.error(
            f"Configuration update failed: {str(e)}",
            extra={"component": "config", "action": "update_failed", "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to update configuration settings") from e


@router.get("/backup", response_model=ConfigurationBackup)
async def export_configuration_backup(db: AsyncSession = Depends(get_db_session)) -> ConfigurationBackup:
    """Export complete configuration as backup."""

    logger.info("Configuration backup requested", extra={"component": "config", "action": "backup_export"})

    try:
        # Get all settings
        query = select(ConfigurationSetting).order_by(ConfigurationSetting.category, ConfigurationSetting.key)
        result = await db.execute(query)
        settings = result.scalars().all()

        # Convert to backup format
        settings_data = []
        for setting in settings:
            settings_data.append(
                {
                    "category": setting.category,
                    "key": setting.key,
                    "value": setting.value,  # Full value for backup
                    "value_type": setting.value_type,
                    "default_value": setting.default_value,
                    "description": setting.description,
                    "is_sensitive": setting.is_sensitive,
                    "requires_restart": setting.requires_restart,
                }
            )

        backup = ConfigurationBackup(
            version="1.0", created_at=str(datetime.utcnow().isoformat()), settings=settings_data
        )

        logger.info(
            f"Configuration backup created with {len(settings_data)} settings",
            extra={"component": "config", "action": "backup_created", "settings_count": len(settings_data)},
        )

        return backup

    except Exception as e:
        logger.error(
            f"Configuration backup failed: {str(e)}",
            extra={"component": "config", "action": "backup_failed", "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to create configuration backup") from e


@router.post("/backup", response_model=ConfigurationResponse)
async def restore_configuration_backup(
    backup: ConfigurationBackup, db: AsyncSession = Depends(get_db_session)
) -> ConfigurationResponse:
    """Restore configuration from backup."""

    logger.info(
        f"Configuration restore requested with {len(backup.settings)} settings",
        extra={"component": "config", "action": "backup_restore", "settings_count": len(backup.settings)},
    )

    updated_count = 0
    errors = []
    restart_required = False

    try:
        for setting_data in backup.settings:
            try:
                # Find existing setting
                query = select(ConfigurationSetting).where(ConfigurationSetting.key == setting_data["key"])
                result = await db.execute(query)
                setting = result.scalar_one_or_none()

                if setting:
                    # Update existing
                    setting.value = setting_data["value"]
                    setting.updated_by = "backup_restore"
                    if setting.requires_restart:
                        restart_required = True
                    updated_count += 1

            except Exception as e:
                errors.append({"key": setting_data.get("key", "unknown"), "message": str(e)})

        await db.commit()

        response = ConfigurationResponse(updated=updated_count, errors=errors, restart_required=restart_required)

        logger.info(
            f"Configuration restore completed: {updated_count} restored",
            extra={
                "component": "config",
                "action": "restore_completed",
                "updated": updated_count,
                "errors": len(errors),
            },
        )

        return response

    except Exception as e:
        await db.rollback()
        logger.error(
            f"Configuration restore failed: {str(e)}",
            extra={"component": "config", "action": "restore_failed", "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to restore configuration") from e
