"""MCP Request model for tracking AI interactions with homelab services."""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class McpRequestStatus(str, Enum):
    """Status of an MCP request."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class McpToolCategory(str, Enum):
    """Category of MCP tools."""

    MEDIA = "media"  # Plex, Tautulli
    MONITORING = "monitoring"  # Tautulli stats, metrics
    REQUESTS = "requests"  # Overseerr
    SUPPORT = "support"  # Zammad
    SYSTEM = "system"  # System monitoring, logs
    USERS = "users"  # User management


class McpRequest(Base, UUIDMixin, TimestampMixin):
    """Model for tracking MCP requests from AI to homelab services."""

    __tablename__ = "mcp_requests"

    # Request identification
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)

    # Tool information
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tool_category: Mapped[McpToolCategory] = mapped_column(String(20), default=McpToolCategory.SYSTEM, index=True)

    # Request details
    input_params: Mapped[dict] = mapped_column(JSON, default=dict)
    output_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Status tracking
    status: Mapped[McpRequestStatus] = mapped_column(String(20), default=McpRequestStatus.PENDING, index=True)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Service reference (which homelab service was called)
    service_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("service_configs.id", ondelete="SET NULL"), nullable=True
    )

    # User context (who triggered the request via AI)
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    user_query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # AI context
    ai_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ai_response_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Audit flags
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    is_mutation: Mapped[bool] = mapped_column(Boolean, default=False)  # True if request modifies data

    # Relationships
    service = relationship("ServiceConfig", foreign_keys=[service_id], lazy="selectin")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_mcp_requests_created_status", "created_at", "status"),
        Index("ix_mcp_requests_tool_status", "tool_name", "status"),
        Index("ix_mcp_requests_category_created", "tool_category", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<McpRequest(id={self.id}, "
            f"tool={self.tool_name}, "
            f"status={self.status}, "
            f"duration_ms={self.duration_ms})>"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "tool_name": self.tool_name,
            "tool_category": self.tool_category.value if hasattr(self.tool_category, "value") else self.tool_category,
            "input_params": self.input_params,
            "output_result": self.output_result,
            "status": self.status.value if hasattr(self.status, "value") else self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "service_id": self.service_id,
            "user_id": self.user_id,
            "user_query": self.user_query,
            "ai_model": self.ai_model,
            "is_sensitive": self.is_sensitive,
            "is_mutation": self.is_mutation,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def mark_started(self) -> None:
        """Mark request as started processing."""
        self.status = McpRequestStatus.PROCESSING
        self.started_at = datetime.utcnow()

    def mark_completed(self, result: dict) -> None:
        """Mark request as completed with result."""
        self.status = McpRequestStatus.COMPLETED
        self.output_result = result
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)

    def mark_failed(self, error_message: str, error_type: str = "Error") -> None:
        """Mark request as failed with error details."""
        self.status = McpRequestStatus.FAILED
        self.error_message = error_message
        self.error_type = error_type
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
