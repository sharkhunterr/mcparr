"""Tool Chain management API routes for defining conditional tool execution sequences."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database.connection import get_db_session as get_db
from ..models.tool_chain import (
    ConditionOperator,
    ExecutionMode,
    ToolChain,
    ToolChainStep,
    ToolChainStepTarget,
)
from ..schemas.tool_chains import (
    AvailableTool,
    AvailableToolsResponse,
    ConditionOperatorsResponse,
    StepTargetCreate,
    StepTargetResponse,
    StepTargetUpdate,
    ToolChainCreate,
    ToolChainDetailResponse,
    ToolChainListResponse,
    ToolChainResponse,
    ToolChainStepCreate,
    ToolChainStepDetailResponse,
    ToolChainStepResponse,
    ToolChainStepUpdate,
    ToolChainUpdate,
)

router = APIRouter(prefix="/api/tool-chains", tags=["tool-chains"])


# === Helper functions ===


def _get_service_display_names() -> dict:
    """Get display names for services."""
    return {
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
        "system": "System",
    }


def _enrich_chain_response(chain: ToolChain) -> dict:
    """Enrich a chain response with computed fields."""
    data = {
        "id": str(chain.id),
        "name": chain.name,
        "description": chain.description,
        "color": chain.color,
        "priority": chain.priority,
        "enabled": chain.enabled,
        "created_at": chain.created_at,
        "updated_at": chain.updated_at,
        "step_count": len(chain.steps) if chain.steps else 0,
    }
    return data


def _enrich_step_response(step: ToolChainStep) -> dict:
    """Enrich a step response with computed fields."""
    display_names = _get_service_display_names()
    source_tool_display = step.source_tool.replace("_", " ").replace(
        f"{step.source_service}_", ""
    ).title()

    data = {
        "id": str(step.id),
        "chain_id": str(step.chain_id),
        "order": step.order,
        "source_service": step.source_service,
        "source_tool": step.source_tool,
        "condition_operator": step.condition_operator,
        "condition_field": step.condition_field,
        "condition_value": step.condition_value,
        "ai_comment": step.ai_comment,
        "enabled": step.enabled,
        "created_at": step.created_at,
        "updated_at": step.updated_at,
        "target_count": len(step.target_tools) if step.target_tools else 0,
        "source_service_name": display_names.get(
            step.source_service, step.source_service.capitalize()
        ),
        "source_tool_display_name": source_tool_display,
    }
    return data


def _enrich_target_response(target: ToolChainStepTarget) -> dict:
    """Enrich a target response with computed fields."""
    display_names = _get_service_display_names()
    target_tool_display = target.target_tool.replace("_", " ").replace(
        f"{target.target_service}_", ""
    ).title()

    data = {
        "id": str(target.id),
        "step_id": str(target.step_id),
        "target_service": target.target_service,
        "target_tool": target.target_tool,
        "order": target.order,
        "execution_mode": target.execution_mode,
        "argument_mappings": target.argument_mappings,
        "target_ai_comment": target.target_ai_comment,
        "enabled": target.enabled,
        "created_at": target.created_at,
        "updated_at": target.updated_at,
        "target_service_name": display_names.get(
            target.target_service, target.target_service.capitalize()
        ),
        "target_tool_display_name": target_tool_display,
    }
    return data


# === Reference Data ===


@router.get("/operators", response_model=ConditionOperatorsResponse)
async def get_condition_operators():
    """Get list of available condition operators with descriptions."""
    return ConditionOperatorsResponse()


@router.get("/available-tools", response_model=AvailableToolsResponse)
async def get_available_tools(
    service_type: Optional[str] = Query(None, description="Filter by service type"),
    db: AsyncSession = Depends(get_db),
):
    """Get all available tools for chain configuration.

    Returns tools from all configured services with their parameters.
    """
    from ..routers.openapi_tools import get_tool_registry

    registry = await get_tool_registry(db)
    tools = []
    display_names = _get_service_display_names()

    # Get all tools from the registry
    for tool_def in registry.list_tools():
        svc_type = tool_def.requires_service or "system"

        # Filter by service type if specified
        if service_type and svc_type != service_type:
            continue

        # Create display name from tool name
        tool_display = tool_def.name.replace("_", " ").replace(f"{svc_type}_", "").title()

        # Convert ToolParameter list to dict format
        parameters = {}
        if hasattr(tool_def, "parameters") and tool_def.parameters:
            for param in tool_def.parameters:
                param_info = {
                    "type": param.type,
                    "description": param.description,
                    "required": param.required,
                }
                if param.enum:
                    param_info["enum"] = param.enum
                if param.default is not None:
                    param_info["default"] = param.default
                parameters[param.name] = param_info

        tools.append(
            AvailableTool(
                service_type=svc_type,
                service_name=display_names.get(svc_type, svc_type.capitalize()),
                tool_name=tool_def.name,
                tool_display_name=tool_display,
                description=tool_def.description or "",
                parameters=parameters,
            )
        )

    # Sort by service then tool name
    tools.sort(key=lambda t: (t.service_name, t.tool_display_name))

    return AvailableToolsResponse(tools=tools, total=len(tools))


# === Tool Chain CRUD ===


@router.get("/", response_model=ToolChainListResponse)
async def list_tool_chains(
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: AsyncSession = Depends(get_db),
):
    """List all tool chains with optional filtering."""
    query = select(ToolChain).options(selectinload(ToolChain.steps))

    if enabled is not None:
        query = query.where(ToolChain.enabled == enabled)

    query = query.order_by(ToolChain.priority.desc(), ToolChain.name).offset(skip).limit(limit)

    result = await db.execute(query)
    chains = result.scalars().all()

    # Get total count
    count_query = select(func.count(ToolChain.id))
    if enabled is not None:
        count_query = count_query.where(ToolChain.enabled == enabled)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return ToolChainListResponse(
        chains=[ToolChainResponse(**_enrich_chain_response(c)) for c in chains],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{chain_id}", response_model=ToolChainDetailResponse)
async def get_tool_chain(chain_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific tool chain with all steps and their targets."""
    result = await db.execute(
        select(ToolChain)
        .options(
            selectinload(ToolChain.steps).selectinload(ToolChainStep.target_tools)
        )
        .where(ToolChain.id == chain_id)
    )
    chain = result.scalar_one_or_none()

    if not chain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool chain not found")

    # Build detailed response
    chain_data = _enrich_chain_response(chain)
    chain_data["steps"] = []

    for step in sorted(chain.steps, key=lambda s: s.order):
        step_data = _enrich_step_response(step)
        step_data["targets"] = [
            StepTargetResponse(**_enrich_target_response(t))
            for t in sorted(step.target_tools, key=lambda t: t.order)
        ]
        chain_data["steps"].append(ToolChainStepDetailResponse(**step_data))

    return ToolChainDetailResponse(**chain_data)


@router.post("/", response_model=ToolChainResponse, status_code=status.HTTP_201_CREATED)
async def create_tool_chain(chain_data: ToolChainCreate, db: AsyncSession = Depends(get_db)):
    """Create a new tool chain."""
    # Create chain without steps
    chain_dict = chain_data.model_dump(exclude={"steps"})
    chain = ToolChain(**chain_dict)
    db.add(chain)
    await db.flush()  # Get the ID

    # Add steps if provided
    if chain_data.steps:
        for i, step_data in enumerate(chain_data.steps):
            step_dict = step_data.model_dump(exclude={"targets"})
            step_dict["chain_id"] = chain.id
            step_dict["order"] = step_dict.get("order", i)

            # Convert enums to values
            if isinstance(step_dict.get("condition_operator"), ConditionOperator):
                step_dict["condition_operator"] = step_dict["condition_operator"].value

            step = ToolChainStep(**step_dict)
            db.add(step)
            await db.flush()  # Get step ID for targets

            # Add targets for this step
            if step_data.targets:
                for j, target_data in enumerate(step_data.targets):
                    target_dict = target_data.model_dump()
                    target_dict["step_id"] = step.id
                    target_dict["order"] = target_dict.get("order", j)

                    if isinstance(target_dict.get("execution_mode"), ExecutionMode):
                        target_dict["execution_mode"] = target_dict["execution_mode"].value

                    target = ToolChainStepTarget(**target_dict)
                    db.add(target)

    await db.commit()
    await db.refresh(chain, ["steps"])

    logger.info(f"Created tool chain: {chain.name} ({chain.id})")
    return ToolChainResponse(**_enrich_chain_response(chain))


@router.put("/{chain_id}", response_model=ToolChainResponse)
async def update_tool_chain(chain_id: str, chain_data: ToolChainUpdate, db: AsyncSession = Depends(get_db)):
    """Update an existing tool chain."""
    result = await db.execute(
        select(ToolChain).options(selectinload(ToolChain.steps)).where(ToolChain.id == chain_id)
    )
    chain = result.scalar_one_or_none()

    if not chain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool chain not found")

    # Update fields
    update_data = chain_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(chain, field, value)

    await db.commit()
    await db.refresh(chain)

    logger.info(f"Updated tool chain: {chain.name} ({chain.id})")
    return ToolChainResponse(**_enrich_chain_response(chain))


@router.delete("/{chain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool_chain(chain_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a tool chain and all its steps and targets."""
    result = await db.execute(select(ToolChain).where(ToolChain.id == chain_id))
    chain = result.scalar_one_or_none()

    if not chain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool chain not found")

    await db.delete(chain)
    await db.commit()
    logger.info(f"Deleted tool chain: {chain.name} ({chain.id})")


# === Tool Chain Steps ===


@router.get("/{chain_id}/steps", response_model=List[ToolChainStepDetailResponse])
async def list_chain_steps(
    chain_id: str,
    enabled: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all steps in a tool chain with their targets."""
    # Verify chain exists
    chain_result = await db.execute(select(ToolChain).where(ToolChain.id == chain_id))
    if not chain_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tool chain not found")

    query = (
        select(ToolChainStep)
        .options(selectinload(ToolChainStep.target_tools))
        .where(ToolChainStep.chain_id == chain_id)
    )
    if enabled is not None:
        query = query.where(ToolChainStep.enabled == enabled)

    query = query.order_by(ToolChainStep.order)

    result = await db.execute(query)
    steps = result.scalars().all()

    response = []
    for step in steps:
        step_data = _enrich_step_response(step)
        step_data["targets"] = [
            StepTargetResponse(**_enrich_target_response(t))
            for t in sorted(step.target_tools, key=lambda t: t.order)
        ]
        response.append(ToolChainStepDetailResponse(**step_data))

    return response


@router.post("/{chain_id}/steps", response_model=ToolChainStepDetailResponse, status_code=status.HTTP_201_CREATED)
async def add_chain_step(
    chain_id: str,
    step_data: ToolChainStepCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a step to a tool chain."""
    # Verify chain exists
    chain_result = await db.execute(select(ToolChain).where(ToolChain.id == chain_id))
    if not chain_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tool chain not found")

    step_dict = step_data.model_dump(exclude={"targets"})
    step_dict["chain_id"] = chain_id

    # Convert enums to values
    if isinstance(step_dict.get("condition_operator"), ConditionOperator):
        step_dict["condition_operator"] = step_dict["condition_operator"].value

    step = ToolChainStep(**step_dict)
    db.add(step)
    await db.flush()  # Get step ID for targets

    # Add targets if provided
    if step_data.targets:
        for j, target_data in enumerate(step_data.targets):
            target_dict = target_data.model_dump()
            target_dict["step_id"] = step.id
            target_dict["order"] = target_dict.get("order", j)

            if isinstance(target_dict.get("execution_mode"), ExecutionMode):
                target_dict["execution_mode"] = target_dict["execution_mode"].value

            target = ToolChainStepTarget(**target_dict)
            db.add(target)

    await db.commit()
    await db.refresh(step, ["target_tools"])

    logger.info(f"Added step to chain {chain_id}: {step.source_service}.{step.source_tool}")

    step_data_response = _enrich_step_response(step)
    step_data_response["targets"] = [
        StepTargetResponse(**_enrich_target_response(t))
        for t in sorted(step.target_tools, key=lambda t: t.order)
    ]
    return ToolChainStepDetailResponse(**step_data_response)


@router.get("/{chain_id}/steps/{step_id}", response_model=ToolChainStepDetailResponse)
async def get_chain_step(chain_id: str, step_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific step from a tool chain with its targets."""
    result = await db.execute(
        select(ToolChainStep)
        .options(selectinload(ToolChainStep.target_tools))
        .where(
            and_(ToolChainStep.chain_id == chain_id, ToolChainStep.id == step_id)
        )
    )
    step = result.scalar_one_or_none()

    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    step_data = _enrich_step_response(step)
    step_data["targets"] = [
        StepTargetResponse(**_enrich_target_response(t))
        for t in sorted(step.target_tools, key=lambda t: t.order)
    ]
    return ToolChainStepDetailResponse(**step_data)


@router.put("/{chain_id}/steps/{step_id}", response_model=ToolChainStepDetailResponse)
async def update_chain_step(
    chain_id: str,
    step_id: str,
    step_data: ToolChainStepUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a step in a tool chain."""
    result = await db.execute(
        select(ToolChainStep)
        .options(selectinload(ToolChainStep.target_tools))
        .where(
            and_(ToolChainStep.chain_id == chain_id, ToolChainStep.id == step_id)
        )
    )
    step = result.scalar_one_or_none()

    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    # Update fields
    update_data = step_data.model_dump(exclude_unset=True)

    # Convert enums to values
    if "condition_operator" in update_data and isinstance(update_data["condition_operator"], ConditionOperator):
        update_data["condition_operator"] = update_data["condition_operator"].value

    for field, value in update_data.items():
        setattr(step, field, value)

    await db.commit()
    await db.refresh(step)

    logger.info(f"Updated step {step_id} in chain {chain_id}")

    step_data_response = _enrich_step_response(step)
    step_data_response["targets"] = [
        StepTargetResponse(**_enrich_target_response(t))
        for t in sorted(step.target_tools, key=lambda t: t.order)
    ]
    return ToolChainStepDetailResponse(**step_data_response)


@router.delete("/{chain_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chain_step(chain_id: str, step_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a step from a tool chain (cascade deletes targets)."""
    result = await db.execute(
        select(ToolChainStep).where(
            and_(ToolChainStep.chain_id == chain_id, ToolChainStep.id == step_id)
        )
    )
    step = result.scalar_one_or_none()

    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    await db.delete(step)
    await db.commit()
    logger.info(f"Deleted step {step_id} from chain {chain_id}")


@router.post("/{chain_id}/steps/reorder", response_model=List[ToolChainStepResponse])
async def reorder_chain_steps(
    chain_id: str,
    step_ids: List[str],
    db: AsyncSession = Depends(get_db),
):
    """Reorder steps in a tool chain.

    The step_ids list should contain all step IDs in the desired order.
    """
    # Verify chain exists
    chain_result = await db.execute(select(ToolChain).where(ToolChain.id == chain_id))
    if not chain_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tool chain not found")

    # Get all steps for this chain
    result = await db.execute(
        select(ToolChainStep).where(ToolChainStep.chain_id == chain_id)
    )
    steps = {str(s.id): s for s in result.scalars().all()}

    # Validate all step_ids belong to this chain
    for step_id in step_ids:
        if step_id not in steps:
            raise HTTPException(
                status_code=400,
                detail=f"Step {step_id} not found in chain {chain_id}",
            )

    # Update order
    for new_order, step_id in enumerate(step_ids):
        steps[step_id].order = new_order

    await db.commit()

    # Return updated steps in new order
    ordered_steps = sorted(steps.values(), key=lambda s: s.order)
    logger.info(f"Reordered {len(step_ids)} steps in chain {chain_id}")
    return [ToolChainStepResponse(**_enrich_step_response(s)) for s in ordered_steps]


# === Step Targets ===


@router.get("/{chain_id}/steps/{step_id}/targets", response_model=List[StepTargetResponse])
async def list_step_targets(
    chain_id: str,
    step_id: str,
    enabled: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all targets in a step."""
    # Verify step exists and belongs to chain
    step_result = await db.execute(
        select(ToolChainStep).where(
            and_(ToolChainStep.chain_id == chain_id, ToolChainStep.id == step_id)
        )
    )
    if not step_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Step not found")

    query = select(ToolChainStepTarget).where(ToolChainStepTarget.step_id == step_id)
    if enabled is not None:
        query = query.where(ToolChainStepTarget.enabled == enabled)

    query = query.order_by(ToolChainStepTarget.order)

    result = await db.execute(query)
    targets = result.scalars().all()

    return [StepTargetResponse(**_enrich_target_response(t)) for t in targets]


@router.post(
    "/{chain_id}/steps/{step_id}/targets",
    response_model=StepTargetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_step_target(
    chain_id: str,
    step_id: str,
    target_data: StepTargetCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a target tool to a step."""
    # Verify step exists and belongs to chain
    step_result = await db.execute(
        select(ToolChainStep).where(
            and_(ToolChainStep.chain_id == chain_id, ToolChainStep.id == step_id)
        )
    )
    if not step_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Step not found")

    target_dict = target_data.model_dump()
    target_dict["step_id"] = step_id

    # Convert enums to values
    if isinstance(target_dict.get("execution_mode"), ExecutionMode):
        target_dict["execution_mode"] = target_dict["execution_mode"].value

    target = ToolChainStepTarget(**target_dict)
    db.add(target)
    await db.commit()
    await db.refresh(target)

    logger.info(f"Added target to step {step_id}: {target.target_service}.{target.target_tool}")
    return StepTargetResponse(**_enrich_target_response(target))


@router.get("/{chain_id}/steps/{step_id}/targets/{target_id}", response_model=StepTargetResponse)
async def get_step_target(
    chain_id: str,
    step_id: str,
    target_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific target from a step."""
    # Verify step exists and belongs to chain
    step_result = await db.execute(
        select(ToolChainStep).where(
            and_(ToolChainStep.chain_id == chain_id, ToolChainStep.id == step_id)
        )
    )
    if not step_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Step not found")

    result = await db.execute(
        select(ToolChainStepTarget).where(
            and_(ToolChainStepTarget.step_id == step_id, ToolChainStepTarget.id == target_id)
        )
    )
    target = result.scalar_one_or_none()

    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    return StepTargetResponse(**_enrich_target_response(target))


@router.put("/{chain_id}/steps/{step_id}/targets/{target_id}", response_model=StepTargetResponse)
async def update_step_target(
    chain_id: str,
    step_id: str,
    target_id: str,
    target_data: StepTargetUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a target in a step."""
    # Verify step exists and belongs to chain
    step_result = await db.execute(
        select(ToolChainStep).where(
            and_(ToolChainStep.chain_id == chain_id, ToolChainStep.id == step_id)
        )
    )
    if not step_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Step not found")

    result = await db.execute(
        select(ToolChainStepTarget).where(
            and_(ToolChainStepTarget.step_id == step_id, ToolChainStepTarget.id == target_id)
        )
    )
    target = result.scalar_one_or_none()

    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    # Update fields
    update_data = target_data.model_dump(exclude_unset=True)

    # Convert enums to values
    if "execution_mode" in update_data and isinstance(update_data["execution_mode"], ExecutionMode):
        update_data["execution_mode"] = update_data["execution_mode"].value

    for field, value in update_data.items():
        setattr(target, field, value)

    await db.commit()
    await db.refresh(target)

    logger.info(f"Updated target {target_id} in step {step_id}")
    return StepTargetResponse(**_enrich_target_response(target))


@router.delete("/{chain_id}/steps/{step_id}/targets/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_step_target(
    chain_id: str,
    step_id: str,
    target_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a target from a step."""
    # Verify step exists and belongs to chain
    step_result = await db.execute(
        select(ToolChainStep).where(
            and_(ToolChainStep.chain_id == chain_id, ToolChainStep.id == step_id)
        )
    )
    if not step_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Step not found")

    result = await db.execute(
        select(ToolChainStepTarget).where(
            and_(ToolChainStepTarget.step_id == step_id, ToolChainStepTarget.id == target_id)
        )
    )
    target = result.scalar_one_or_none()

    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    await db.delete(target)
    await db.commit()
    logger.info(f"Deleted target {target_id} from step {step_id}")


@router.post("/{chain_id}/steps/{step_id}/targets/reorder", response_model=List[StepTargetResponse])
async def reorder_step_targets(
    chain_id: str,
    step_id: str,
    target_ids: List[str],
    db: AsyncSession = Depends(get_db),
):
    """Reorder targets in a step.

    The target_ids list should contain all target IDs in the desired order.
    """
    # Verify step exists and belongs to chain
    step_result = await db.execute(
        select(ToolChainStep).where(
            and_(ToolChainStep.chain_id == chain_id, ToolChainStep.id == step_id)
        )
    )
    if not step_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Step not found")

    # Get all targets for this step
    result = await db.execute(
        select(ToolChainStepTarget).where(ToolChainStepTarget.step_id == step_id)
    )
    targets = {str(t.id): t for t in result.scalars().all()}

    # Validate all target_ids belong to this step
    for target_id in target_ids:
        if target_id not in targets:
            raise HTTPException(
                status_code=400,
                detail=f"Target {target_id} not found in step {step_id}",
            )

    # Update order
    for new_order, target_id in enumerate(target_ids):
        targets[target_id].order = new_order

    await db.commit()

    # Return updated targets in new order
    ordered_targets = sorted(targets.values(), key=lambda t: t.order)
    logger.info(f"Reordered {len(target_ids)} targets in step {step_id}")
    return [StepTargetResponse(**_enrich_target_response(t)) for t in ordered_targets]


# === Chain Lookup for Tool Execution ===


@router.get("/lookup/{service_type}/{tool_name}", response_model=List[ToolChainStepDetailResponse])
async def lookup_steps_for_tool(
    service_type: str,
    tool_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Find all enabled steps that trigger from a specific tool.

    Used internally to attach chain information to tool responses.
    Returns steps from enabled chains that have this tool as their source.
    """
    result = await db.execute(
        select(ToolChainStep)
        .options(selectinload(ToolChainStep.target_tools))
        .join(ToolChain)
        .where(
            and_(
                ToolChainStep.source_service == service_type,
                ToolChainStep.source_tool == tool_name,
                ToolChainStep.enabled == True,
                ToolChain.enabled == True,
            )
        )
        .order_by(ToolChain.priority.desc(), ToolChainStep.order)
    )
    steps = result.scalars().all()

    response = []
    for step in steps:
        step_data = _enrich_step_response(step)
        step_data["targets"] = [
            StepTargetResponse(**_enrich_target_response(t))
            for t in sorted(step.target_tools, key=lambda t: t.order)
        ]
        response.append(ToolChainStepDetailResponse(**step_data))

    return response
