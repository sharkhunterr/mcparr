"""Training prompt models for Ollama model training."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .training_session import TrainingSession

# Association table for many-to-many relationship between sessions and prompts
session_prompt_association = Table(
    "session_prompt_association",
    Base.metadata,
    Column("session_id", String(36), ForeignKey("training_sessions.id", ondelete="CASCADE"), primary_key=True),
    Column("prompt_id", String(36), ForeignKey("training_prompts.id", ondelete="CASCADE"), primary_key=True),
    Column("added_at", DateTime, default=datetime.utcnow),
)


class PromptCategory(str, Enum):
    """Training prompt categories."""

    GENERAL = "general"
    MEDIA = "media"
    SUPPORT = "support"
    HOMELAB = "homelab"
    CUSTOM = "custom"


class PromptDifficulty(str, Enum):
    """Training prompt difficulty levels."""

    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class PromptSource(str, Enum):
    """Training prompt sources."""

    MANUAL = "manual"
    IMPORTED = "imported"
    GENERATED = "generated"
    SYSTEM = "system"


class PromptFormat(str, Enum):
    """Training data format."""

    CHAT = "chat"  # [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    INSTRUCTION = "instruction"  # {"instruction": "...", "input": "...", "output": "..."}
    COMPLETION = "completion"  # {"prompt": "...", "completion": "..."}
    QA = "qa"  # {"question": "...", "answer": "..."}


class TrainingPrompt(Base, UUIDMixin, TimestampMixin):
    """Training prompt/example for model fine-tuning."""

    __tablename__ = "training_prompts"

    # Basic information
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Categorization
    category: Mapped[PromptCategory] = mapped_column(
        String(50), default=PromptCategory.GENERAL, nullable=False, index=True
    )
    difficulty: Mapped[PromptDifficulty] = mapped_column(String(20), default=PromptDifficulty.BASIC, nullable=False)
    source: Mapped[PromptSource] = mapped_column(String(20), default=PromptSource.MANUAL, nullable=False)
    format: Mapped[PromptFormat] = mapped_column(String(20), default=PromptFormat.CHAT, nullable=False)

    # Content - The actual training data
    # For CHAT format: [{"role": "user/assistant/system", "content": "..."}]
    # For INSTRUCTION: {"instruction": "...", "input": "...", "output": "..."}
    # For COMPLETION: {"prompt": "...", "completion": "..."}
    content: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    # System prompt (optional, for chat format)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # User input/question
    user_input: Mapped[str] = mapped_column(Text, nullable=False)

    # Tool calling support - for prompts that involve function calling
    # tool_call contains the expected tool call: {"name": "tool_name", "arguments": {...}}
    tool_call: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # tool_response contains an example response from the tool (realistic mock data)
    tool_response: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Final assistant response (after processing tool results if applicable)
    assistant_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # DEPRECATED: Expected output/answer - replaced by assistant_response
    # Kept for backward compatibility
    expected_output: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Tags for filtering/grouping
    tags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    # Quality/validation
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    validated_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Usage tracking
    times_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Status
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # DEPRECATED: session_id kept for backward compatibility, use sessions relationship instead
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("training_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Many-to-many relationship with sessions (a prompt can be in multiple sessions)
    sessions: Mapped[List["TrainingSession"]] = relationship(
        "TrainingSession", secondary=session_prompt_association, back_populates="prompts"
    )

    # DEPRECATED: kept for backward compatibility
    session: Mapped[Optional["TrainingSession"]] = relationship(
        "TrainingSession", foreign_keys=[session_id], viewonly=True
    )

    def __repr__(self) -> str:
        return (
            f"<TrainingPrompt(id={self.id}, "
            f"name={self.name}, "
            f"category={self.category}, "
            f"format={self.format})>"
        )

    def to_training_format(self) -> Dict[str, Any]:
        """Convert prompt to training format based on format type.

        For tool calling prompts (when tool_call is set):
        - Generates a multi-turn conversation: user -> assistant (tool call) -> tool (response) -> assistant (final)

        For regular prompts:
        - Uses the standard format based on format type
        """
        import json as json_module

        # Get the final response (prefer assistant_response, fallback to expected_output)
        final_response = self.assistant_response or self.expected_output

        if self.format == PromptFormat.CHAT:
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            messages.append({"role": "user", "content": self.user_input})

            # If this is a tool calling prompt
            if self.tool_call and self.tool_response:
                # Assistant makes a tool call
                json_module.dumps(self.tool_call, ensure_ascii=False)
                tool_args_json = json_module.dumps(self.tool_call.get("arguments", {}), ensure_ascii=False)
                tool_name = self.tool_call.get("name", "")
                messages.append(
                    {"role": "assistant", "content": f'{{"name": "{tool_name}", "parameters": {tool_args_json}}}'}
                )
                # Tool returns response
                messages.append({"role": "tool", "content": json_module.dumps(self.tool_response, ensure_ascii=False)})
                # Assistant provides final response based on tool result
                messages.append({"role": "assistant", "content": final_response})
            else:
                # Regular prompt without tool calling
                messages.append({"role": "assistant", "content": final_response})

            return {"messages": messages}

        elif self.format == PromptFormat.INSTRUCTION:
            return {"instruction": self.user_input, "input": "", "output": final_response}

        elif self.format == PromptFormat.COMPLETION:
            return {"prompt": self.user_input, "completion": final_response}

        elif self.format == PromptFormat.QA:
            return {"question": self.user_input, "answer": final_response}

        return self.content

    @property
    def has_tool_calling(self) -> bool:
        """Check if this prompt uses tool calling."""
        return bool(self.tool_call and self.tool_response)

    def mark_used(self) -> None:
        """Mark this prompt as used in training."""
        self.times_used += 1
        self.last_used_at = datetime.utcnow()

    def validate(self, score: float = None, validated_by: str = None) -> None:
        """Mark prompt as validated."""
        self.is_validated = True
        self.validated_at = datetime.utcnow()
        if score is not None:
            self.validation_score = score
        if validated_by:
            self.validated_by = validated_by


class PromptTemplate(Base, UUIDMixin, TimestampMixin):
    """Reusable prompt templates for creating training prompts."""

    __tablename__ = "prompt_templates"

    # Basic information
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Template content
    system_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_template: Mapped[str] = mapped_column(Text, nullable=False)
    assistant_template: Mapped[str] = mapped_column(Text, nullable=False)

    # Template variables
    variables: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    # Categorization
    category: Mapped[PromptCategory] = mapped_column(String(50), default=PromptCategory.GENERAL, nullable=False)
    format: Mapped[PromptFormat] = mapped_column(String(20), default=PromptFormat.CHAT, nullable=False)

    # Status
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Usage tracking
    times_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<PromptTemplate(id={self.id}, name={self.name})>"

    def render(self, **kwargs) -> Dict[str, str]:
        """Render template with provided variables."""
        result = {
            "user_input": self.user_template.format(**kwargs),
            "expected_output": self.assistant_template.format(**kwargs),
        }
        if self.system_template:
            result["system_prompt"] = self.system_template.format(**kwargs)
        return result
