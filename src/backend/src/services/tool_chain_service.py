"""Service for evaluating and applying tool chains."""

import json
import re
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.tool_chain import (
    ConditionOperator,
    ToolChain,
    ToolChainStep,
    ToolChainStepTarget,
)


def get_nested_value(data: Any, path: str) -> Any:
    """Get a nested value from a dict/list using dot notation.

    Examples:
        get_nested_value({"a": {"b": 1}}, "a.b") -> 1
        get_nested_value({"items": [1, 2, 3]}, "items.length") -> 3
        get_nested_value({"data": [{"id": 1}]}, "data.0.id") -> 1
    """
    if not path or data is None:
        return data

    parts = path.split(".")
    current = data

    for part in parts:
        if current is None:
            return None

        # Handle special "length" property for lists
        if part == "length" and isinstance(current, (list, str)):
            return len(current)

        # Handle numeric indices for lists
        if isinstance(current, list):
            try:
                idx = int(part)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            except ValueError:
                # Not a numeric index, try to get from each item
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None

    return current


def evaluate_condition(
    result: Dict[str, Any],
    success: bool,
    operator: str,
    field: Optional[str] = None,
    value: Optional[str] = None,
) -> bool:
    """Evaluate a tool chain condition against a result.

    Args:
        result: The tool execution result
        success: Whether the tool execution was successful
        operator: The condition operator
        field: The field path to check (for field-based conditions)
        value: The value to compare against

    Returns:
        True if the condition matches, False otherwise
    """
    # Handle success/failed operators first (don't need field)
    if operator == ConditionOperator.SUCCESS.value:
        return success

    if operator == ConditionOperator.FAILED.value:
        return not success

    # For other operators, we need a field
    if not field:
        return False

    # Get the actual value from the result
    actual_value = get_nested_value(result, field)

    # Handle empty checks
    if operator == ConditionOperator.IS_EMPTY.value:
        if actual_value is None:
            return True
        if isinstance(actual_value, (list, dict, str)):
            return len(actual_value) == 0
        return False

    if operator == ConditionOperator.IS_NOT_EMPTY.value:
        if actual_value is None:
            return False
        if isinstance(actual_value, (list, dict, str)):
            return len(actual_value) > 0
        return True

    # For comparison operators, we need a value
    if value is None:
        return False

    # Try to parse value as JSON for complex comparisons
    try:
        parsed_value = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        parsed_value = value

    # Handle comparison operators
    if operator == ConditionOperator.EQUALS.value:
        return actual_value == parsed_value

    if operator == ConditionOperator.NOT_EQUALS.value:
        return actual_value != parsed_value

    if operator == ConditionOperator.CONTAINS.value:
        if isinstance(actual_value, str):
            return str(parsed_value) in actual_value
        if isinstance(actual_value, list):
            return parsed_value in actual_value
        return False

    if operator == ConditionOperator.NOT_CONTAINS.value:
        if isinstance(actual_value, str):
            return str(parsed_value) not in actual_value
        if isinstance(actual_value, list):
            return parsed_value not in actual_value
        return True

    if operator == ConditionOperator.REGEX_MATCH.value:
        if isinstance(actual_value, str):
            try:
                return bool(re.search(str(parsed_value), actual_value))
            except re.error:
                return False
        return False

    # Numeric comparisons
    try:
        actual_num = float(actual_value) if actual_value is not None else None
        compare_num = float(parsed_value)

        if actual_num is None:
            return False

        if operator == ConditionOperator.GREATER_THAN.value:
            return actual_num > compare_num
        if operator == ConditionOperator.LESS_THAN.value:
            return actual_num < compare_num
        if operator == ConditionOperator.GREATER_OR_EQUAL.value:
            return actual_num >= compare_num
        if operator == ConditionOperator.LESS_OR_EQUAL.value:
            return actual_num <= compare_num
    except (ValueError, TypeError):
        return False

    return False


def build_argument_mappings(
    mappings: Optional[Dict[str, Any]],
    result: Dict[str, Any],
    input_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build arguments for the next tool based on mappings.

    Mapping format:
    {
        "target_param": {"source": "result.field.path"},
        "target_param2": {"value": "static_value"},
        "target_param3": {"input": "original_param"}
    }
    """
    if not mappings:
        return {}

    args = {}
    for target_param, mapping in mappings.items():
        if isinstance(mapping, dict):
            if "source" in mapping:
                # Get value from result
                source_path = mapping["source"]
                if source_path == "result":
                    args[target_param] = result
                elif source_path.startswith("result."):
                    args[target_param] = get_nested_value(result, source_path[7:])
                else:
                    args[target_param] = get_nested_value(result, source_path)
            elif "value" in mapping:
                # Static value
                args[target_param] = mapping["value"]
            elif "input" in mapping and input_params:
                # From original input
                input_path = mapping["input"]
                if input_path in input_params:
                    args[target_param] = input_params[input_path]
        else:
            # Direct value assignment
            args[target_param] = mapping

    return args


# Service display names for better AI readability
SERVICE_DISPLAY_NAMES = {
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


async def get_matching_steps(
    session: AsyncSession,
    service_type: str,
    tool_name: str,
    result: Dict[str, Any],
    success: bool,
    input_params: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Find all steps that match a tool result.

    The new architecture has steps with their own source tool and condition.
    When a step's condition matches, we return its targets as next tools to call.

    IMPORTANT: Only steps at order=1 are evaluated by default.
    Steps at order > 1 are only triggered if called from a target of a previous step
    in the same chain. This prevents steps from being triggered out of context.

    Returns a list of next tool suggestions with:
    - target tool info
    - AI guidance/comments
    - suggested arguments
    """
    # Fetch enabled steps for this source tool from enabled chains
    # ONLY fetch steps at order=1 (first steps of chains)
    # Steps at order > 1 should only be triggered as part of chain flow
    query = (
        select(ToolChainStep)
        .options(
            selectinload(ToolChainStep.target_tools),
            selectinload(ToolChainStep.chain),
        )
        .join(ToolChain)
        .where(
            and_(
                ToolChainStep.source_service == service_type,
                ToolChainStep.source_tool == tool_name,
                ToolChainStep.enabled == True,
                ToolChain.enabled == True,
                ToolChainStep.order == 0,  # Only first steps of chains (0-indexed)
            )
        )
        .order_by(ToolChain.priority.desc(), ToolChainStep.order)
    )

    db_result = await session.execute(query)
    steps = db_result.scalars().all()

    matching_suggestions = []

    for step in steps:
        # Evaluate the step's condition
        if not evaluate_condition(
            result,
            success,
            step.condition_operator,
            step.condition_field,
            step.condition_value,
        ):
            continue

        # Step condition matches! Get enabled targets
        enabled_targets = [t for t in step.target_tools if t.enabled]
        if not enabled_targets:
            continue

        # Sort by order
        enabled_targets.sort(key=lambda t: t.order)

        # Get chain info
        chain = step.chain

        # Build suggestions for each target
        for target in enabled_targets:
            target_service_name = SERVICE_DISPLAY_NAMES.get(
                target.target_service, target.target_service
            )

            suggestion = {
                "tool": target.target_tool,
                "service": target.target_service,
                "service_name": target_service_name,
                # Minimal chain reference (full context is at root level)
                "_chain_id": str(chain.id),
                "_chain_name": chain.name,
                "_chain_color": chain.color,
                "_step_order": step.order,  # Current step order (0-indexed)
            }

            # Build suggested arguments if mappings exist
            if target.argument_mappings:
                suggestion["suggested_arguments"] = build_argument_mappings(
                    target.argument_mappings, result, input_params
                )

            # Add AI guidance - combine step comment and target comment
            comments = []
            if step.ai_comment:
                comments.append(step.ai_comment)
            if target.target_ai_comment:
                comments.append(target.target_ai_comment)
            if comments:
                suggestion["reason"] = " ".join(comments)

            matching_suggestions.append(suggestion)

    return matching_suggestions


async def get_matching_steps_any_order(
    session: AsyncSession,
    service_type: str,
    tool_name: str,
    result: Dict[str, Any],
    success: bool,
    input_params: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Find matching steps for a tool that is in the middle of a chain (any order).

    Unlike get_matching_steps, this doesn't filter by order == 0.
    Used when we know the tool is already part of a chain flow.
    """
    # Fetch enabled steps for this source tool from enabled chains (any order)
    query = (
        select(ToolChainStep)
        .options(
            selectinload(ToolChainStep.target_tools),
            selectinload(ToolChainStep.chain),
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

    db_result = await session.execute(query)
    steps = db_result.scalars().all()

    matching_suggestions = []

    for step in steps:
        # Evaluate the step's condition
        if not evaluate_condition(
            result,
            success,
            step.condition_operator,
            step.condition_field,
            step.condition_value,
        ):
            continue

        # Step condition matches! Get enabled targets
        enabled_targets = [t for t in step.target_tools if t.enabled]
        if not enabled_targets:
            continue

        # Sort by order
        enabled_targets.sort(key=lambda t: t.order)

        # Get chain info
        chain = step.chain

        # Build suggestions for each target
        for target in enabled_targets:
            target_service_name = SERVICE_DISPLAY_NAMES.get(
                target.target_service, target.target_service
            )

            suggestion = {
                "tool": target.target_tool,
                "service": target.target_service,
                "service_name": target_service_name,
                # Minimal chain reference (full context is at root level)
                "_chain_id": str(chain.id),
                "_chain_name": chain.name,
                "_chain_color": chain.color,
                "_step_order": step.order,  # Current step order (0-indexed)
            }

            # Build suggested arguments if mappings exist
            if target.argument_mappings:
                suggestion["suggested_arguments"] = build_argument_mappings(
                    target.argument_mappings, result, input_params
                )

            # Add AI guidance
            comments = []
            if step.ai_comment:
                comments.append(step.ai_comment)
            if target.target_ai_comment:
                comments.append(target.target_ai_comment)
            if comments:
                suggestion["reason"] = " ".join(comments)

            matching_suggestions.append(suggestion)

    return matching_suggestions


def format_next_tools_for_response(
    suggestions: List[Dict[str, Any]],
    source_tool: str,
) -> Optional[Dict[str, Any]]:
    """Format next tool suggestions into a response block.

    This will be added to tool responses to guide the AI on what to call next.
    """
    if not suggestions:
        return None

    # Extract unique chains and step order from suggestions (using internal fields)
    chains_seen = {}
    step_order = None
    for s in suggestions:
        chain_id = s.get("_chain_id")
        if chain_id and chain_id not in chains_seen:
            chains_seen[chain_id] = {
                "id": chain_id,
                "name": s.get("_chain_name"),
                "color": s.get("_chain_color"),
            }
        # Get step_order from first suggestion (they should all be from same step)
        if step_order is None and "_step_order" in s:
            step_order = s["_step_order"]

    # Clean suggestions - remove internal chain fields (prefixed with _)
    clean_suggestions = []
    for s in suggestions:
        clean_s = {k: v for k, v in s.items() if not k.startswith("_")}
        clean_suggestions.append(clean_s)

    return {
        "chain_context": {
            "position": "start",
            "source_tool": source_tool,
            "chains": list(chains_seen.values()),
            "step_number": (step_order + 1) if step_order is not None else 1,  # 1-indexed for display
        },
        "next_tools_to_call": clean_suggestions,
        "ai_instruction": (
            "Based on the result above and configured tool chains, "
            "you should consider calling these tools next. "
            "Each suggestion includes a reason explaining when/why to use it."
        ),
    }


async def get_tool_chain_position(
    session: AsyncSession,
    service_type: str,
    tool_name: str,
) -> Optional[Dict[str, Any]]:
    """Check if this tool is a target in any chain step (meaning it's part of a chain flow).

    Returns chain context info if the tool is a target, None otherwise.
    """
    # Check if this tool is a target in any enabled chain step
    target_query = (
        select(ToolChainStepTarget)
        .options(
            selectinload(ToolChainStepTarget.step).selectinload(ToolChainStep.chain),
        )
        .join(ToolChainStep)
        .join(ToolChain)
        .where(
            and_(
                ToolChainStepTarget.target_service == service_type,
                ToolChainStepTarget.target_tool == tool_name,
                ToolChainStepTarget.enabled == True,
                ToolChainStep.enabled == True,
                ToolChain.enabled == True,
            )
        )
    )

    target_result = await session.execute(target_query)
    targets = target_result.scalars().all()

    if not targets:
        return None

    # This tool is a target - check if there are next steps that use it as source
    # If no next steps exist, this is the end of the chain
    chains_info = []

    for target in targets:
        step = target.step
        chain = step.chain

        # Check if there's a next step in this chain that uses this tool as source
        next_step_query = (
            select(ToolChainStep)
            .where(
                and_(
                    ToolChainStep.chain_id == chain.id,
                    ToolChainStep.source_service == service_type,
                    ToolChainStep.source_tool == tool_name,
                    ToolChainStep.enabled == True,
                )
            )
        )
        next_step_result = await session.execute(next_step_query)
        has_next_step = next_step_result.scalar() is not None

        # Determine position
        position = "middle" if has_next_step else "end"

        chains_info.append({
            "id": str(chain.id),
            "name": chain.name,
            "color": chain.color,
            "position": position,
            "previous_step_order": step.order,
            "source_tool": step.source_tool,  # The tool that triggered this one
        })

    if not chains_info:
        return None

    # Use the first chain's position (most relevant)
    primary_position = chains_info[0]["position"]
    primary_source = chains_info[0]["source_tool"]
    # Step number is previous_step_order + 2 (because we're at the target of that step)
    # previous_step_order is 0-indexed, and we're now at the next step
    step_number = chains_info[0]["previous_step_order"] + 2

    return {
        "position": primary_position,
        "source_tool": primary_source,
        "step_number": step_number,  # 1-indexed for display
        "chains": [{"id": c["id"], "name": c["name"], "color": c["color"]} for c in chains_info],
    }


async def check_recent_chain_flow(
    session: AsyncSession,
    service_type: str,
    tool_name: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    time_window_seconds: int = 60,
) -> Optional[Dict[str, Any]]:
    """Check if this tool was called as part of a chain flow by looking at recent history.

    Looks at the most recent MCP request FROM THE SAME USER/SESSION to see if it
    was a tool that has this tool as a target in a chain step.

    Args:
        session: Database session
        service_type: Service type of the current tool
        tool_name: Name of the current tool
        session_id: Session ID to filter by (for multi-user support)
        user_id: User ID to filter by (fallback if no session_id)
        time_window_seconds: How far back to look for previous calls (default 60s)

    Returns:
        Chain context if this tool follows a chain flow, None otherwise
    """
    from datetime import datetime, timedelta

    from src.models.mcp_request import McpRequest, McpRequestStatus

    # Get the most recent completed request (excluding current one)
    time_threshold = datetime.utcnow() - timedelta(seconds=time_window_seconds)

    # Build query conditions
    conditions = [
        McpRequest.status == McpRequestStatus.COMPLETED,
        McpRequest.created_at >= time_threshold,
    ]

    # Filter by session_id or user_id to support multiple concurrent users
    if session_id:
        conditions.append(McpRequest.session_id == session_id)
    elif user_id:
        conditions.append(McpRequest.user_id == user_id)
    # If neither is provided, we can't reliably determine chain flow for this user
    # Fall back to global (but this could cause issues with concurrent users)

    recent_query = (
        select(McpRequest)
        .where(and_(*conditions))
        .order_by(McpRequest.created_at.desc())
        .limit(1)
    )

    recent_result = await session.execute(recent_query)
    recent_request = recent_result.scalar()

    if not recent_request:
        return None

    previous_tool = recent_request.tool_name

    # Check if the previous tool has a chain step that targets the current tool
    # AND if the previous result had next_tools_to_call suggesting this tool
    previous_result = recent_request.output_result or {}
    next_tools = previous_result.get("next_tools_to_call", [])

    # Check if current tool was suggested by the previous tool
    for next_tool in next_tools:
        if next_tool.get("tool") == tool_name:
            # This tool was suggested by the previous call - it's part of a chain!
            chain_context = previous_result.get("chain_context", {})
            return {
                "is_chain_flow": True,
                "previous_tool": previous_tool,
                "chain_context": chain_context,
            }

    return None


async def enrich_tool_result_with_chains(
    session: AsyncSession,
    tool_name: str,
    result: Dict[str, Any],
    input_params: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Add next tool suggestions to a tool result if matching chains exist.

    This function should be called after tool execution to add
    chain suggestions to the response.

    Chain flow detection (automatic):
    - Checks recent MCP history to see if the previous tool suggested this one
    - If yes, this tool is part of a chain flow (middle or end position)
    - If not, only first steps (order=0) are evaluated

    Multi-user support:
    - Uses session_id or user_id to filter history and only look at requests
      from the same user/session, preventing cross-user chain interference

    This design ensures that:
    - Chain suggestions only appear when the FIRST tool of a chain is called
    - OR when the previous tool in history suggested this tool (automatic chain flow)
    - Calling a "middle" tool directly does NOT trigger chain logic
    - Multiple users can use chains simultaneously without interference

    Args:
        session: Database session
        tool_name: Name of the tool that was executed
        result: The tool execution result
        input_params: Original input parameters
        session_id: Session ID for multi-user chain flow tracking
        user_id: User ID for multi-user chain flow tracking (fallback)
    """
    # Determine service type from tool name
    service_type = None
    prefixes = [
        "plex_", "overseerr_", "zammad_", "tautulli_", "openwebui_",
        "radarr_", "sonarr_", "prowlarr_", "jackett_", "deluge_",
        "komga_", "romm_", "audiobookshelf_", "wikijs_", "authentik_",
        "system_"
    ]

    for prefix in prefixes:
        if tool_name.startswith(prefix):
            service_type = prefix.rstrip("_")
            break

    if not service_type:
        return result

    # Check if the tool was successful
    success = result.get("success", False)

    try:
        # First, check if this tool is part of a chain flow by looking at recent history
        # Filter by session_id/user_id to support multiple concurrent users
        chain_flow = await check_recent_chain_flow(
            session, service_type, tool_name, session_id=session_id, user_id=user_id
        )

        if chain_flow and chain_flow.get("is_chain_flow"):
            # This tool was called as part of a chain flow (previous tool suggested it)
            logger.info(
                f"Tool '{tool_name}' is part of chain flow (preceded by '{chain_flow['previous_tool']}')"
            )

            # Check if there are next steps configured for this tool
            existing_position = await get_tool_chain_position(session, service_type, tool_name)

            if existing_position:
                result["chain_context"] = existing_position

                # If this is a "middle" position, evaluate next step conditions
                if existing_position["position"] == "middle":
                    middle_suggestions = await get_matching_steps_any_order(
                        session, service_type, tool_name, result, success, input_params
                    )
                    if middle_suggestions:
                        next_block = format_next_tools_for_response(middle_suggestions, tool_name)
                        if next_block:
                            # Override chain_context with proper position
                            next_block["chain_context"]["position"] = "middle"
                            result.update(next_block)
                            logger.info(
                                f"Added {len(middle_suggestions)} next tool suggestions to '{tool_name}' (middle step)"
                            )
                else:
                    # End of chain - no next tools
                    logger.info(
                        f"Tool '{tool_name}' is end of chain(s): "
                        f"{[c['name'] for c in existing_position['chains']]}"
                    )
        else:
            # Not part of a chain flow - only evaluate first steps (order=0)
            suggestions = await get_matching_steps(
                session, service_type, tool_name, result, success, input_params
            )

            if suggestions:
                # This tool is the START of a chain - add next tools to result
                next_tools_block = format_next_tools_for_response(suggestions, tool_name)
                if next_tools_block:
                    result.update(next_tools_block)
                    logger.info(
                        f"Added {len(suggestions)} next tool suggestions to '{tool_name}' result"
                    )
            # If no suggestions, this tool is either:
            # - Not part of any chain as a first step
            # - A middle/end tool called directly (we ignore chains in this case)

    except Exception as e:
        # Don't fail the tool call if chain evaluation fails
        logger.error(f"Error evaluating tool chains for '{tool_name}': {e}")

    return result
