"""Complete site backup/restore endpoints."""

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.connection import get_db_session
from src.models.configuration import ConfigurationSetting
from src.models.group import Group, GroupMembership, GroupToolPermission
from src.models.service_config import ServiceConfig
from src.models.training_prompt import PromptTemplate, TrainingPrompt
from src.models.training_worker import TrainingWorker
from src.models.user_mapping import UserMapping
from src.utils.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/api/backup", tags=["backup"])


class ExportOptions(BaseModel):
    """Options for what to include in export."""

    services: bool = Field(default=True, description="Include service configurations")
    user_mappings: bool = Field(default=True, description="Include user mappings")
    groups: bool = Field(default=True, description="Include groups and permissions")
    site_config: bool = Field(default=True, description="Include site configuration")
    training_prompts: bool = Field(default=True, description="Include AI training prompts")
    prompt_templates: bool = Field(default=True, description="Include prompt templates")
    training_workers: bool = Field(default=True, description="Include training worker configurations")


class ExportResponse(BaseModel):
    """Complete export response."""

    version: str
    exported_at: str
    app_name: str = "mcparr-ai-gateway"
    options: ExportOptions
    data: Dict[str, Any]
    stats: Dict[str, int]


class ImportOptions(BaseModel):
    """Options for what to import."""

    services: bool = Field(default=True, description="Import service configurations")
    user_mappings: bool = Field(default=True, description="Import user mappings")
    groups: bool = Field(default=True, description="Import groups and permissions")
    site_config: bool = Field(default=True, description="Import site configuration")
    training_prompts: bool = Field(default=True, description="Import AI training prompts")
    prompt_templates: bool = Field(default=True, description="Import prompt templates")
    training_workers: bool = Field(default=True, description="Import training worker configurations")
    merge_mode: bool = Field(default=False, description="Merge with existing data instead of replacing")


class ImportRequest(BaseModel):
    """Import request with data and options."""

    version: str
    data: Dict[str, Any]
    options: ImportOptions = Field(default_factory=ImportOptions)


class ImportResult(BaseModel):
    """Result of import operation."""

    success: bool
    imported: Dict[str, int]
    errors: List[Dict[str, str]]
    warnings: List[str]


@router.post("/export", response_model=ExportResponse)
async def export_configuration(
    options: ExportOptions = ExportOptions(), db: AsyncSession = Depends(get_db_session)
) -> ExportResponse:
    """Export complete site configuration based on selected options."""
    logger.info(f"Configuration export requested with options: {options.model_dump()}")

    data = {}
    stats = {}

    try:
        # Export services
        if options.services:
            result = await db.execute(select(ServiceConfig))
            services = result.scalars().all()
            data["services"] = [
                {
                    "name": s.name,
                    "service_type": s.service_type.value if hasattr(s.service_type, "value") else str(s.service_type),
                    "base_url": s.base_url,
                    "external_url": s.external_url,
                    "api_key": s.api_key,  # Note: sensitive data included
                    "enabled": s.enabled,
                    "config": s.config or {},
                    "description": s.description,
                    "port": s.port,
                    "username": s.username,
                    "password": s.password,
                    "health_check_enabled": s.health_check_enabled,
                    "health_check_interval": s.health_check_interval,
                }
                for s in services
            ]
            stats["services"] = len(data["services"])

        # Export user mappings
        if options.user_mappings:
            result = await db.execute(select(UserMapping).options(selectinload(UserMapping.service_config)))
            mappings = result.scalars().all()
            data["user_mappings"] = [
                {
                    "central_user_id": m.central_user_id,
                    "central_username": m.central_username,
                    "central_email": m.central_email,
                    "service_type": m.service_config.service_type.value
                    if m.service_config and hasattr(m.service_config.service_type, "value")
                    else None,
                    "service_name": m.service_config.name if m.service_config else None,
                    "service_user_id": m.service_user_id,
                    "service_username": m.service_username,
                    "service_email": m.service_email,
                    "role": m.role.value if hasattr(m.role, "value") else str(m.role),
                    "status": m.status.value if hasattr(m.status, "value") else str(m.status),
                }
                for m in mappings
            ]
            stats["user_mappings"] = len(data["user_mappings"])

        # Export groups with memberships and permissions
        if options.groups:
            result = await db.execute(
                select(Group).options(selectinload(Group.memberships), selectinload(Group.tool_permissions))
            )
            groups = result.scalars().all()
            data["groups"] = [
                {
                    "name": g.name,
                    "description": g.description,
                    "color": g.color,
                    "priority": g.priority,
                    "enabled": g.enabled,
                    "memberships": [
                        {
                            "central_user_id": m.central_user_id,
                            "enabled": m.enabled,
                            "granted_by": m.granted_by,
                        }
                        for m in g.memberships
                    ],
                    "tool_permissions": [
                        {
                            "tool_name": p.tool_name,
                            "service_type": p.service_type,
                            "enabled": p.enabled,
                            "description": p.description,
                        }
                        for p in g.tool_permissions
                    ],
                }
                for g in groups
            ]
            stats["groups"] = len(data["groups"])
            stats["group_memberships"] = sum(len(g.memberships) for g in groups)
            stats["group_permissions"] = sum(len(g.tool_permissions) for g in groups)

        # Export site configuration
        if options.site_config:
            result = await db.execute(select(ConfigurationSetting))
            settings = result.scalars().all()
            data["site_config"] = [
                {
                    "category": s.category,
                    "key": s.key,
                    "value": s.value,
                    "value_type": s.value_type,
                    "default_value": s.default_value,
                    "description": s.description,
                    "is_sensitive": s.is_sensitive,
                    "requires_restart": s.requires_restart,
                }
                for s in settings
            ]
            stats["site_config"] = len(data["site_config"])

        # Export training prompts
        if options.training_prompts:
            result = await db.execute(select(TrainingPrompt))
            prompts = result.scalars().all()
            data["training_prompts"] = [
                {
                    "name": p.name,
                    "description": p.description,
                    "category": p.category.value if hasattr(p.category, "value") else str(p.category),
                    "difficulty": p.difficulty.value if hasattr(p.difficulty, "value") else str(p.difficulty),
                    "source": p.source.value if hasattr(p.source, "value") else str(p.source),
                    "format": p.format.value if hasattr(p.format, "value") else str(p.format),
                    "content": p.content or {},
                    "system_prompt": p.system_prompt,
                    "user_input": p.user_input,
                    "expected_output": p.expected_output,
                    "tool_call": p.tool_call,
                    "tool_response": p.tool_response,
                    "assistant_response": p.assistant_response,
                    "tags": p.tags or [],
                    "is_validated": p.is_validated,
                    "validation_score": p.validation_score,
                    "validated_by": p.validated_by,
                    "times_used": p.times_used,
                    "enabled": p.enabled,
                }
                for p in prompts
            ]
            stats["training_prompts"] = len(data["training_prompts"])

        # Export prompt templates
        if options.prompt_templates:
            result = await db.execute(select(PromptTemplate))
            templates = result.scalars().all()
            data["prompt_templates"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "system_template": t.system_template,
                    "user_template": t.user_template,
                    "assistant_template": t.assistant_template,
                    "variables": t.variables or [],
                    "category": t.category.value if hasattr(t.category, "value") else str(t.category),
                    "format": t.format.value if hasattr(t.format, "value") else str(t.format),
                    "enabled": t.enabled,
                    "times_used": t.times_used,
                }
                for t in templates
            ]
            stats["prompt_templates"] = len(data["prompt_templates"])

        # Export training workers
        if options.training_workers:
            result = await db.execute(select(TrainingWorker))
            workers = result.scalars().all()
            data["training_workers"] = [
                {
                    "name": w.name,
                    "description": w.description,
                    "url": w.url,
                    "api_key": w.api_key,
                    "enabled": w.enabled,
                    "ollama_service_id": w.ollama_service_id,
                    # Don't export volatile status fields like gpu_*, last_seen_at, etc.
                }
                for w in workers
            ]
            stats["training_workers"] = len(data["training_workers"])

        response = ExportResponse(
            version="1.0", exported_at=datetime.utcnow().isoformat(), options=options, data=data, stats=stats
        )

        logger.info(f"Configuration export completed: {stats}")

        return response

    except Exception as e:
        logger.error(f"Configuration export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}") from e


@router.post("/import", response_model=ImportResult)
async def import_configuration(request: ImportRequest, db: AsyncSession = Depends(get_db_session)) -> ImportResult:
    """Import configuration from backup file."""
    logger.info(f"Configuration import requested with options: {request.options.model_dump()}")

    imported = {}
    errors = []
    warnings = []

    try:
        # Import services
        if request.options.services and "services" in request.data:
            count = 0
            for service_data in request.data["services"]:
                try:
                    # Check if service exists by name
                    existing = await db.execute(select(ServiceConfig).where(ServiceConfig.name == service_data["name"]))
                    existing_service = existing.scalar_one_or_none()

                    if existing_service:
                        if request.options.merge_mode:
                            # Update existing service
                            for key, value in service_data.items():
                                if key != "name" and hasattr(existing_service, key):
                                    setattr(existing_service, key, value)
                            count += 1
                        else:
                            warnings.append(f"Service '{service_data['name']}' already exists, skipped")
                    else:
                        # Create new service
                        from src.models.service_config import ServiceType

                        service = ServiceConfig(
                            name=service_data["name"],
                            service_type=ServiceType(service_data["service_type"]),
                            base_url=service_data["base_url"],
                            external_url=service_data.get("external_url"),
                            api_key=service_data.get("api_key"),
                            enabled=service_data.get("enabled", True),
                            config=service_data.get("config", {}),
                            description=service_data.get("description"),
                            port=service_data.get("port"),
                            username=service_data.get("username"),
                            password=service_data.get("password"),
                            health_check_enabled=service_data.get("health_check_enabled", True),
                            health_check_interval=service_data.get("health_check_interval", 300),
                        )
                        db.add(service)
                        count += 1
                except Exception as e:
                    errors.append({"type": "service", "name": service_data.get("name", "unknown"), "error": str(e)})

            imported["services"] = count

        # Import groups first (before user mappings since memberships reference users)
        if request.options.groups and "groups" in request.data:
            group_count = 0
            membership_count = 0
            permission_count = 0

            for group_data in request.data["groups"]:
                try:
                    # Check if group exists
                    existing = await db.execute(select(Group).where(Group.name == group_data["name"]))
                    existing_group = existing.scalar_one_or_none()

                    if existing_group:
                        if request.options.merge_mode:
                            # Update existing group
                            existing_group.description = group_data.get("description", "")
                            existing_group.color = group_data.get("color", "#6b7280")
                            existing_group.priority = group_data.get("priority", 0)
                            existing_group.enabled = group_data.get("enabled", True)
                            group = existing_group
                            group_count += 1
                        else:
                            warnings.append(f"Group '{group_data['name']}' already exists, skipped")
                            continue
                    else:
                        group = Group(
                            name=group_data["name"],
                            description=group_data.get("description", ""),
                            color=group_data.get("color", "#6b7280"),
                            priority=group_data.get("priority", 0),
                            enabled=group_data.get("enabled", True),
                        )
                        db.add(group)
                        await db.flush()  # Get group ID
                        group_count += 1

                    # Import memberships
                    for member_data in group_data.get("memberships", []):
                        try:
                            existing_member = await db.execute(
                                select(GroupMembership).where(
                                    GroupMembership.group_id == group.id,
                                    GroupMembership.central_user_id == member_data["central_user_id"],
                                )
                            )
                            if not existing_member.scalar_one_or_none():
                                membership = GroupMembership(
                                    group_id=group.id,
                                    central_user_id=member_data["central_user_id"],
                                    enabled=member_data.get("enabled", True),
                                    granted_by=member_data.get("granted_by"),
                                )
                                db.add(membership)
                                membership_count += 1
                        except Exception as e:
                            errors.append({"type": "membership", "group": group_data["name"], "error": str(e)})

                    # Import tool permissions
                    for perm_data in group_data.get("tool_permissions", []):
                        try:
                            existing_perm = await db.execute(
                                select(GroupToolPermission).where(
                                    GroupToolPermission.group_id == group.id,
                                    GroupToolPermission.tool_name == perm_data["tool_name"],
                                )
                            )
                            if not existing_perm.scalar_one_or_none():
                                permission = GroupToolPermission(
                                    group_id=group.id,
                                    tool_name=perm_data["tool_name"],
                                    service_type=perm_data.get("service_type"),
                                    enabled=perm_data.get("enabled", True),
                                    description=perm_data.get("description"),
                                )
                                db.add(permission)
                                permission_count += 1
                        except Exception as e:
                            errors.append({"type": "permission", "group": group_data["name"], "error": str(e)})

                except Exception as e:
                    errors.append({"type": "group", "name": group_data.get("name", "unknown"), "error": str(e)})

            imported["groups"] = group_count
            imported["memberships"] = membership_count
            imported["permissions"] = permission_count

        # Import user mappings
        if request.options.user_mappings and "user_mappings" in request.data:
            count = 0
            for mapping_data in request.data["user_mappings"]:
                try:
                    # Find service by name
                    if mapping_data.get("service_name"):
                        service_result = await db.execute(
                            select(ServiceConfig).where(ServiceConfig.name == mapping_data["service_name"])
                        )
                        service = service_result.scalar_one_or_none()

                        if not service:
                            warnings.append(f"Service '{mapping_data['service_name']}' not found for mapping")
                            continue

                        # Check if mapping exists
                        existing = await db.execute(
                            select(UserMapping).where(
                                UserMapping.central_user_id == mapping_data["central_user_id"],
                                UserMapping.service_config_id == service.id,
                            )
                        )
                        if not existing.scalar_one_or_none():
                            from src.models.user_mapping import MappingStatus, UserRole

                            mapping = UserMapping(
                                central_user_id=mapping_data["central_user_id"],
                                central_username=mapping_data.get("central_username"),
                                central_email=mapping_data.get("central_email"),
                                service_config_id=service.id,
                                service_user_id=mapping_data.get("service_user_id"),
                                service_username=mapping_data.get("service_username"),
                                service_email=mapping_data.get("service_email"),
                                role=UserRole(mapping_data.get("role", "user")),
                                status=MappingStatus(mapping_data.get("status", "active")),
                            )
                            db.add(mapping)
                            count += 1
                except Exception as e:
                    errors.append(
                        {
                            "type": "user_mapping",
                            "user": mapping_data.get("central_user_id", "unknown"),
                            "error": str(e),
                        }
                    )

            imported["user_mappings"] = count

        # Import site config
        if request.options.site_config and "site_config" in request.data:
            count = 0
            for config_data in request.data["site_config"]:
                try:
                    existing = await db.execute(
                        select(ConfigurationSetting).where(ConfigurationSetting.key == config_data["key"])
                    )
                    setting = existing.scalar_one_or_none()

                    if setting:
                        setting.value = config_data["value"]
                        setting.updated_by = "import"
                        count += 1
                except Exception as e:
                    errors.append({"type": "config", "key": config_data.get("key", "unknown"), "error": str(e)})

            imported["site_config"] = count

        # Import training prompts
        if request.options.training_prompts and "training_prompts" in request.data:
            count = 0
            for prompt_data in request.data["training_prompts"]:
                try:
                    existing = await db.execute(
                        select(TrainingPrompt).where(TrainingPrompt.name == prompt_data["name"])
                    )
                    if not existing.scalar_one_or_none():
                        from src.models.training_prompt import (
                            PromptCategory,
                            PromptDifficulty,
                            PromptFormat,
                            PromptSource,
                        )

                        prompt = TrainingPrompt(
                            name=prompt_data["name"],
                            description=prompt_data.get("description"),
                            category=PromptCategory(prompt_data.get("category", "general")),
                            difficulty=PromptDifficulty(prompt_data.get("difficulty", "basic")),
                            source=PromptSource(prompt_data.get("source", "manual")),
                            format=PromptFormat(prompt_data.get("format", "chat")),
                            content=prompt_data.get("content", {}),
                            system_prompt=prompt_data.get("system_prompt"),
                            user_input=prompt_data.get("user_input", ""),
                            expected_output=prompt_data.get("expected_output", ""),
                            tool_call=prompt_data.get("tool_call"),
                            tool_response=prompt_data.get("tool_response"),
                            assistant_response=prompt_data.get("assistant_response"),
                            tags=prompt_data.get("tags", []),
                            is_validated=prompt_data.get("is_validated", False),
                            validation_score=prompt_data.get("validation_score"),
                            validated_by=prompt_data.get("validated_by"),
                            times_used=prompt_data.get("times_used", 0),
                            enabled=prompt_data.get("enabled", True),
                        )
                        db.add(prompt)
                        count += 1
                except Exception as e:
                    errors.append(
                        {"type": "training_prompt", "name": prompt_data.get("name", "unknown"), "error": str(e)}
                    )

            imported["training_prompts"] = count

        # Import prompt templates
        if request.options.prompt_templates and "prompt_templates" in request.data:
            count = 0
            for template_data in request.data["prompt_templates"]:
                try:
                    existing = await db.execute(
                        select(PromptTemplate).where(PromptTemplate.name == template_data["name"])
                    )
                    if not existing.scalar_one_or_none():
                        from src.models.training_prompt import PromptCategory, PromptFormat

                        template = PromptTemplate(
                            name=template_data["name"],
                            description=template_data.get("description"),
                            system_template=template_data.get("system_template"),
                            user_template=template_data.get("user_template", ""),
                            assistant_template=template_data.get("assistant_template", ""),
                            variables=template_data.get("variables", []),
                            category=PromptCategory(template_data.get("category", "general")),
                            format=PromptFormat(template_data.get("format", "chat")),
                            enabled=template_data.get("enabled", True),
                            times_used=template_data.get("times_used", 0),
                        )
                        db.add(template)
                        count += 1
                except Exception as e:
                    errors.append(
                        {"type": "prompt_template", "name": template_data.get("name", "unknown"), "error": str(e)}
                    )

            imported["prompt_templates"] = count

        # Import training workers
        if request.options.training_workers and "training_workers" in request.data:
            count = 0
            for worker_data in request.data["training_workers"]:
                try:
                    existing = await db.execute(
                        select(TrainingWorker).where(TrainingWorker.name == worker_data["name"])
                    )
                    existing_worker = existing.scalar_one_or_none()

                    if existing_worker:
                        if request.options.merge_mode:
                            # Update existing worker
                            existing_worker.description = worker_data.get("description")
                            existing_worker.url = worker_data.get("url", existing_worker.url)
                            existing_worker.api_key = worker_data.get("api_key")
                            existing_worker.enabled = worker_data.get("enabled", True)
                            existing_worker.ollama_service_id = worker_data.get("ollama_service_id")
                            count += 1
                        else:
                            warnings.append(f"Training worker '{worker_data['name']}' already exists, skipped")
                    else:
                        worker = TrainingWorker(
                            name=worker_data["name"],
                            description=worker_data.get("description"),
                            url=worker_data.get("url", ""),
                            api_key=worker_data.get("api_key"),
                            enabled=worker_data.get("enabled", True),
                            ollama_service_id=worker_data.get("ollama_service_id"),
                        )
                        db.add(worker)
                        count += 1
                except Exception as e:
                    errors.append(
                        {"type": "training_worker", "name": worker_data.get("name", "unknown"), "error": str(e)}
                    )

            imported["training_workers"] = count

        await db.commit()

        result = ImportResult(success=len(errors) == 0, imported=imported, errors=errors, warnings=warnings)

        logger.info(f"Configuration import completed: {imported}, errors: {len(errors)}")

        return result

    except Exception as e:
        await db.rollback()
        logger.error(f"Configuration import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}") from e


@router.get("/preview")
async def preview_export(
    services: bool = True,
    user_mappings: bool = True,
    groups: bool = True,
    site_config: bool = True,
    training_prompts: bool = True,
    prompt_templates: bool = True,
    training_workers: bool = True,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, int]:
    """Preview what would be exported with the given options."""
    stats = {}

    if services:
        result = await db.execute(select(ServiceConfig))
        stats["services"] = len(result.scalars().all())

    if user_mappings:
        result = await db.execute(select(UserMapping))
        stats["user_mappings"] = len(result.scalars().all())

    if groups:
        result = await db.execute(select(Group))
        stats["groups"] = len(result.scalars().all())

        result = await db.execute(select(GroupMembership))
        stats["group_memberships"] = len(result.scalars().all())

        result = await db.execute(select(GroupToolPermission))
        stats["group_permissions"] = len(result.scalars().all())

    if site_config:
        result = await db.execute(select(ConfigurationSetting))
        stats["site_config"] = len(result.scalars().all())

    if training_prompts:
        result = await db.execute(select(TrainingPrompt))
        stats["training_prompts"] = len(result.scalars().all())

    if prompt_templates:
        result = await db.execute(select(PromptTemplate))
        stats["prompt_templates"] = len(result.scalars().all())

    if training_workers:
        result = await db.execute(select(TrainingWorker))
        stats["training_workers"] = len(result.scalars().all())

    return stats


class ResetAllResult(BaseModel):
    """Result of reset-all operation."""

    success: bool
    deleted: Dict[str, int]
    message: str


@router.post("/reset-all", response_model=ResetAllResult)
async def reset_all_data(db: AsyncSession = Depends(get_db_session)) -> ResetAllResult:
    """Delete all data from the database. This operation is irreversible."""
    logger.warning("Reset all data operation requested - this will delete ALL data")

    deleted = {}

    try:
        # Delete in order to respect foreign key constraints
        # Start with child tables first

        # 1. Delete group memberships and permissions (depend on groups)
        result = await db.execute(delete(GroupMembership))
        deleted["group_memberships"] = result.rowcount

        result = await db.execute(delete(GroupToolPermission))
        deleted["group_permissions"] = result.rowcount

        # 2. Delete groups
        result = await db.execute(delete(Group))
        deleted["groups"] = result.rowcount

        # 3. Delete user mappings (depend on services)
        result = await db.execute(delete(UserMapping))
        deleted["user_mappings"] = result.rowcount

        # 4. Delete services
        result = await db.execute(delete(ServiceConfig))
        deleted["services"] = result.rowcount

        # 5. Delete training data
        result = await db.execute(delete(TrainingPrompt))
        deleted["training_prompts"] = result.rowcount

        result = await db.execute(delete(PromptTemplate))
        deleted["prompt_templates"] = result.rowcount

        result = await db.execute(delete(TrainingWorker))
        deleted["training_workers"] = result.rowcount

        # 6. Delete configuration settings
        result = await db.execute(delete(ConfigurationSetting))
        deleted["configuration_settings"] = result.rowcount

        # Commit all deletions
        await db.commit()

        total_deleted = sum(deleted.values())
        message = f"Successfully deleted all data ({total_deleted} total records)"

        logger.warning(f"Reset all data completed: {deleted}")

        return ResetAllResult(success=True, deleted=deleted, message=message)

    except Exception as e:
        await db.rollback()
        logger.error(f"Reset all data failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}") from e
