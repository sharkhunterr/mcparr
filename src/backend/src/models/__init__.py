"""Database models for MCParr AI Gateway."""

from .base import Base, UUIDMixin, TimestampMixin, LogLevel, AlertSeverity
from .system_metrics import SystemMetric
from .configuration import ConfigurationSetting
from .service_config import ServiceConfig, ServiceType, ServiceStatus, ServiceHealthHistory
from .user_mapping import UserMapping, UserSync, UserRole, MappingStatus
from .log_entry import LogEntry
from .alert_config import AlertConfiguration, AlertHistory
from .mcp_request import McpRequest, McpRequestStatus, McpToolCategory
from .group import Group, GroupMembership, GroupToolPermission
from .training_session import TrainingSession, TrainingStatus, TrainingType
from .training_prompt import (
    TrainingPrompt,
    PromptTemplate,
    PromptCategory,
    PromptDifficulty,
    PromptSource,
    PromptFormat,
    session_prompt_association
)
from .training_worker import TrainingWorker, WorkerStatus, WorkerMetricsSnapshot

__all__ = [
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    "LogLevel",
    "AlertSeverity",
    "SystemMetric",
    "ConfigurationSetting",
    "ServiceConfig",
    "ServiceType",
    "ServiceStatus",
    "ServiceHealthHistory",
    "UserMapping",
    "UserSync",
    "UserRole",
    "MappingStatus",
    "LogEntry",
    "AlertConfiguration",
    "AlertHistory",
    "McpRequest",
    "McpRequestStatus",
    "McpToolCategory",
    "Group",
    "GroupMembership",
    "GroupToolPermission",
    "TrainingSession",
    "TrainingStatus",
    "TrainingType",
    "TrainingPrompt",
    "PromptTemplate",
    "PromptCategory",
    "PromptDifficulty",
    "PromptSource",
    "PromptFormat",
    "session_prompt_association",
    "TrainingWorker",
    "WorkerStatus",
    "WorkerMetricsSnapshot",
]