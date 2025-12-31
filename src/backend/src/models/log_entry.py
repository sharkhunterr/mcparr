"""Log entry model for observability and real-time log streaming."""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, LogLevel, TimestampMixin, UUIDMixin


class LogEntry(Base, UUIDMixin, TimestampMixin):
    """Log entry model for storing and querying system logs."""

    __tablename__ = "log_entries"

    # Log content
    level: Mapped[str] = mapped_column(String(20), nullable=False, default=LogLevel.INFO.value, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Source identification
    source: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # e.g., "backend", "frontend", "plex", "tautulli"

    component: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # e.g., "api", "websocket", "adapter", "service"

    # Request tracing
    correlation_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )  # UUID for tracing requests across services

    request_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # Unique request identifier

    # User context
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Service context
    service_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )  # Related service config ID

    service_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Additional data
    extra_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    # Exception info
    exception_type: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    exception_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Performance data
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamp for when the log event occurred (may differ from created_at)
    logged_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Indexes for common queries
    __table_args__ = (
        Index("ix_log_entries_level_logged_at", "level", "logged_at"),
        Index("ix_log_entries_source_logged_at", "source", "logged_at"),
        Index("ix_log_entries_service_logged_at", "service_id", "logged_at"),
    )

    def __repr__(self) -> str:
        return f"<LogEntry {self.id[:8]} [{self.level}] {self.source}: {self.message[:50]}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "level": self.level,
            "message": self.message,
            "source": self.source,
            "component": self.component,
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "service_id": self.service_id,
            "service_type": self.service_type,
            "extra_data": self.extra_data,
            "exception_type": self.exception_type,
            "exception_message": self.exception_message,
            "stack_trace": self.stack_trace,
            "duration_ms": self.duration_ms,
            "logged_at": self.logged_at.isoformat() if self.logged_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
