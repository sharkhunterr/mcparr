"""Base models and enums for MCParr AI Gateway."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# Service Types
class ServiceType(str, Enum):
    """Supported homelab service types."""

    PLEX = "plex"
    TAUTULLI = "tautulli"
    OVERSEERR = "overseerr"
    ZAMMAD = "zammad"
    AUTHENTIK = "authentik"
    MONITORING = "monitoring"


# Status Types
class TestStatus(str, Enum):
    """Service connection test status."""

    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


class TrainingStatus(str, Enum):
    """Training session status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RequestStatus(str, Enum):
    """Request completion status."""

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


# User and Permission Types
class UserRole(str, Enum):
    """User role in the system."""

    ADMIN = "admin"
    USER = "user"


class LogLevel(str, Enum):
    """Log entry severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# MCP Types
class McpRequestType(str, Enum):
    """MCP request types."""

    TOOL_CALL = "tool_call"
    RESOURCE_REQUEST = "resource_request"
    PROMPT_REQUEST = "prompt_request"


# Training Types
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


# Monitoring Types
class MetricType(str, Enum):
    """System metric types."""

    # System metrics
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    DOCKER_CONTAINER = "docker_container"

    # Service metrics
    SERVICE_DOWN = "service_down"
    SERVICE_TEST_FAILED = "service_test_failed"
    SERVICE_LATENCY = "service_latency"

    # MCP metrics
    MCP_ERROR_RATE = "mcp_error_rate"
    MCP_REQUEST_VOLUME = "mcp_request_volume"
    MCP_DURATION = "mcp_duration"

    # User metrics
    USER_SYNC_FAILED = "user_sync_failed"
    USER_PERMISSION_DENIED = "user_permission_denied"

    # Training/Worker metrics
    WORKER_OFFLINE = "worker_offline"
    WORKER_GPU_USAGE = "worker_gpu_usage"
    TRAINING_FAILED = "training_failed"

    # Log-based metrics
    ERROR_RATE = "error_rate"
    LOG_VOLUME = "log_volume"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThresholdOperator(str, Enum):
    """Alert threshold operators."""

    GT = "gt"
    LT = "lt"
    EQ = "eq"
    NE = "ne"
    GTE = "gte"
    LTE = "lte"


class DestinationType(str, Enum):
    """Alert destination types."""

    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"


# Configuration Types
class ConfigCategory(str, Enum):
    """Configuration setting categories."""

    GENERAL = "general"
    SERVICES = "services"
    TRAINING = "training"
    MONITORING = "monitoring"
    SECURITY = "security"


class ValueType(str, Enum):
    """Configuration value types."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    ARRAY = "array"


# Base model mixins
class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class UUIDMixin:
    """Mixin for UUID primary key (as string for SQLite compatibility)."""

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()), nullable=False)


# Pydantic model helpers
def to_dict(obj: Any) -> Dict[str, Any]:
    """Convert SQLAlchemy model to dictionary."""
    if hasattr(obj, "__dict__"):
        result = {}
        for key, value in obj.__dict__.items():
            if not key.startswith("_"):
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, (UUID, str)) and key == "id":
                    result[key] = str(value)
                elif isinstance(value, Enum):
                    result[key] = value.value
                else:
                    result[key] = value
        return result
    return obj


def from_dict(cls: type, data: Dict[str, Any]) -> Any:
    """Create model instance from dictionary."""
    if hasattr(cls, "__annotations__"):
        filtered_data = {k: v for k, v in data.items() if k in cls.__annotations__}
        return cls(**filtered_data)
    return cls(**data)
