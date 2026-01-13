"""Tool Chain management API routes for IF/THEN/ELSE conditional tool execution sequences."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database.connection import get_db_session as get_db
from ..models.tool_chain import (
    ActionType,
    ConditionGroupOperator,
    ConditionOperator,
    ExecutionMode,
    StepPositionType,
    ToolChain,
    ToolChainAction,
    ToolChainCondition,
    ToolChainConditionGroup,
    ToolChainStep,
)
from ..schemas.tool_chains import (
    ActionCreate,
    ActionResponse,
    ActionTypesResponse,
    ActionUpdate,
    AvailableTool,
    AvailableToolsResponse,
    ConditionCreate,
    ConditionGroupCreate,
    ConditionGroupOperatorsResponse,
    ConditionGroupResponse,
    ConditionOperatorsResponse,
    ConditionResponse,
    ConditionUpdate,
    FlowchartEdge,
    FlowchartNode,
    FlowchartResponse,
    StepPositionTypesResponse,
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
    return {
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


def _enrich_step_response(step: ToolChainStep) -> dict:
    """Enrich a step response with computed fields."""
    display_names = _get_service_display_names()
    source_tool_display = step.source_tool.replace("_", " ").replace(
        f"{step.source_service}_", ""
    ).title()

    # Count conditions (recursive through groups)
    condition_count = 0
    if step.condition_groups:
        for group in step.condition_groups:
            condition_count += len(group.conditions) if group.conditions else 0

    # Count then/else actions
    then_count = 0
    else_count = 0
    if hasattr(step, "then_actions") and step.then_actions:
        then_count = len(step.then_actions)
    if hasattr(step, "else_actions") and step.else_actions:
        else_count = len(step.else_actions)

    return {
        "id": str(step.id),
        "chain_id": str(step.chain_id),
        "order": step.order,
        "position_type": step.position_type,
        "source_service": step.source_service,
        "source_tool": step.source_tool,
        "ai_comment": step.ai_comment,
        "enabled": step.enabled,
        "created_at": step.created_at,
        "updated_at": step.updated_at,
        "condition_count": condition_count,
        "then_action_count": then_count,
        "else_action_count": else_count,
        "source_service_name": display_names.get(
            step.source_service, step.source_service.capitalize()
        ),
        "source_tool_display_name": source_tool_display,
    }


def _enrich_condition_group_response(group: ToolChainConditionGroup) -> dict:
    """Enrich a condition group response recursively."""
    conditions = []
    if group.conditions:
        for cond in sorted(group.conditions, key=lambda c: c.order):
            conditions.append(ConditionResponse(
                id=str(cond.id),
                group_id=str(cond.group_id),
                operator=cond.operator,
                field=cond.field,
                value=cond.value,
                order=cond.order,
                created_at=cond.created_at,
                updated_at=cond.updated_at,
            ))

    child_groups = []
    if group.child_groups:
        for child in sorted(group.child_groups, key=lambda g: g.order):
            child_groups.append(
                ConditionGroupResponse(**_enrich_condition_group_response(child))
            )

    return {
        "id": str(group.id),
        "step_id": str(group.step_id),
        "parent_group_id": str(group.parent_group_id) if group.parent_group_id else None,
        "operator": group.operator,
        "order": group.order,
        "created_at": group.created_at,
        "updated_at": group.updated_at,
        "conditions": conditions,
        "child_groups": child_groups,
    }


def _enrich_action_response(action: ToolChainAction) -> dict:
    """Enrich an action response with computed fields."""
    display_names = _get_service_display_names()

    target_service_name = None
    target_tool_display = None
    if action.target_service:
        target_service_name = display_names.get(
            action.target_service, action.target_service.capitalize()
        )
    if action.target_tool:
        target_tool_display = action.target_tool.replace("_", " ").replace(
            f"{action.target_service}_", ""
        ).title()

    return {
        "id": str(action.id),
        "step_id": str(action.step_id),
        "branch": action.branch,
        "action_type": action.action_type,
        "target_service": action.target_service,
        "target_tool": action.target_tool,
        "argument_mappings": action.argument_mappings,
        "message_template": action.message_template,
        "order": action.order,
        "execution_mode": action.execution_mode,
        "ai_comment": action.ai_comment,
        "enabled": action.enabled,
        "created_at": action.created_at,
        "updated_at": action.updated_at,
        "target_service_name": target_service_name,
        "target_tool_display_name": target_tool_display,
    }


def _build_step_detail_response(step: ToolChainStep) -> dict:
    """Build a detailed step response with conditions and actions."""
    step_data = _enrich_step_response(step)

    # Build condition groups
    condition_groups = []
    if step.condition_groups:
        for group in sorted(step.condition_groups, key=lambda g: g.order):
            if group.parent_group_id is None:  # Only root groups
                condition_groups.append(
                    ConditionGroupResponse(**_enrich_condition_group_response(group))
                )

    # Get all actions for this step and separate by branch
    then_actions = []
    else_actions = []
    if hasattr(step, "then_actions") and step.then_actions:
        for action in sorted(step.then_actions, key=lambda a: a.order):
            then_actions.append(ActionResponse(**_enrich_action_response(action)))

    if hasattr(step, "else_actions") and step.else_actions:
        for action in sorted(step.else_actions, key=lambda a: a.order):
            else_actions.append(ActionResponse(**_enrich_action_response(action)))

    step_data["condition_groups"] = condition_groups
    step_data["then_actions"] = then_actions
    step_data["else_actions"] = else_actions

    return step_data


async def _create_condition_groups_recursive(
    db: AsyncSession,
    step_id: str,
    groups_data: List[ConditionGroupCreate],
    parent_group_id: Optional[str] = None,
) -> List[ToolChainConditionGroup]:
    """Create condition groups recursively with their conditions."""
    created_groups = []

    for i, group_data in enumerate(groups_data):
        # Create the group
        group = ToolChainConditionGroup(
            step_id=step_id,
            parent_group_id=parent_group_id,
            operator=group_data.operator.value if isinstance(group_data.operator, ConditionGroupOperator) else group_data.operator,
            order=group_data.order if group_data.order != 0 else i,
        )
        db.add(group)
        await db.flush()

        # Create conditions in this group
        if group_data.conditions:
            for j, cond_data in enumerate(group_data.conditions):
                condition = ToolChainCondition(
                    group_id=group.id,
                    operator=cond_data.operator.value if isinstance(cond_data.operator, ConditionOperator) else cond_data.operator,
                    field=cond_data.field,
                    value=cond_data.value,
                    order=cond_data.order if cond_data.order != 0 else j,
                )
                db.add(condition)

        # Recursively create child groups
        if group_data.child_groups:
            await _create_condition_groups_recursive(
                db, step_id, group_data.child_groups, group.id
            )

        created_groups.append(group)

    return created_groups


async def _create_actions(
    db: AsyncSession,
    step_id: str,
    actions_data: List[ActionCreate],
    branch: str,
) -> List[ToolChainAction]:
    """Create actions for a step branch."""
    created_actions = []

    for i, action_data in enumerate(actions_data):
        action = ToolChainAction(
            step_id=step_id,
            branch=branch,
            action_type=action_data.action_type.value if isinstance(action_data.action_type, ActionType) else action_data.action_type,
            target_service=action_data.target_service,
            target_tool=action_data.target_tool,
            argument_mappings=action_data.argument_mappings,
            message_template=action_data.message_template,
            order=action_data.order if action_data.order != 0 else i,
            execution_mode=action_data.execution_mode.value if isinstance(action_data.execution_mode, ExecutionMode) else action_data.execution_mode,
            ai_comment=action_data.ai_comment,
            enabled=action_data.enabled,
        )
        db.add(action)
        created_actions.append(action)

    return created_actions


# === Reference Data ===


@router.get("/operators", response_model=ConditionOperatorsResponse)
async def get_condition_operators():
    """Get list of available condition operators with descriptions."""
    return ConditionOperatorsResponse()


@router.get("/group-operators", response_model=ConditionGroupOperatorsResponse)
async def get_condition_group_operators():
    """Get list of available condition group operators (AND/OR)."""
    return ConditionGroupOperatorsResponse()


@router.get("/action-types", response_model=ActionTypesResponse)
async def get_action_types():
    """Get list of available action types."""
    return ActionTypesResponse()


@router.get("/position-types", response_model=StepPositionTypesResponse)
async def get_step_position_types():
    """Get list of available step position types."""
    return StepPositionTypesResponse()


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
    """Get a specific tool chain with all steps, conditions, and actions."""
    result = await db.execute(
        select(ToolChain)
        .options(
            selectinload(ToolChain.steps)
            .selectinload(ToolChainStep.condition_groups)
            .selectinload(ToolChainConditionGroup.conditions),
            selectinload(ToolChain.steps)
            .selectinload(ToolChainStep.condition_groups)
            .selectinload(ToolChainConditionGroup.child_groups),
            selectinload(ToolChain.steps)
            .selectinload(ToolChainStep.then_actions),
            selectinload(ToolChain.steps)
            .selectinload(ToolChainStep.else_actions),
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
        chain_data["steps"].append(
            ToolChainStepDetailResponse(**_build_step_detail_response(step))
        )

    return ToolChainDetailResponse(**chain_data)


@router.post("/", response_model=ToolChainResponse, status_code=status.HTTP_201_CREATED)
async def create_tool_chain(chain_data: ToolChainCreate, db: AsyncSession = Depends(get_db)):
    """Create a new tool chain with optional steps."""
    # Create chain without steps
    chain = ToolChain(
        name=chain_data.name,
        description=chain_data.description,
        color=chain_data.color,
        priority=chain_data.priority,
        enabled=chain_data.enabled,
    )
    db.add(chain)
    await db.flush()

    # Add steps if provided
    if chain_data.steps:
        for i, step_data in enumerate(chain_data.steps):
            step = ToolChainStep(
                chain_id=chain.id,
                order=step_data.order if step_data.order != 0 else i,
                position_type=step_data.position_type.value if isinstance(step_data.position_type, StepPositionType) else step_data.position_type,
                source_service=step_data.source_service,
                source_tool=step_data.source_tool,
                ai_comment=step_data.ai_comment,
                enabled=step_data.enabled,
            )
            db.add(step)
            await db.flush()

            # Create condition groups
            if step_data.condition_groups:
                await _create_condition_groups_recursive(
                    db, step.id, step_data.condition_groups
                )

            # Create THEN actions
            if step_data.then_actions:
                await _create_actions(db, step.id, step_data.then_actions, "then")

            # Create ELSE actions
            if step_data.else_actions:
                await _create_actions(db, step.id, step_data.else_actions, "else")

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
    """Delete a tool chain and all its steps, conditions, and actions."""
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
    """List all steps in a tool chain with their conditions and actions."""
    # Verify chain exists
    chain_result = await db.execute(select(ToolChain).where(ToolChain.id == chain_id))
    if not chain_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tool chain not found")

    query = (
        select(ToolChainStep)
        .options(
            selectinload(ToolChainStep.condition_groups)
            .selectinload(ToolChainConditionGroup.conditions),
            selectinload(ToolChainStep.condition_groups)
            .selectinload(ToolChainConditionGroup.child_groups),
            selectinload(ToolChainStep.then_actions),
            selectinload(ToolChainStep.else_actions),
        )
        .where(ToolChainStep.chain_id == chain_id)
    )
    if enabled is not None:
        query = query.where(ToolChainStep.enabled == enabled)

    query = query.order_by(ToolChainStep.order)

    result = await db.execute(query)
    steps = result.scalars().all()

    return [
        ToolChainStepDetailResponse(**_build_step_detail_response(step))
        for step in steps
    ]


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

    step = ToolChainStep(
        chain_id=chain_id,
        order=step_data.order,
        position_type=step_data.position_type.value if isinstance(step_data.position_type, StepPositionType) else step_data.position_type,
        source_service=step_data.source_service,
        source_tool=step_data.source_tool,
        ai_comment=step_data.ai_comment,
        enabled=step_data.enabled,
    )
    db.add(step)
    await db.flush()

    # Create condition groups
    if step_data.condition_groups:
        await _create_condition_groups_recursive(db, step.id, step_data.condition_groups)

    # Create THEN actions
    if step_data.then_actions:
        await _create_actions(db, step.id, step_data.then_actions, "then")

    # Create ELSE actions
    if step_data.else_actions:
        await _create_actions(db, step.id, step_data.else_actions, "else")

    await db.commit()

    # Reload step with all relationships
    result = await db.execute(
        select(ToolChainStep)
        .options(
            selectinload(ToolChainStep.condition_groups)
            .selectinload(ToolChainConditionGroup.conditions),
            selectinload(ToolChainStep.condition_groups)
            .selectinload(ToolChainConditionGroup.child_groups),
            selectinload(ToolChainStep.then_actions),
            selectinload(ToolChainStep.else_actions),
        )
        .where(ToolChainStep.id == step.id)
    )
    step = result.scalar_one()

    logger.info(f"Added step to chain {chain_id}: {step.source_service}.{step.source_tool}")
    return ToolChainStepDetailResponse(**_build_step_detail_response(step))


@router.get("/{chain_id}/steps/{step_id}", response_model=ToolChainStepDetailResponse)
async def get_chain_step(chain_id: str, step_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific step from a tool chain with its conditions and actions."""
    result = await db.execute(
        select(ToolChainStep)
        .options(
            selectinload(ToolChainStep.condition_groups)
            .selectinload(ToolChainConditionGroup.conditions),
            selectinload(ToolChainStep.condition_groups)
            .selectinload(ToolChainConditionGroup.child_groups),
            selectinload(ToolChainStep.then_actions),
            selectinload(ToolChainStep.else_actions),
        )
        .where(
            and_(ToolChainStep.chain_id == chain_id, ToolChainStep.id == step_id)
        )
    )
    step = result.scalar_one_or_none()

    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    return ToolChainStepDetailResponse(**_build_step_detail_response(step))


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
        .options(
            selectinload(ToolChainStep.condition_groups)
            .selectinload(ToolChainConditionGroup.conditions),
            selectinload(ToolChainStep.condition_groups)
            .selectinload(ToolChainConditionGroup.child_groups),
            selectinload(ToolChainStep.then_actions),
            selectinload(ToolChainStep.else_actions),
        )
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
    if "position_type" in update_data and isinstance(update_data["position_type"], StepPositionType):
        update_data["position_type"] = update_data["position_type"].value

    for field, value in update_data.items():
        setattr(step, field, value)

    await db.commit()
    await db.refresh(step)

    logger.info(f"Updated step {step_id} in chain {chain_id}")
    return ToolChainStepDetailResponse(**_build_step_detail_response(step))


@router.delete("/{chain_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chain_step(chain_id: str, step_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a step from a tool chain (cascade deletes conditions and actions)."""
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


# === Condition Groups ===


@router.post(
    "/{chain_id}/steps/{step_id}/condition-groups",
    response_model=ConditionGroupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_condition_group(
    chain_id: str,
    step_id: str,
    group_data: ConditionGroupCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a condition group to a step."""
    # Verify step exists and belongs to chain
    step_result = await db.execute(
        select(ToolChainStep).where(
            and_(ToolChainStep.chain_id == chain_id, ToolChainStep.id == step_id)
        )
    )
    if not step_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Step not found")

    # Create the group (and nested conditions/groups)
    created_groups = await _create_condition_groups_recursive(
        db, step_id, [group_data]
    )
    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(ToolChainConditionGroup)
        .options(
            selectinload(ToolChainConditionGroup.conditions),
            selectinload(ToolChainConditionGroup.child_groups),
        )
        .where(ToolChainConditionGroup.id == created_groups[0].id)
    )
    group = result.scalar_one()

    logger.info(f"Added condition group to step {step_id}")
    return ConditionGroupResponse(**_enrich_condition_group_response(group))


@router.delete(
    "/{chain_id}/steps/{step_id}/condition-groups/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_condition_group(
    chain_id: str,
    step_id: str,
    group_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a condition group from a step (cascade deletes conditions and child groups)."""
    # Verify step exists and belongs to chain
    step_result = await db.execute(
        select(ToolChainStep).where(
            and_(ToolChainStep.chain_id == chain_id, ToolChainStep.id == step_id)
        )
    )
    if not step_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Step not found")

    result = await db.execute(
        select(ToolChainConditionGroup).where(
            and_(
                ToolChainConditionGroup.step_id == step_id,
                ToolChainConditionGroup.id == group_id,
            )
        )
    )
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=404, detail="Condition group not found")

    await db.delete(group)
    await db.commit()
    logger.info(f"Deleted condition group {group_id} from step {step_id}")


# === Conditions ===


@router.post(
    "/{chain_id}/steps/{step_id}/condition-groups/{group_id}/conditions",
    response_model=ConditionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_condition(
    chain_id: str,
    step_id: str,
    group_id: str,
    cond_data: ConditionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a condition to a condition group."""
    # Verify group exists
    group_result = await db.execute(
        select(ToolChainConditionGroup).where(
            and_(
                ToolChainConditionGroup.step_id == step_id,
                ToolChainConditionGroup.id == group_id,
            )
        )
    )
    if not group_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Condition group not found")

    condition = ToolChainCondition(
        group_id=group_id,
        operator=cond_data.operator.value if isinstance(cond_data.operator, ConditionOperator) else cond_data.operator,
        field=cond_data.field,
        value=cond_data.value,
        order=cond_data.order,
    )
    db.add(condition)
    await db.commit()
    await db.refresh(condition)

    logger.info(f"Added condition to group {group_id}")
    return ConditionResponse(
        id=str(condition.id),
        group_id=str(condition.group_id),
        operator=condition.operator,
        field=condition.field,
        value=condition.value,
        order=condition.order,
        created_at=condition.created_at,
        updated_at=condition.updated_at,
    )


@router.put(
    "/{chain_id}/steps/{step_id}/condition-groups/{group_id}/conditions/{cond_id}",
    response_model=ConditionResponse,
)
async def update_condition(
    chain_id: str,
    step_id: str,
    group_id: str,
    cond_id: str,
    cond_data: ConditionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a condition."""
    result = await db.execute(
        select(ToolChainCondition).where(
            and_(
                ToolChainCondition.group_id == group_id,
                ToolChainCondition.id == cond_id,
            )
        )
    )
    condition = result.scalar_one_or_none()

    if not condition:
        raise HTTPException(status_code=404, detail="Condition not found")

    # Update fields
    update_data = cond_data.model_dump(exclude_unset=True)

    # Convert enum to value
    if "operator" in update_data and isinstance(update_data["operator"], ConditionOperator):
        update_data["operator"] = update_data["operator"].value

    for field, value in update_data.items():
        setattr(condition, field, value)

    await db.commit()
    await db.refresh(condition)

    logger.info(f"Updated condition {cond_id}")
    return ConditionResponse(
        id=str(condition.id),
        group_id=str(condition.group_id),
        operator=condition.operator,
        field=condition.field,
        value=condition.value,
        order=condition.order,
        created_at=condition.created_at,
        updated_at=condition.updated_at,
    )


@router.delete(
    "/{chain_id}/steps/{step_id}/condition-groups/{group_id}/conditions/{cond_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_condition(
    chain_id: str,
    step_id: str,
    group_id: str,
    cond_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a condition from a group."""
    result = await db.execute(
        select(ToolChainCondition).where(
            and_(
                ToolChainCondition.group_id == group_id,
                ToolChainCondition.id == cond_id,
            )
        )
    )
    condition = result.scalar_one_or_none()

    if not condition:
        raise HTTPException(status_code=404, detail="Condition not found")

    await db.delete(condition)
    await db.commit()
    logger.info(f"Deleted condition {cond_id} from group {group_id}")


# === Actions (THEN/ELSE branches) ===


@router.get(
    "/{chain_id}/steps/{step_id}/actions/{branch}",
    response_model=List[ActionResponse],
)
async def list_step_actions(
    chain_id: str,
    step_id: str,
    branch: str,
    enabled: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all actions in a step branch (then or else)."""
    if branch not in ("then", "else"):
        raise HTTPException(status_code=400, detail="Branch must be 'then' or 'else'")

    # Verify step exists and belongs to chain
    step_result = await db.execute(
        select(ToolChainStep).where(
            and_(ToolChainStep.chain_id == chain_id, ToolChainStep.id == step_id)
        )
    )
    if not step_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Step not found")

    query = select(ToolChainAction).where(
        and_(
            ToolChainAction.step_id == step_id,
            ToolChainAction.branch == branch,
        )
    )
    if enabled is not None:
        query = query.where(ToolChainAction.enabled == enabled)

    query = query.order_by(ToolChainAction.order)

    result = await db.execute(query)
    actions = result.scalars().all()

    return [ActionResponse(**_enrich_action_response(a)) for a in actions]


@router.post(
    "/{chain_id}/steps/{step_id}/actions/{branch}",
    response_model=ActionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_step_action(
    chain_id: str,
    step_id: str,
    branch: str,
    action_data: ActionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add an action to a step branch (then or else)."""
    if branch not in ("then", "else"):
        raise HTTPException(status_code=400, detail="Branch must be 'then' or 'else'")

    # Verify step exists and belongs to chain
    step_result = await db.execute(
        select(ToolChainStep).where(
            and_(ToolChainStep.chain_id == chain_id, ToolChainStep.id == step_id)
        )
    )
    if not step_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Step not found")

    action = ToolChainAction(
        step_id=step_id,
        branch=branch,
        action_type=action_data.action_type.value if isinstance(action_data.action_type, ActionType) else action_data.action_type,
        target_service=action_data.target_service,
        target_tool=action_data.target_tool,
        argument_mappings=action_data.argument_mappings,
        message_template=action_data.message_template,
        order=action_data.order,
        execution_mode=action_data.execution_mode.value if isinstance(action_data.execution_mode, ExecutionMode) else action_data.execution_mode,
        ai_comment=action_data.ai_comment,
        enabled=action_data.enabled,
    )
    db.add(action)
    await db.commit()
    await db.refresh(action)

    logger.info(f"Added {branch} action to step {step_id}")
    return ActionResponse(**_enrich_action_response(action))


@router.put(
    "/{chain_id}/steps/{step_id}/actions/{branch}/{action_id}",
    response_model=ActionResponse,
)
async def update_step_action(
    chain_id: str,
    step_id: str,
    branch: str,
    action_id: str,
    action_data: ActionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an action in a step branch."""
    if branch not in ("then", "else"):
        raise HTTPException(status_code=400, detail="Branch must be 'then' or 'else'")

    result = await db.execute(
        select(ToolChainAction).where(
            and_(
                ToolChainAction.step_id == step_id,
                ToolChainAction.branch == branch,
                ToolChainAction.id == action_id,
            )
        )
    )
    action = result.scalar_one_or_none()

    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    # Update fields
    update_data = action_data.model_dump(exclude_unset=True)

    # Convert enums to values
    if "action_type" in update_data and isinstance(update_data["action_type"], ActionType):
        update_data["action_type"] = update_data["action_type"].value
    if "execution_mode" in update_data and isinstance(update_data["execution_mode"], ExecutionMode):
        update_data["execution_mode"] = update_data["execution_mode"].value

    for field, value in update_data.items():
        setattr(action, field, value)

    await db.commit()
    await db.refresh(action)

    logger.info(f"Updated action {action_id} in step {step_id}")
    return ActionResponse(**_enrich_action_response(action))


@router.delete(
    "/{chain_id}/steps/{step_id}/actions/{branch}/{action_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_step_action(
    chain_id: str,
    step_id: str,
    branch: str,
    action_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete an action from a step branch."""
    if branch not in ("then", "else"):
        raise HTTPException(status_code=400, detail="Branch must be 'then' or 'else'")

    result = await db.execute(
        select(ToolChainAction).where(
            and_(
                ToolChainAction.step_id == step_id,
                ToolChainAction.branch == branch,
                ToolChainAction.id == action_id,
            )
        )
    )
    action = result.scalar_one_or_none()

    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    await db.delete(action)
    await db.commit()
    logger.info(f"Deleted action {action_id} from step {step_id}")


@router.post(
    "/{chain_id}/steps/{step_id}/actions/{branch}/reorder",
    response_model=List[ActionResponse],
)
async def reorder_step_actions(
    chain_id: str,
    step_id: str,
    branch: str,
    action_ids: List[str],
    db: AsyncSession = Depends(get_db),
):
    """Reorder actions in a step branch."""
    if branch not in ("then", "else"):
        raise HTTPException(status_code=400, detail="Branch must be 'then' or 'else'")

    # Verify step exists and belongs to chain
    step_result = await db.execute(
        select(ToolChainStep).where(
            and_(ToolChainStep.chain_id == chain_id, ToolChainStep.id == step_id)
        )
    )
    if not step_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Step not found")

    # Get all actions for this branch
    result = await db.execute(
        select(ToolChainAction).where(
            and_(
                ToolChainAction.step_id == step_id,
                ToolChainAction.branch == branch,
            )
        )
    )
    actions = {str(a.id): a for a in result.scalars().all()}

    # Validate all action_ids belong to this step/branch
    for action_id in action_ids:
        if action_id not in actions:
            raise HTTPException(
                status_code=400,
                detail=f"Action {action_id} not found in step {step_id} branch {branch}",
            )

    # Update order
    for new_order, action_id in enumerate(action_ids):
        actions[action_id].order = new_order

    await db.commit()

    # Return updated actions in new order
    ordered_actions = sorted(actions.values(), key=lambda a: a.order)
    logger.info(f"Reordered {len(action_ids)} actions in step {step_id} branch {branch}")
    return [ActionResponse(**_enrich_action_response(a)) for a in ordered_actions]


# === Flowchart Visualization ===


@router.get("/{chain_id}/flowchart", response_model=FlowchartResponse)
async def get_chain_flowchart(chain_id: str, db: AsyncSession = Depends(get_db)):
    """Get flowchart data for visualizing a tool chain.

    Returns nodes and edges for rendering with a graph library.
    """
    result = await db.execute(
        select(ToolChain)
        .options(
            selectinload(ToolChain.steps)
            .selectinload(ToolChainStep.condition_groups)
            .selectinload(ToolChainConditionGroup.conditions),
            selectinload(ToolChain.steps)
            .selectinload(ToolChainStep.then_actions),
            selectinload(ToolChain.steps)
            .selectinload(ToolChainStep.else_actions),
        )
        .where(ToolChain.id == chain_id)
    )
    chain = result.scalar_one_or_none()

    if not chain:
        raise HTTPException(status_code=404, detail="Tool chain not found")

    nodes = []
    edges = []
    display_names = _get_service_display_names()

    y_offset = 0
    spacing_y = 150
    spacing_x = 250

    for step in sorted(chain.steps, key=lambda s: s.order):
        step_id = str(step.id)
        source_tool_display = step.source_tool.replace("_", " ").replace(
            f"{step.source_service}_", ""
        ).title()

        # Step node (trigger)
        step_node_id = f"step-{step_id}"
        nodes.append(FlowchartNode(
            id=step_node_id,
            type="step",
            label=f"{display_names.get(step.source_service, step.source_service)}: {source_tool_display}",
            data={"step_id": step_id, "position_type": step.position_type},
            position={"x": 0, "y": y_offset},
        ))

        # Condition node (diamond)
        condition_node_id = f"condition-{step_id}"
        condition_label = "Conditions"
        if step.condition_groups:
            first_group = step.condition_groups[0]
            if first_group.conditions:
                first_cond = first_group.conditions[0]
                condition_label = f"{first_cond.field or ''} {first_cond.operator} {first_cond.value or ''}"

        nodes.append(FlowchartNode(
            id=condition_node_id,
            type="condition",
            label=condition_label,
            data={"step_id": step_id},
            position={"x": 0, "y": y_offset + spacing_y},
        ))
        edges.append(FlowchartEdge(
            id=f"edge-{step_node_id}-{condition_node_id}",
            source=step_node_id,
            target=condition_node_id,
            type="default",
        ))

        # THEN branch
        then_y = y_offset + spacing_y * 2
        if step.then_actions:
            for i, action in enumerate(sorted(step.then_actions, key=lambda a: a.order)):
                action_id = f"then-{action.id}"
                if action.action_type == ActionType.MESSAGE.value:
                    label = "Message"
                    node_type = "message"
                else:
                    label = f"{display_names.get(action.target_service, action.target_service or '')}: {action.target_tool or ''}"
                    node_type = "action"

                nodes.append(FlowchartNode(
                    id=action_id,
                    type=node_type,
                    label=label,
                    data={"action_id": str(action.id), "branch": "then"},
                    position={"x": -spacing_x, "y": then_y + (i * 80)},
                ))

                if i == 0:
                    edges.append(FlowchartEdge(
                        id=f"edge-{condition_node_id}-{action_id}",
                        source=condition_node_id,
                        target=action_id,
                        label="TRUE",
                        type="then",
                    ))
                else:
                    prev_action = f"then-{step.then_actions[i - 1].id}"
                    edges.append(FlowchartEdge(
                        id=f"edge-{prev_action}-{action_id}",
                        source=prev_action,
                        target=action_id,
                        type="then",
                    ))

        # ELSE branch
        if step.else_actions:
            for i, action in enumerate(sorted(step.else_actions, key=lambda a: a.order)):
                action_id = f"else-{action.id}"
                if action.action_type == ActionType.MESSAGE.value:
                    label = "Message"
                    node_type = "message"
                else:
                    label = f"{display_names.get(action.target_service, action.target_service or '')}: {action.target_tool or ''}"
                    node_type = "action"

                nodes.append(FlowchartNode(
                    id=action_id,
                    type=node_type,
                    label=label,
                    data={"action_id": str(action.id), "branch": "else"},
                    position={"x": spacing_x, "y": then_y + (i * 80)},
                ))

                if i == 0:
                    edges.append(FlowchartEdge(
                        id=f"edge-{condition_node_id}-{action_id}",
                        source=condition_node_id,
                        target=action_id,
                        label="FALSE",
                        type="else",
                    ))
                else:
                    prev_action = f"else-{step.else_actions[i - 1].id}"
                    edges.append(FlowchartEdge(
                        id=f"edge-{prev_action}-{action_id}",
                        source=prev_action,
                        target=action_id,
                        type="else",
                    ))

        # Calculate next step y offset
        max_actions = max(
            len(step.then_actions) if step.then_actions else 0,
            len(step.else_actions) if step.else_actions else 0,
        )
        y_offset += spacing_y * 2 + (max_actions * 80) + spacing_y

    return FlowchartResponse(
        chain_id=str(chain.id),
        chain_name=chain.name,
        nodes=nodes,
        edges=edges,
    )


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
        .options(
            selectinload(ToolChainStep.condition_groups)
            .selectinload(ToolChainConditionGroup.conditions),
            selectinload(ToolChainStep.condition_groups)
            .selectinload(ToolChainConditionGroup.child_groups),
            selectinload(ToolChainStep.then_actions),
            selectinload(ToolChainStep.else_actions),
        )
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

    return [
        ToolChainStepDetailResponse(**_build_step_detail_response(step))
        for step in steps
    ]
