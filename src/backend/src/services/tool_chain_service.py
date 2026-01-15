"""Service for evaluating and applying tool chains with IF/THEN/ELSE logic."""

import json
import re
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.tool_chain import (
    ActionType,
    ConditionGroupOperator,
    ConditionOperator,
    StepPositionType,
    ToolChain,
    ToolChainAction,
    ToolChainConditionGroup,
    ToolChainStep,
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


def evaluate_single_condition(
    result: Dict[str, Any],
    success: bool,
    operator: str,
    field: Optional[str] = None,
    value: Optional[str] = None,
) -> bool:
    """Evaluate a single condition against a result.

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


def evaluate_condition_group(
    group: ToolChainConditionGroup,
    result: Dict[str, Any],
    success: bool,
) -> bool:
    """Evaluate a condition group recursively with AND/OR logic.

    Supports nested groups for complex expressions like:
    (A AND B) OR (C AND D)

    Args:
        group: The condition group to evaluate
        result: The tool execution result
        success: Whether the tool execution was successful

    Returns:
        True if the group conditions evaluate to true
    """
    group_operator = group.operator

    # Evaluate all conditions in this group
    condition_results = []
    if group.conditions:
        for condition in group.conditions:
            cond_result = evaluate_single_condition(
                result,
                success,
                condition.operator,
                condition.field,
                condition.value,
            )
            condition_results.append(cond_result)

    # Evaluate child groups recursively
    child_results = []
    if group.child_groups:
        for child_group in group.child_groups:
            child_result = evaluate_condition_group(child_group, result, success)
            child_results.append(child_result)

    # Combine all results
    all_results = condition_results + child_results

    if not all_results:
        # Empty group - default to True (no conditions = always match)
        return True

    # Apply AND/OR logic
    if group_operator == ConditionGroupOperator.AND.value:
        return all(all_results)
    else:  # OR
        return any(all_results)


def evaluate_step_conditions(
    step: ToolChainStep,
    result: Dict[str, Any],
    success: bool,
) -> bool:
    """Evaluate all conditions for a step.

    A step can have multiple condition groups at the root level.
    Groups are combined with AND logic.

    Args:
        step: The step to evaluate
        result: The tool execution result (full dict with success, result, error)
        success: Whether the tool execution was successful

    Returns:
        True if conditions pass (THEN branch), False otherwise (ELSE branch)
    """
    if not step.condition_groups:
        # No conditions = THEN branch executes
        return True

    # Only evaluate root groups (those without parent and not attached to an action)
    root_groups = [g for g in step.condition_groups if g.parent_group_id is None]

    if not root_groups:
        return True

    # Extract the actual result data for condition evaluation
    # This allows conditions to use "available" instead of "result.available"
    eval_data = result.get("result", {}) if isinstance(result.get("result"), dict) else result

    # All groups are combined with AND logic
    for group in root_groups:
        if not evaluate_condition_group(group, eval_data, success):
            return False

    return True


def evaluate_action_conditions(
    action: "ToolChainAction",
    result: Dict[str, Any],
    success: bool,
) -> bool:
    """Evaluate conditions for a CONDITIONAL action.

    Args:
        action: The conditional action with condition_groups
        result: The tool execution result
        success: Whether the tool execution was successful

    Returns:
        True if conditions pass (THEN branch), False otherwise (ELSE branch)
    """
    if not action.condition_groups:
        # No conditions = THEN branch
        return True

    # Extract the actual result data for condition evaluation
    eval_data = result.get("result", {}) if isinstance(result.get("result"), dict) else result

    # All groups combined with AND logic
    for group in action.condition_groups:
        if group.parent_group_id is None:  # Only root groups
            if not evaluate_condition_group(group, eval_data, success):
                return False

    return True


def interpolate_message_template(
    template: str,
    result: Dict[str, Any],
    input_params: Optional[Dict[str, Any]] = None,
    chain_context: Optional[Dict[str, Any]] = None,
) -> str:
    """Interpolate placeholders in a message template.

    Supports placeholders like:
    - {result.title} - Access result fields
    - {result.data.0.name} - Access nested/array fields
    - {input.query} - Access original input parameters
    - {context.variable} - Access saved context variables

    Args:
        template: The message template with placeholders
        result: The tool execution result (full dict with success, result, error)
        input_params: Original input parameters
        chain_context: Saved context variables from previous steps

    Returns:
        The interpolated message string
    """
    if not template:
        return ""

    # Extract the actual result data for interpolation
    result_data = result.get("result", {}) if isinstance(result.get("result"), dict) else result
    ctx = chain_context or {}

    # Find all placeholders like {result.field}, {input.param}, or {context.var}
    placeholder_pattern = r"\{((?:result|input|context)\.[\w.]+)\}"

    def replace_placeholder(match):
        path = match.group(1)
        if path.startswith("result."):
            field_path = path[7:]  # Remove "result." prefix
            value = get_nested_value(result_data, field_path)
        elif path.startswith("input."):
            field_path = path[6:]  # Remove "input." prefix
            value = input_params.get(field_path) if input_params else None
        elif path.startswith("context."):
            var_name = path[8:]  # Remove "context." prefix
            value = ctx.get(var_name)
        else:
            value = None

        # Convert to string representation
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return str(value)

    return re.sub(placeholder_pattern, replace_placeholder, template)


def build_argument_mappings(
    mappings: Optional[Dict[str, Any]],
    result: Dict[str, Any],
    input_params: Optional[Dict[str, Any]] = None,
    chain_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build arguments for the next tool based on mappings.

    Simplified mapping format (recommended):
    {
        "movie_id": "id",              # Maps result.id to movie_id
        "title": "title",              # Maps result.title to title
        "year": "year",                # Maps result.year to year
        "media_id": "context.saved_id" # Maps from chain context
    }

    Advanced mapping format (also supported):
    {
        "target_param": {"source": "result.field.path"},
        "target_param2": {"value": "static_value"},
        "target_param3": {"input": "original_param"},
        "target_param4": {"context": "variable_name"}
    }

    The result data is extracted from result.result if it exists (to allow
    using field names directly like "id" instead of "result.id").

    Context variables can be accessed with "context." prefix in simplified format
    or with {"context": "var_name"} in advanced format.
    """
    if not mappings:
        return {}

    # Extract the actual result data for simpler field access
    # This allows using "id" instead of "result.id"
    eval_data = result.get("result", {}) if isinstance(result.get("result"), dict) else result

    # Ensure chain_context is a dict
    ctx = chain_context or {}

    args = {}
    for target_param, mapping in mappings.items():
        if isinstance(mapping, dict):
            # Advanced format with explicit source type
            if "source" in mapping:
                # Get value from result (supports nested paths like "result.movie.id")
                source_path = mapping["source"]
                args[target_param] = get_nested_value(result, source_path)
            elif "value" in mapping:
                # Static value
                args[target_param] = mapping["value"]
            elif "input" in mapping and input_params:
                # From original input
                input_path = mapping["input"]
                if input_path in input_params:
                    args[target_param] = input_params[input_path]
            elif "context" in mapping:
                # From chain context
                context_var = mapping["context"]
                if context_var in ctx:
                    args[target_param] = ctx[context_var]
        elif isinstance(mapping, str):
            # Simplified format: "target_param": "source_field" or "context.var_name"
            if mapping.startswith("context."):
                # Get from chain context
                context_var = mapping[8:]  # Remove "context." prefix
                if context_var in ctx:
                    args[target_param] = ctx[context_var]
            else:
                # First try from eval_data (result.result), then from full result
                value = get_nested_value(eval_data, mapping)
                if value is None:
                    value = get_nested_value(result, mapping)
                if value is not None:
                    args[target_param] = value
        else:
            # Direct value assignment (number, boolean, etc.)
            args[target_param] = mapping

    return args


def build_context_from_result(
    save_to_context: Optional[Dict[str, str]],
    result: Dict[str, Any],
    existing_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Extract values from result and add them to chain context.

    Args:
        save_to_context: Mapping of context variable names to result field paths
                        e.g. {"media_id": "media_info.tmdbId", "title": "title"}
        result: The tool execution result
        existing_context: Existing context to merge with

    Returns:
        Updated context with new values
    """
    ctx = dict(existing_context) if existing_context else {}

    if not save_to_context:
        return ctx

    # Extract the actual result data
    eval_data = result.get("result", {}) if isinstance(result.get("result"), dict) else result

    for var_name, field_path in save_to_context.items():
        value = get_nested_value(eval_data, field_path)
        if value is None:
            value = get_nested_value(result, field_path)
        if value is not None:
            ctx[var_name] = value
            logger.debug(f"Saved to context: {var_name} = {value}")

    return ctx


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


def build_action_suggestions(
    actions: List[ToolChainAction],
    result: Dict[str, Any],
    input_params: Optional[Dict[str, Any]],
    chain: ToolChain,
    step: ToolChainStep,
    branch: str,
    success: bool = True,
    chain_context: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Build suggestion list from actions.

    Handles nested CONDITIONAL actions recursively.
    Empty action list = silent end of chain (no suggestions returned).

    Args:
        actions: List of actions to convert to suggestions
        result: The tool execution result
        input_params: Original input parameters
        chain: The parent chain
        step: The parent step
        branch: "then" or "else"
        success: Whether tool execution succeeded
        chain_context: Context with saved variables from previous steps

    Returns:
        List of action suggestions (empty list = silent chain end)
    """
    # Empty actions = silent end of chain
    if not actions:
        return []

    suggestions = []

    for action in sorted(actions, key=lambda a: a.order):
        if not action.enabled:
            continue

        if action.action_type == ActionType.MESSAGE.value:
            # Message action - interpolate template
            message = interpolate_message_template(
                action.message_template or "",
                result,
                input_params,
                chain_context,
            )
            suggestion = {
                "action_type": "message",
                "message": message,
                "_chain_id": str(chain.id),
                "_chain_name": chain.name,
                "_chain_color": chain.color,
                "_step_order": step.order,
                "_branch": branch,
            }
            if action.ai_comment:
                suggestion["reason"] = action.ai_comment
            suggestions.append(suggestion)

        elif action.action_type == ActionType.CONDITIONAL.value:
            # Nested IF/THEN/ELSE - evaluate conditions and recurse
            condition_result = evaluate_action_conditions(action, result, success)

            if condition_result:
                # THEN branch
                nested_actions = action.then_actions
                nested_branch = "then"
            else:
                # ELSE branch
                nested_actions = action.else_actions
                nested_branch = "else"

            # Recursively build suggestions from nested actions
            # Empty nested_actions = silent end of chain (returns empty list)
            nested_suggestions = build_action_suggestions(
                nested_actions,
                result,
                input_params,
                chain,
                step,
                nested_branch,
                success,
                chain_context,
            )
            suggestions.extend(nested_suggestions)

        else:  # TOOL_CALL
            target_service_name = SERVICE_DISPLAY_NAMES.get(action.target_service, action.target_service)
            suggestion = {
                "action_type": "tool_call",
                "tool": action.target_tool,
                "service": action.target_service,
                "service_name": target_service_name,
                "_chain_id": str(chain.id),
                "_chain_name": chain.name,
                "_chain_color": chain.color,
                "_step_order": step.order,
                "_branch": branch,
            }

            # Build suggested arguments if mappings exist
            if action.argument_mappings:
                suggestion["suggested_arguments"] = build_argument_mappings(
                    action.argument_mappings, result, input_params, chain_context
                )

            # Include save_to_context info so AI knows to save result values
            if action.save_to_context:
                suggestion["save_to_context"] = action.save_to_context

            if action.ai_comment:
                suggestion["reason"] = action.ai_comment

            suggestions.append(suggestion)

    return suggestions


async def get_matching_steps(
    session: AsyncSession,
    service_type: str,
    tool_name: str,
    result: Dict[str, Any],
    success: bool,
    input_params: Optional[Dict[str, Any]] = None,
    only_first_step: bool = True,
    chain_context: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Find all steps that match a tool result and evaluate their conditions.

    For each matching step:
    - Evaluate conditions
    - If TRUE: return THEN actions
    - If FALSE: return ELSE actions

    Args:
        session: Database session
        service_type: Service type of the executed tool
        tool_name: Name of the executed tool
        result: The tool execution result
        success: Whether the tool execution was successful
        input_params: Original input parameters
        only_first_step: If True, only evaluate steps at order=0
        chain_context: Context with saved variables from previous steps

    Returns:
        List of action suggestions
    """
    # Build query conditions
    conditions = [
        ToolChainStep.source_service == service_type,
        ToolChainStep.source_tool == tool_name,
        ToolChainStep.enabled is True,
        ToolChain.enabled is True,
    ]

    if only_first_step:
        conditions.append(ToolChainStep.order == 0)

    query = (
        select(ToolChainStep)
        .options(
            selectinload(ToolChainStep.condition_groups).selectinload(ToolChainConditionGroup.conditions),
            selectinload(ToolChainStep.condition_groups).selectinload(ToolChainConditionGroup.child_groups),
            # Load THEN actions with nested conditionals
            selectinload(ToolChainStep.then_actions).selectinload(ToolChainAction.child_actions),
            selectinload(ToolChainStep.then_actions)
            .selectinload(ToolChainAction.condition_groups)
            .selectinload(ToolChainConditionGroup.conditions),
            selectinload(ToolChainStep.then_actions)
            .selectinload(ToolChainAction.condition_groups)
            .selectinload(ToolChainConditionGroup.child_groups),
            # Load ELSE actions with nested conditionals
            selectinload(ToolChainStep.else_actions).selectinload(ToolChainAction.child_actions),
            selectinload(ToolChainStep.else_actions)
            .selectinload(ToolChainAction.condition_groups)
            .selectinload(ToolChainConditionGroup.conditions),
            selectinload(ToolChainStep.else_actions)
            .selectinload(ToolChainAction.condition_groups)
            .selectinload(ToolChainConditionGroup.child_groups),
            selectinload(ToolChainStep.chain),
        )
        .join(ToolChain)
        .where(and_(*conditions))
        .order_by(ToolChain.priority.desc(), ToolChainStep.order)
    )

    db_result = await session.execute(query)
    steps = db_result.scalars().all()

    all_suggestions = []

    for step in steps:
        chain = step.chain

        # Evaluate conditions - returns True (THEN) or False (ELSE)
        condition_result = evaluate_step_conditions(step, result, success)

        if condition_result:
            # Conditions TRUE - get THEN actions
            # Empty then_actions = silent end of chain (returns empty list)
            suggestions = build_action_suggestions(
                step.then_actions, result, input_params, chain, step, "then", success, chain_context
            )
            all_suggestions.extend(suggestions)
        else:
            # Conditions FALSE - get ELSE actions
            # Empty else_actions = silent end of chain (returns empty list)
            suggestions = build_action_suggestions(
                step.else_actions, result, input_params, chain, step, "else", success, chain_context
            )
            all_suggestions.extend(suggestions)

    return all_suggestions


def format_next_actions_for_response(
    suggestions: List[Dict[str, Any]],
    source_tool: str,
) -> Optional[Dict[str, Any]]:
    """Format action suggestions into a response block.

    This will be added to tool responses to guide the AI on what to do next.
    Separates tool_call and message actions.
    """
    if not suggestions:
        return None

    # Extract unique chains from suggestions
    chains_seen = {}
    step_order = None
    branch = None

    for s in suggestions:
        chain_id = s.get("_chain_id")
        if chain_id and chain_id not in chains_seen:
            chains_seen[chain_id] = {
                "id": chain_id,
                "name": s.get("_chain_name"),
                "color": s.get("_chain_color"),
            }
        if step_order is None and "_step_order" in s:
            step_order = s["_step_order"]
        if branch is None and "_branch" in s:
            branch = s["_branch"]

    # Separate tool calls and messages
    next_tools = []
    messages = []

    for s in suggestions:
        # Clean suggestion - remove internal fields
        clean_s = {k: v for k, v in s.items() if not k.startswith("_")}

        if s.get("action_type") == "message":
            messages.append(clean_s)
        else:
            next_tools.append(clean_s)

    response = {
        "chain_context": {
            "position": "start",
            "source_tool": source_tool,
            "branch": branch,
            "chains": list(chains_seen.values()),
            "step_number": (step_order + 1) if step_order is not None else 1,
        },
    }

    if next_tools:
        response["next_tools_to_call"] = next_tools
        response["ai_instruction"] = (
            "Based on the result above and configured tool chains, "
            "you should consider calling these tools next. "
            "Each suggestion includes a reason explaining when/why to use it."
        )

    if messages:
        response["chain_messages"] = messages
        # Add a simple top-level field for the first message
        if messages[0].get("message"):
            response["message_to_display"] = messages[0]["message"]
        if not next_tools:
            response["ai_instruction"] = (
                "Based on the result above and configured tool chains, "
                "please relay the message_to_display to the user."
            )

    return response


async def get_tool_chain_position(
    session: AsyncSession,
    service_type: str,
    tool_name: str,
) -> Optional[Dict[str, Any]]:
    """Check if this tool is an action target in any chain step.

    Returns chain context info if the tool is a target, None otherwise.
    Handles both direct actions (with step_id) and nested actions (with parent_action_id).
    """
    # First, find all actions that target this tool (regardless of nesting level)
    action_query = (
        select(ToolChainAction)
        .options(
            selectinload(ToolChainAction.step).selectinload(ToolChainStep.chain),
            selectinload(ToolChainAction.parent_action)
            .selectinload(ToolChainAction.step)
            .selectinload(ToolChainStep.chain),
        )
        .where(
            and_(
                ToolChainAction.target_service == service_type,
                ToolChainAction.target_tool == tool_name,
                ToolChainAction.enabled is True,
            )
        )
    )

    action_result = await session.execute(action_query)
    all_actions = action_result.scalars().all()

    # Filter to only enabled chains/steps by traversing up to the step
    actions = []
    for action in all_actions:
        # Get the step (either direct or through parent chain)
        step = action.step
        if not step and action.parent_action:
            # Nested action - traverse up to find the step
            parent = action.parent_action
            while parent and not parent.step:
                parent = parent.parent_action
            if parent:
                step = parent.step

        if step and step.enabled:
            chain = step.chain
            if chain and chain.enabled:
                # Store both the action and its resolved step
                action._resolved_step = step
                actions.append(action)

    if not actions:
        return None

    # This tool is an action target - determine position
    chains_info = []

    for action in actions:
        step = getattr(action, "_resolved_step", action.step)
        if not step:
            continue
        chain = step.chain

        # Find the step that uses this tool as SOURCE (the step we're about to execute)
        source_step_query = select(ToolChainStep).where(
            and_(
                ToolChainStep.chain_id == chain.id,
                ToolChainStep.source_service == service_type,
                ToolChainStep.source_tool == tool_name,
                ToolChainStep.enabled is True,
            )
        )
        source_step_result = await session.execute(source_step_query)
        source_step = source_step_result.scalar()

        if source_step:
            # Use the source step's position type
            pos = "end" if source_step.position_type == StepPositionType.END.value else "middle"
            step_order = source_step.order
        else:
            # No source step found - this tool is just a target, use action's step info
            pos = "end" if step.position_type == StepPositionType.END.value else "middle"
            step_order = step.order

        chains_info.append(
            {
                "id": str(chain.id),
                "name": chain.name,
                "color": chain.color,
                "position": pos,
                "previous_step_order": step_order,
                "source_tool": step.source_tool,
                "branch": action.branch,
            }
        )

    if not chains_info:
        return None

    # Use the first chain's position
    primary = chains_info[0]
    step_number = primary["previous_step_order"] + 2  # Next step number

    return {
        "position": primary["position"],
        "source_tool": primary["source_tool"],
        "branch": primary["branch"],
        "step_number": step_number,
        "chains": [{"id": c["id"], "name": c["name"], "color": c["color"]} for c in chains_info],
    }


async def check_recent_chain_flow(
    session: AsyncSession,
    service_type: str,
    tool_name: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    time_window_seconds: int = 300,
) -> Optional[Dict[str, Any]]:
    """Check if this tool was called as part of a chain flow by looking at recent history.

    Looks at the most recent MCP request FROM THE SAME USER/SESSION to see if it
    was a tool that has this tool as an action target in a chain step.

    Args:
        session: Database session
        service_type: Service type of the current tool
        tool_name: Name of the current tool
        session_id: Session ID to filter by (for multi-user support)
        user_id: User ID to filter by (fallback if no session_id)
        time_window_seconds: How far back to look for previous calls

    Returns:
        Chain context if this tool follows a chain flow, None otherwise.
        Includes 'save_to_context' from the action that suggested this tool,
        and 'previous_result' to extract values from.
    """
    from datetime import datetime, timedelta

    from src.models.mcp_request import McpRequest, McpRequestStatus

    time_threshold = datetime.utcnow() - timedelta(seconds=time_window_seconds)

    conditions = [
        McpRequest.status == McpRequestStatus.COMPLETED,
        McpRequest.created_at >= time_threshold,
    ]

    if session_id:
        conditions.append(McpRequest.session_id == session_id)
    elif user_id:
        conditions.append(McpRequest.user_id == user_id)

    # Get recent requests (not just the last one, as it might be the current tool)
    recent_query = (
        select(McpRequest)
        .where(and_(*conditions))
        .order_by(McpRequest.created_at.desc())
        .limit(10)  # Check last 10 requests
    )

    recent_result = await session.execute(recent_query)
    recent_requests = recent_result.scalars().all()

    if not recent_requests:
        return None

    # Look through recent requests for one that suggests this tool
    for recent_request in recent_requests:
        # Skip if this is the same tool (could be the current request already saved)
        if recent_request.tool_name == tool_name:
            continue

        previous_result = recent_request.output_result or {}
        next_tools = previous_result.get("next_tools_to_call", [])

        for next_tool in next_tools:
            if next_tool.get("tool") == tool_name:
                chain_context = previous_result.get("chain_context", {})
                return {
                    "is_chain_flow": True,
                    "previous_tool": recent_request.tool_name,
                    "chain_context": chain_context,
                    # Include save_to_context from the action that suggested this tool
                    "save_to_context": next_tool.get("save_to_context"),
                    # Include the previous tool's result to extract values from
                    "previous_result": previous_result,
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
    """Add next action suggestions to a tool result if matching chains exist.

    This function should be called after tool execution to add
    chain suggestions to the response.

    Chain flow detection (automatic):
    - Checks recent MCP history to see if the previous tool suggested this one
    - If yes, this tool is part of a chain flow (middle or end position)
    - If not, only first steps (order=0) are evaluated

    Multi-user support:
    - Uses session_id or user_id to filter history

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
        "plex_",
        "overseerr_",
        "zammad_",
        "tautulli_",
        "openwebui_",
        "radarr_",
        "sonarr_",
        "prowlarr_",
        "jackett_",
        "deluge_",
        "komga_",
        "romm_",
        "audiobookshelf_",
        "wikijs_",
        "authentik_",
        "system_",
    ]

    for prefix in prefixes:
        if tool_name.startswith(prefix):
            service_type = prefix.rstrip("_")
            break

    if not service_type:
        return result

    success = result.get("success", False)

    try:
        # Check if this tool is part of a chain flow
        chain_flow = await check_recent_chain_flow(
            session, service_type, tool_name, session_id=session_id, user_id=user_id
        )

        if chain_flow and chain_flow.get("is_chain_flow"):
            # This tool was called as part of a chain flow
            logger.info(f"Tool '{tool_name}' is part of chain flow (preceded by '{chain_flow['previous_tool']}')")

            # Get saved variables from previous chain context
            previous_context = chain_flow.get("chain_context", {})
            saved_variables = dict(previous_context.get("variables", {}))

            # Extract values from previous result if save_to_context was configured
            previous_save_to_context = chain_flow.get("save_to_context")
            previous_result = chain_flow.get("previous_result", {})
            if previous_save_to_context and previous_result:
                # Use build_context_from_result to extract actual values
                saved_variables = build_context_from_result(
                    previous_save_to_context,
                    previous_result,
                    saved_variables,
                )
                logger.info(f"Extracted context variables from previous result: {saved_variables}")

            existing_position = await get_tool_chain_position(session, service_type, tool_name)

            if existing_position:
                result["chain_context"] = existing_position
                # Preserve saved variables in context
                if saved_variables:
                    result["chain_context"]["variables"] = saved_variables

                if existing_position["position"] == "middle":
                    # Evaluate next step conditions
                    middle_suggestions = await get_matching_steps(
                        session,
                        service_type,
                        tool_name,
                        result,
                        success,
                        input_params,
                        only_first_step=False,
                        chain_context=saved_variables,
                    )
                    if middle_suggestions:
                        next_block = format_next_actions_for_response(middle_suggestions, tool_name)
                        if next_block:
                            next_block["chain_context"]["position"] = "middle"
                            # Preserve saved variables
                            if saved_variables:
                                next_block["chain_context"]["variables"] = saved_variables
                            result.update(next_block)
                            logger.info(
                                f"Added {len(middle_suggestions)} action suggestions to '{tool_name}' (middle step)"
                            )
                else:
                    # End of chain - still need to evaluate conditions and return messages
                    end_suggestions = await get_matching_steps(
                        session,
                        service_type,
                        tool_name,
                        result,
                        success,
                        input_params,
                        only_first_step=False,
                        chain_context=saved_variables,
                    )
                    if end_suggestions:
                        next_block = format_next_actions_for_response(end_suggestions, tool_name)
                        if next_block:
                            next_block["chain_context"]["position"] = "end"
                            # Preserve saved variables
                            if saved_variables:
                                next_block["chain_context"]["variables"] = saved_variables
                            result.update(next_block)
                            logger.info(f"Added {len(end_suggestions)} action suggestions to '{tool_name}' (end step)")
                    else:
                        # No suggestions but still mark as end of chain
                        result["chain_context"] = existing_position
                        if saved_variables:
                            result["chain_context"]["variables"] = saved_variables
                        logger.info(
                            f"Tool '{tool_name}' is end of chain(s): "
                            f"{[c['name'] for c in existing_position['chains']]}"
                        )
        else:
            # Not part of a chain flow - only evaluate first steps
            suggestions = await get_matching_steps(
                session, service_type, tool_name, result, success, input_params, only_first_step=True
            )

            if suggestions:
                next_block = format_next_actions_for_response(suggestions, tool_name)
                if next_block:
                    result.update(next_block)
                    logger.info(f"Added {len(suggestions)} action suggestions to '{tool_name}' result")

    except Exception as e:
        logger.error(f"Error evaluating tool chains for '{tool_name}': {e}")

    return result
