"""Tool Chain schemas for API validation and serialization."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.models.tool_chain import ConditionOperator, ExecutionMode


# === Step Target Schemas (tools to execute) ===


class StepTargetCreate(BaseModel):
    """Schema for creating a target tool in a step."""

    target_service: str = Field(..., description="Target service type (e.g., 'overseerr')")
    target_tool: str = Field(..., description="Target tool name to execute")
    order: int = Field(0, description="Execution order")
    execution_mode: ExecutionMode = Field(
        ExecutionMode.SEQUENTIAL, description="How to execute relative to other targets"
    )
    argument_mappings: Optional[Dict[str, Any]] = Field(
        None, description="Input argument mappings from source result"
    )
    target_ai_comment: Optional[str] = Field(
        None, description="AI guidance for this specific target"
    )
    enabled: bool = Field(True, description="Whether this target is active")


class StepTargetUpdate(BaseModel):
    """Schema for updating a step target."""

    target_service: Optional[str] = None
    target_tool: Optional[str] = None
    order: Optional[int] = None
    execution_mode: Optional[ExecutionMode] = None
    argument_mappings: Optional[Dict[str, Any]] = None
    target_ai_comment: Optional[str] = None
    enabled: Optional[bool] = None


class StepTargetResponse(BaseModel):
    """Schema for step target API responses."""

    id: str
    step_id: str
    target_service: str
    target_tool: str
    order: int
    execution_mode: str
    argument_mappings: Optional[Dict[str, Any]]
    target_ai_comment: Optional[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime
    # Enriched info
    target_service_name: Optional[str] = None
    target_tool_display_name: Optional[str] = None


# === Tool Chain Step Schemas ===


class ToolChainStepCreate(BaseModel):
    """Schema for creating a step in a tool chain."""

    order: int = Field(0, description="Step order within the chain")
    # Source tool (trigger)
    source_service: str = Field(..., description="Source service type that triggers this step")
    source_tool: str = Field(..., description="Source tool name that triggers this step")
    # Condition
    condition_operator: ConditionOperator = Field(
        ConditionOperator.SUCCESS, description="Condition operator"
    )
    condition_field: Optional[str] = Field(
        None, description="Field path in result to check"
    )
    condition_value: Optional[str] = Field(
        None, description="Value to compare against"
    )
    # AI guidance
    ai_comment: Optional[str] = Field(
        None, description="AI guidance explaining when/why to use this step"
    )
    enabled: bool = Field(True, description="Whether this step is active")
    # Optional: create targets on step creation
    targets: Optional[List[StepTargetCreate]] = Field(
        None, description="Target tools to create with the step"
    )


class ToolChainStepUpdate(BaseModel):
    """Schema for updating a tool chain step."""

    order: Optional[int] = None
    source_service: Optional[str] = None
    source_tool: Optional[str] = None
    condition_operator: Optional[ConditionOperator] = None
    condition_field: Optional[str] = None
    condition_value: Optional[str] = None
    ai_comment: Optional[str] = None
    enabled: Optional[bool] = None


class ToolChainStepResponse(BaseModel):
    """Schema for tool chain step API responses."""

    id: str
    chain_id: str
    order: int
    source_service: str
    source_tool: str
    condition_operator: str
    condition_field: Optional[str]
    condition_value: Optional[str]
    ai_comment: Optional[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime
    # Computed
    target_count: int = 0
    # Enriched info
    source_service_name: Optional[str] = None
    source_tool_display_name: Optional[str] = None


class ToolChainStepDetailResponse(ToolChainStepResponse):
    """Detailed step response with targets."""

    targets: List[StepTargetResponse] = []


# === Tool Chain Schemas ===


class ToolChainCreate(BaseModel):
    """Schema for creating a new tool chain."""

    name: str = Field(..., description="Chain name")
    description: Optional[str] = Field(None, description="Chain description")
    color: str = Field("#8b5cf6", description="Chain color (hex)")
    priority: int = Field(0, description="Priority for chain matching")
    enabled: bool = Field(True, description="Whether chain is active")
    # Optional: create steps on chain creation
    steps: Optional[List[ToolChainStepCreate]] = Field(
        None, description="Steps to create with the chain"
    )


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
            value="gte", label="Greater or Equal", description="Result is greater than or equal to value",
            requires_value=True, requires_field=True
        ),
        ConditionOperatorInfo(
            value="lte", label="Less or Equal", description="Result is less than or equal to value",
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


# === Tool Chain Execution Context (for AI responses) ===


class TargetSuggestion(BaseModel):
    """A suggested target tool to execute."""

    target_service: str
    target_tool: str
    suggested_arguments: Optional[Dict[str, Any]] = None
    ai_comment: Optional[str] = None
    execution_mode: str = "sequential"


class StepSuggestion(BaseModel):
    """A suggested step based on matching condition."""

    chain_id: str
    chain_name: str
    step_id: str
    ai_comment: Optional[str] = None
    targets: List[TargetSuggestion] = []


class ChainExecutionContext(BaseModel):
    """Context information about chains that may apply to a tool result.

    This is included in tool responses to guide the AI about potential
    next steps based on configured tool chains.
    """

    source_service: str
    source_tool: str
    matching_steps: List[StepSuggestion] = []
    has_suggestions: bool = False

    @classmethod
    def empty(cls, source_service: str, source_tool: str) -> "ChainExecutionContext":
        """Create empty context (no matching steps)."""
        return cls(
            source_service=source_service,
            source_tool=source_tool,
            matching_steps=[],
            has_suggestions=False,
        )


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
