"""Tool Chain models for defining conditional tool execution sequences."""

from enum import Enum
from typing import List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class ConditionOperator(str, Enum):
    """Operators for evaluating tool chain conditions."""

    EQUALS = "eq"           # result == value
    NOT_EQUALS = "ne"       # result != value
    GREATER_THAN = "gt"     # result > value
    LESS_THAN = "lt"        # result < value
    GREATER_OR_EQUAL = "gte"  # result >= value
    LESS_OR_EQUAL = "lte"   # result <= value
    CONTAINS = "contains"   # value in result
    NOT_CONTAINS = "not_contains"  # value not in result
    IS_EMPTY = "is_empty"   # result is empty/null
    IS_NOT_EMPTY = "is_not_empty"  # result is not empty
    SUCCESS = "success"     # tool execution succeeded
    FAILED = "failed"       # tool execution failed
    REGEX_MATCH = "regex"   # result matches regex pattern


class ExecutionMode(str, Enum):
    """How to execute multiple target tools in a step."""

    SEQUENTIAL = "sequential"  # Execute tools one after another
    PARALLEL = "parallel"      # Execute all tools at once


class ToolChain(Base, UUIDMixin, TimestampMixin):
    """A chain definition - a container for conditional tool execution steps.

    Tool chains allow users to define automatic workflows where the
    result of one tool triggers the execution of other tools.
    Each step in the chain has its own trigger condition.
    """

    __tablename__ = "tool_chains"

    # Chain identity
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Visual customization
    color: Mapped[str] = mapped_column(String(20), default="#8b5cf6", nullable=False)  # Purple default

    # Priority for ordering when multiple chains could apply
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Chain status
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    steps: Mapped[List["ToolChainStep"]] = relationship(
        "ToolChainStep", back_populates="chain", cascade="all, delete-orphan",
        order_by="ToolChainStep.order"
    )

    def __repr__(self) -> str:
        return f"<ToolChain(id={self.id}, name={self.name})>"


class ToolChainStep(Base, UUIDMixin, TimestampMixin):
    """A step in a tool chain - defines a trigger condition and target tools.

    Each step specifies:
    - Source tool that triggers this step (when its result matches the condition)
    - Condition to evaluate on the source tool's result
    - One or more target tools to execute when condition matches
    - AI guidance for when to follow this step
    """

    __tablename__ = "tool_chain_steps"

    # Parent chain
    chain_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tool_chains.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Step order within the chain (for display)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Source tool (the trigger) - when this tool is called and condition matches
    source_service: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_tool: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Condition for triggering this step
    condition_operator: Mapped[str] = mapped_column(
        String(20), default=ConditionOperator.SUCCESS.value, nullable=False
    )
    condition_field: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # Field path in result to check (e.g., "count", "data.status")
    condition_value: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Value to compare against

    # AI guidance - explains when/why to use this step
    ai_comment: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # e.g., "If a movie is found, offer to request it via Overseerr"

    # Step status
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    chain: Mapped["ToolChain"] = relationship("ToolChain", back_populates="steps")
    target_tools: Mapped[List["ToolChainStepTarget"]] = relationship(
        "ToolChainStepTarget", back_populates="step", cascade="all, delete-orphan",
        order_by="ToolChainStepTarget.order"
    )

    def __repr__(self) -> str:
        return f"<ToolChainStep(chain_id={self.chain_id}, source={self.source_service}.{self.source_tool})>"


class ToolChainStepTarget(Base, UUIDMixin, TimestampMixin):
    """A target tool to execute when a step's condition is met.

    Multiple targets can be defined per step, executed sequentially or in parallel.
    """

    __tablename__ = "tool_chain_step_targets"

    # Parent step
    step_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tool_chain_steps.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Target tool to execute
    target_service: Mapped[str] = mapped_column(String(50), nullable=False)
    target_tool: Mapped[str] = mapped_column(String(100), nullable=False)

    # Execution order (for sequential mode)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Execution mode
    execution_mode: Mapped[str] = mapped_column(
        String(20), default=ExecutionMode.SEQUENTIAL.value, nullable=False
    )

    # Input argument mappings - JSON object mapping target param names to source values
    # Format: {"target_param": {"source": "result.field.path"}} or {"target_param": {"value": "static_value"}}
    # Special sources:
    #   - "result" - entire result from source tool
    #   - "result.field" - specific field from result
    #   - "input.param" - original input parameter from source tool
    argument_mappings: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )

    # AI comment specific to this target
    target_ai_comment: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # e.g., "Request this movie on Overseerr"

    # Target status
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    step: Mapped["ToolChainStep"] = relationship("ToolChainStep", back_populates="target_tools")

    def __repr__(self) -> str:
        return f"<ToolChainStepTarget(step_id={self.step_id}, target={self.target_service}.{self.target_tool})>"
