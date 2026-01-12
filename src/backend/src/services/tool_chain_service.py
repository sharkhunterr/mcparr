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

        # Build suggestions for each target
        for target in enabled_targets:
            target_service_name = SERVICE_DISPLAY_NAMES.get(
                target.target_service, target.target_service
            )

            suggestion = {
                "tool": target.target_tool,
                "service": target.target_service,
                "service_name": target_service_name,
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


def format_next_tools_for_response(
    suggestions: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Format next tool suggestions into a response block.

    This will be added to tool responses to guide the AI on what to call next.
    """
    if not suggestions:
        return None

    return {
        "next_tools_to_call": suggestions,
        "ai_instruction": (
            "Based on the result above and configured tool chains, "
            "you should consider calling these tools next. "
            "Each suggestion includes a reason explaining when/why to use it."
        ),
    }


async def enrich_tool_result_with_chains(
    session: AsyncSession,
    tool_name: str,
    result: Dict[str, Any],
    input_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Add next tool suggestions to a tool result if matching chains exist.

    This function should be called after tool execution to add
    chain suggestions to the response.
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
        # Get matching steps and their target tools
        suggestions = await get_matching_steps(
            session, service_type, tool_name, result, success, input_params
        )

        if suggestions:
            # Add next tools to result
            next_tools_block = format_next_tools_for_response(suggestions)
            if next_tools_block:
                result.update(next_tools_block)
                logger.info(
                    f"Added {len(suggestions)} next tool suggestions to '{tool_name}' result"
                )

    except Exception as e:
        # Don't fail the tool call if chain evaluation fails
        logger.error(f"Error evaluating tool chains for '{tool_name}': {e}")

    return result
