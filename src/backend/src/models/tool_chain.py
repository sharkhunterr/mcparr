"""Tool Chain models for defining conditional IF/THEN/ELSE tool execution sequences."""

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


class ConditionGroupOperator(str, Enum):
    """Logical operators for combining conditions in a group."""

    AND = "and"  # All conditions must be true
    OR = "or"    # At least one condition must be true


class ActionType(str, Enum):
    """Type of action for THEN/ELSE branches."""

    TOOL_CALL = "tool_call"  # Execute a tool
    MESSAGE = "message"       # Display a message to AI (no tool call)


class ExecutionMode(str, Enum):
    """How to execute multiple actions in a branch."""

    SEQUENTIAL = "sequential"  # Execute actions one after another
    PARALLEL = "parallel"      # Execute all actions at once


class StepPositionType(str, Enum):
    """Position type of a step in the chain flow."""

    MIDDLE = "middle"  # Continue to next steps after this one
    END = "end"        # Terminal step (no continuation expected)


class ToolChain(Base, UUIDMixin, TimestampMixin):
    """A chain definition - a container for conditional IF/THEN/ELSE steps.

    Tool chains allow users to define automatic workflows where the
    result of one tool triggers different actions based on conditions.
    """

    __tablename__ = "tool_chains"

    # Chain identity
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Visual customization
    color: Mapped[str] = mapped_column(String(20), default="#8b5cf6", nullable=False)

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
    """A step in a tool chain with IF/THEN/ELSE logic.

    Each step specifies:
    - Source tool that triggers this step
    - Conditions to evaluate (simple or compound with AND/OR)
    - THEN actions to execute when condition is TRUE
    - ELSE actions to execute when condition is FALSE
    """

    __tablename__ = "tool_chain_steps"

    # Parent chain
    chain_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tool_chains.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Step order within the chain (0 = start)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Step position type (middle or end)
    position_type: Mapped[str] = mapped_column(
        String(20), default=StepPositionType.MIDDLE.value, nullable=False
    )

    # Source tool (the trigger)
    source_service: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_tool: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # AI guidance - explains when/why to use this step
    ai_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Step status
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    chain: Mapped["ToolChain"] = relationship("ToolChain", back_populates="steps")
    condition_groups: Mapped[List["ToolChainConditionGroup"]] = relationship(
        "ToolChainConditionGroup", back_populates="step", cascade="all, delete-orphan",
        order_by="ToolChainConditionGroup.order",
        foreign_keys="ToolChainConditionGroup.step_id"
    )
    then_actions: Mapped[List["ToolChainAction"]] = relationship(
        "ToolChainAction", back_populates="step", cascade="all, delete-orphan",
        order_by="ToolChainAction.order",
        primaryjoin="and_(ToolChainStep.id==ToolChainAction.step_id, ToolChainAction.branch=='then')"
    )
    else_actions: Mapped[List["ToolChainAction"]] = relationship(
        "ToolChainAction", back_populates="step", cascade="all, delete-orphan",
        order_by="ToolChainAction.order",
        primaryjoin="and_(ToolChainStep.id==ToolChainAction.step_id, ToolChainAction.branch=='else')",
        viewonly=True
    )

    def __repr__(self) -> str:
        return f"<ToolChainStep(chain_id={self.chain_id}, source={self.source_service}.{self.source_tool})>"


class ToolChainConditionGroup(Base, UUIDMixin, TimestampMixin):
    """A group of conditions combined with AND/OR logic.

    Supports nested groups for complex expressions like:
    (A AND B) OR (C AND D)
    """

    __tablename__ = "tool_chain_condition_groups"

    # Parent step
    step_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tool_chain_steps.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Parent group (for nested conditions, NULL if root)
    parent_group_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("tool_chain_condition_groups.id", ondelete="CASCADE"),
        nullable=True, index=True
    )

    # How conditions in this group are combined
    operator: Mapped[str] = mapped_column(
        String(10), default=ConditionGroupOperator.AND.value, nullable=False
    )

    # Order within parent group (for display)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    step: Mapped["ToolChainStep"] = relationship(
        "ToolChainStep", back_populates="condition_groups",
        foreign_keys=[step_id]
    )
    parent_group: Mapped[Optional["ToolChainConditionGroup"]] = relationship(
        "ToolChainConditionGroup", remote_side="ToolChainConditionGroup.id",
        back_populates="child_groups", foreign_keys=[parent_group_id]
    )
    child_groups: Mapped[List["ToolChainConditionGroup"]] = relationship(
        "ToolChainConditionGroup", back_populates="parent_group",
        cascade="all, delete-orphan", foreign_keys="ToolChainConditionGroup.parent_group_id"
    )
    conditions: Mapped[List["ToolChainCondition"]] = relationship(
        "ToolChainCondition", back_populates="group", cascade="all, delete-orphan",
        order_by="ToolChainCondition.order"
    )

    def __repr__(self) -> str:
        return f"<ToolChainConditionGroup(step_id={self.step_id}, operator={self.operator})>"


class ToolChainCondition(Base, UUIDMixin, TimestampMixin):
    """Individual condition within a condition group."""

    __tablename__ = "tool_chain_conditions"

    # Parent group
    group_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tool_chain_condition_groups.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Condition definition
    operator: Mapped[str] = mapped_column(String(20), nullable=False)
    field: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # Field path in result (e.g., "result.count", "result.data.status")
    value: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Value to compare against

    # Order within group
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    group: Mapped["ToolChainConditionGroup"] = relationship(
        "ToolChainConditionGroup", back_populates="conditions"
    )

    def __repr__(self) -> str:
        return f"<ToolChainCondition(group_id={self.group_id}, {self.field} {self.operator} {self.value})>"


class ToolChainAction(Base, UUIDMixin, TimestampMixin):
    """An action to execute in THEN or ELSE branch.

    Can be either a tool call or a message to display.
    """

    __tablename__ = "tool_chain_actions"

    # Parent step
    step_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tool_chain_steps.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Branch (then or else)
    branch: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # "then" or "else"

    # Action type
    action_type: Mapped[str] = mapped_column(
        String(20), default=ActionType.TOOL_CALL.value, nullable=False
    )

    # For TOOL_CALL action
    target_service: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    target_tool: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    argument_mappings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # For MESSAGE action - template with placeholders like {result.title}, {input.query}
    message_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Execution order and mode
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    execution_mode: Mapped[str] = mapped_column(
        String(20), default=ExecutionMode.SEQUENTIAL.value, nullable=False
    )

    # AI comment specific to this action
    ai_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Action status
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    step: Mapped["ToolChainStep"] = relationship("ToolChainStep", back_populates="then_actions",
                                                  foreign_keys=[step_id])

    def __repr__(self) -> str:
        if self.action_type == ActionType.MESSAGE.value:
            return f"<ToolChainAction(step_id={self.step_id}, branch={self.branch}, type=message)>"
        return f"<ToolChainAction(step_id={self.step_id}, branch={self.branch}, target={self.target_service}.{self.target_tool})>"
