"""Tool Chain schemas for API validation and serialization.

Supports IF/THEN/ELSE logic with compound conditions (AND/OR).
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.models.tool_chain import (
    ActionType,
    ConditionGroupOperator,
    ConditionOperator,
    ExecutionMode,
    StepPositionType,
)


# === Condition Schemas ===


class ConditionCreate(BaseModel):
    """Schema for creating a single condition."""

    operator: ConditionOperator = Field(..., description="Condition operator")
    field: Optional[str] = Field(None, description="Field path in result to check (e.g., 'result.count')")
    value: Optional[str] = Field(None, description="Value to compare against")
    order: int = Field(0, description="Order within the group")


class ConditionUpdate(BaseModel):
    """Schema for updating a condition."""

    operator: Optional[ConditionOperator] = None
    field: Optional[str] = None
    value: Optional[str] = None
    order: Optional[int] = None


class ConditionResponse(BaseModel):
    """Schema for condition API responses."""

    id: str
    group_id: str
    operator: str
    field: Optional[str]
    value: Optional[str]
    order: int
    created_at: datetime
    updated_at: datetime


# === Condition Group Schemas ===


class ConditionGroupCreate(BaseModel):
    """Schema for creating a condition group with AND/OR logic."""

    operator: ConditionGroupOperator = Field(
        ConditionGroupOperator.AND, description="How conditions are combined (and/or)"
    )
    order: int = Field(0, description="Order within parent group or step")
    conditions: List[ConditionCreate] = Field(default_factory=list, description="Conditions in this group")
    child_groups: Optional[List["ConditionGroupCreate"]] = Field(
        None, description="Nested condition groups for complex expressions"
    )


class ConditionGroupUpdate(BaseModel):
    """Schema for updating a condition group."""

    operator: Optional[ConditionGroupOperator] = None
    order: Optional[int] = None


class ConditionGroupResponse(BaseModel):
    """Schema for condition group API responses."""

    id: str
    step_id: Optional[str] = None
    action_id: Optional[str] = None  # For nested conditionals
    parent_group_id: Optional[str] = None
    operator: str
    order: int
    created_at: datetime
    updated_at: datetime
    conditions: List[ConditionResponse] = []
    child_groups: List["ConditionGroupResponse"] = []


# === Action Schemas (for THEN/ELSE branches) ===


class ActionCreate(BaseModel):
    """Schema for creating an action in THEN or ELSE branch.

    Action types:
    - tool_call: Execute a tool
    - message: Display a message
    - conditional: Nested IF/THEN/ELSE block
    """

    branch: str = Field(..., description="Branch type: 'then' or 'else'")
    action_type: ActionType = Field(ActionType.TOOL_CALL, description="Action type")
    # For tool_call action
    target_service: Optional[str] = Field(None, description="Target service type")
    target_tool: Optional[str] = Field(None, description="Target tool name")
    argument_mappings: Optional[Dict[str, Any]] = Field(
        None, description="Input argument mappings from source result"
    )
    # For message action
    message_template: Optional[str] = Field(
        None, description="Message template with placeholders like {result.title}"
    )
    # For conditional action (nested IF/THEN/ELSE)
    condition_groups: Optional[List[ConditionGroupCreate]] = Field(
        None, description="Condition groups for nested IF (only for conditional action)"
    )
    then_actions: Optional[List["ActionCreate"]] = Field(
        None, description="Nested THEN actions (only for conditional action). Empty = silent end of chain."
    )
    else_actions: Optional[List["ActionCreate"]] = Field(
        None, description="Nested ELSE actions (only for conditional action). Empty = silent end of chain."
    )
    # Common
    order: int = Field(0, description="Execution order")
    execution_mode: ExecutionMode = Field(ExecutionMode.SEQUENTIAL, description="Execution mode")
    ai_comment: Optional[str] = Field(None, description="AI guidance for this action")
    enabled: bool = Field(True, description="Whether this action is active")


class ActionUpdate(BaseModel):
    """Schema for updating an action."""

    action_type: Optional[ActionType] = None
    target_service: Optional[str] = None
    target_tool: Optional[str] = None
    argument_mappings: Optional[Dict[str, Any]] = None
    message_template: Optional[str] = None
    order: Optional[int] = None
    execution_mode: Optional[ExecutionMode] = None
    ai_comment: Optional[str] = None
    enabled: Optional[bool] = None


class ActionResponse(BaseModel):
    """Schema for action API responses."""

    id: str
    step_id: Optional[str] = None  # Null for nested actions
    parent_action_id: Optional[str] = None  # For nested actions
    branch: str
    action_type: str
    target_service: Optional[str] = None
    target_tool: Optional[str] = None
    argument_mappings: Optional[Dict[str, Any]] = None
    message_template: Optional[str] = None
    order: int
    execution_mode: str
    ai_comment: Optional[str] = None
    enabled: bool
    created_at: datetime
    updated_at: datetime
    # Enriched info
    target_service_name: Optional[str] = None
    target_tool_display_name: Optional[str] = None
    # For conditional actions - nested structure
    condition_groups: List[ConditionGroupResponse] = []
    then_actions: List["ActionResponse"] = []
    else_actions: List["ActionResponse"] = []


# === Tool Chain Step Schemas ===


class ToolChainStepCreate(BaseModel):
    """Schema for creating a step in a tool chain."""

    order: int = Field(0, description="Step order within the chain")
    position_type: StepPositionType = Field(
        StepPositionType.MIDDLE, description="Step position type (middle or end)"
    )
    # Source tool (trigger)
    source_service: str = Field(..., description="Source service type that triggers this step")
    source_tool: str = Field(..., description="Source tool name that triggers this step")
    # AI guidance
    ai_comment: Optional[str] = Field(None, description="AI guidance explaining when/why to use this step")
    enabled: bool = Field(True, description="Whether this step is active")
    # Conditions (at least one group required)
    condition_groups: List[ConditionGroupCreate] = Field(
        default_factory=list, description="Condition groups for this step"
    )
    # THEN actions (executed when condition is TRUE)
    then_actions: List[ActionCreate] = Field(default_factory=list, description="Actions when condition is true")
    # ELSE actions (executed when condition is FALSE)
    else_actions: List[ActionCreate] = Field(default_factory=list, description="Actions when condition is false")


class ToolChainStepUpdate(BaseModel):
    """Schema for updating a tool chain step."""

    order: Optional[int] = None
    position_type: Optional[StepPositionType] = None
    source_service: Optional[str] = None
    source_tool: Optional[str] = None
    ai_comment: Optional[str] = None
    enabled: Optional[bool] = None


class ToolChainStepResponse(BaseModel):
    """Schema for tool chain step API responses."""

    id: str
    chain_id: str
    order: int
    position_type: str
    source_service: str
    source_tool: str
    ai_comment: Optional[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime
    # Computed counts
    condition_count: int = 0
    then_action_count: int = 0
    else_action_count: int = 0
    # Enriched info
    source_service_name: Optional[str] = None
    source_tool_display_name: Optional[str] = None


class ToolChainStepDetailResponse(ToolChainStepResponse):
    """Detailed step response with conditions and actions."""

    condition_groups: List[ConditionGroupResponse] = []
    then_actions: List[ActionResponse] = []
    else_actions: List[ActionResponse] = []


# === Tool Chain Schemas ===


class ToolChainCreate(BaseModel):
    """Schema for creating a new tool chain."""

    name: str = Field(..., description="Chain name")
    description: Optional[str] = Field(None, description="Chain description")
    color: str = Field("#8b5cf6", description="Chain color (hex)")
    priority: int = Field(0, description="Priority for chain matching")
    enabled: bool = Field(True, description="Whether chain is active")
    # Optional: create steps on chain creation
    steps: Optional[List[ToolChainStepCreate]] = Field(None, description="Steps to create with the chain")


class ToolChainUpdate(BaseModel):
    """Schema for updating an existing tool chain."""

    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None


class ToolChainResponse(BaseModel):
    """Schema for tool chain API responses."""

    id: str
    name: str
    description: Optional[str]
    color: str
    priority: int
    enabled: bool
    created_at: datetime
    updated_at: datetime
    # Computed fields
    step_count: int = 0


class ToolChainDetailResponse(ToolChainResponse):
    """Detailed tool chain response with steps."""

    steps: List[ToolChainStepDetailResponse] = []


class ToolChainListResponse(BaseModel):
    """Schema for paginated tool chain list responses."""

    chains: List[ToolChainResponse]
    total: int
    skip: int
    limit: int


# === Condition Operators Reference ===


class ConditionOperatorInfo(BaseModel):
    """Information about a condition operator."""

    value: str
    label: str
    description: str
    requires_value: bool
    requires_field: bool


class ConditionOperatorsResponse(BaseModel):
    """List of available condition operators."""

    operators: List[ConditionOperatorInfo] = [
        ConditionOperatorInfo(
            value="eq", label="Equals", description="Result equals value",
            requires_value=True, requires_field=True
        ),
        ConditionOperatorInfo(
            value="ne", label="Not Equals", description="Result does not equal value",
            requires_value=True, requires_field=True
        ),
        ConditionOperatorInfo(
            value="gt", label="Greater Than", description="Result is greater than value",
            requires_value=True, requires_field=True
        ),
        ConditionOperatorInfo(
            value="lt", label="Less Than", description="Result is less than value",
            requires_value=True, requires_field=True
        ),
        ConditionOperatorInfo(
            value="gte", label="Greater or Equal", description="Result >= value",
            requires_value=True, requires_field=True
        ),
        ConditionOperatorInfo(
            value="lte", label="Less or Equal", description="Result <= value",
            requires_value=True, requires_field=True
        ),
        ConditionOperatorInfo(
            value="contains", label="Contains", description="Result contains value",
            requires_value=True, requires_field=True
        ),
        ConditionOperatorInfo(
            value="not_contains", label="Not Contains", description="Result does not contain value",
            requires_value=True, requires_field=True
        ),
        ConditionOperatorInfo(
            value="is_empty", label="Is Empty", description="Result is empty or null",
            requires_value=False, requires_field=True
        ),
        ConditionOperatorInfo(
            value="is_not_empty", label="Is Not Empty", description="Result is not empty",
            requires_value=False, requires_field=True
        ),
        ConditionOperatorInfo(
            value="success", label="Success", description="Tool execution succeeded",
            requires_value=False, requires_field=False
        ),
        ConditionOperatorInfo(
            value="failed", label="Failed", description="Tool execution failed",
            requires_value=False, requires_field=False
        ),
        ConditionOperatorInfo(
            value="regex", label="Regex Match", description="Result matches regex pattern",
            requires_value=True, requires_field=True
        ),
    ]


# === Condition Group Operators Reference ===


class ConditionGroupOperatorInfo(BaseModel):
    """Information about a condition group operator."""

    value: str
    label: str
    description: str


class ConditionGroupOperatorsResponse(BaseModel):
    """List of available group operators."""

    operators: List[ConditionGroupOperatorInfo] = [
        ConditionGroupOperatorInfo(
            value="and", label="AND", description="All conditions must be true"
        ),
        ConditionGroupOperatorInfo(
            value="or", label="OR", description="At least one condition must be true"
        ),
    ]


# === Action Types Reference ===


class ActionTypeInfo(BaseModel):
    """Information about an action type."""

    value: str
    label: str
    description: str


class ActionTypesResponse(BaseModel):
    """List of available action types."""

    action_types: List[ActionTypeInfo] = [
        ActionTypeInfo(
            value="tool_call", label="Call Tool", description="Execute a tool"
        ),
        ActionTypeInfo(
            value="message", label="Display Message", description="Display a message to AI (no tool call)"
        ),
    ]


# === Step Position Types Reference ===


class StepPositionInfo(BaseModel):
    """Information about step position type."""

    value: str
    label: str
    description: str


class StepPositionTypesResponse(BaseModel):
    """List of available step positions."""

    positions: List[StepPositionInfo] = [
        StepPositionInfo(
            value="middle", label="Middle", description="Continue to next steps"
        ),
        StepPositionInfo(
            value="end", label="End", description="Terminal step (chain ends here)"
        ),
    ]


# === Flowchart Data for Visualization ===


class FlowchartNode(BaseModel):
    """A node in the flowchart visualization."""

    id: str
    type: str  # 'step', 'condition', 'action', 'message'
    label: str
    data: Dict[str, Any] = {}
    position: Dict[str, float] = {"x": 0, "y": 0}


class FlowchartEdge(BaseModel):
    """An edge connecting nodes in the flowchart."""

    id: str
    source: str
    target: str
    label: Optional[str] = None  # 'TRUE', 'FALSE'
    type: str = "default"  # 'then', 'else', 'default'


class FlowchartResponse(BaseModel):
    """Flowchart data for visualization."""

    chain_id: str
    chain_name: str
    nodes: List[FlowchartNode] = []
    edges: List[FlowchartEdge] = []


# === Available Tools for Chain Configuration ===


class AvailableTool(BaseModel):
    """Information about a tool available for chain configuration."""

    service_type: str
    service_name: str
    tool_name: str
    tool_display_name: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class AvailableToolsResponse(BaseModel):
    """List of available tools for chain configuration."""

    tools: List[AvailableTool]
    total: int


# === Tool Chain Execution Context (for AI responses) ===


class ActionSuggestion(BaseModel):
    """A suggested action to execute."""

    action_type: str
    # For tool_call
    target_service: Optional[str] = None
    target_tool: Optional[str] = None
    service_name: Optional[str] = None
    suggested_arguments: Optional[Dict[str, Any]] = None
    # For message
    message: Optional[str] = None
    # Common
    ai_comment: Optional[str] = None
    reason: Optional[str] = None


class ChainContext(BaseModel):
    """Context about chain execution for AI."""

    position: str  # 'start', 'middle', 'end'
    source_tool: str
    branch: Optional[str] = None  # 'then' or 'else'
    chains: List[Dict[str, Any]] = []
    step_number: int = 1


# Update forward references
ConditionGroupCreate.model_rebuild()
ConditionGroupResponse.model_rebuild()
