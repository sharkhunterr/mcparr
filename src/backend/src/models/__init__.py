"""Database models for MCParr AI Gateway."""

from .alert_config import AlertConfiguration, AlertHistory
from .base import AlertSeverity, Base, LogLevel, TimestampMixin, UUIDMixin
from .configuration import ConfigurationSetting
from .global_search import SEARCHABLE_SERVICES, GlobalSearchConfig
from .group import Group, GroupMembership, GroupToolPermission
from .log_entry import LogEntry
from .mcp_request import McpRequest, McpRequestStatus, McpToolCategory
from .service_config import ServiceConfig, ServiceHealthHistory, ServiceStatus, ServiceType
from .service_group import ServiceGroup, ServiceGroupMembership
from .system_metrics import SystemMetric
from .tool_chain import (
    ActionType,
    ConditionGroupOperator,
    ConditionOperator,
    ExecutionMode,
    StepPositionType,
    ToolChain,
    ToolChainAction,
    ToolChainCondition,
    ToolChainConditionGroup,
    ToolChainStep,
)
from .training_prompt import (
    PromptCategory,
    PromptDifficulty,
    PromptFormat,
    PromptSource,
    PromptTemplate,
    TrainingPrompt,
    session_prompt_association,
)
from .training_session import TrainingSession, TrainingStatus, TrainingType
from .training_worker import TrainingWorker, WorkerMetricsSnapshot, WorkerStatus
from .user_mapping import MappingStatus, UserMapping, UserRole, UserSync

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
    "ServiceGroup",
    "ServiceGroupMembership",
    "ToolChain",
    "ToolChainStep",
    "ToolChainConditionGroup",
    "ToolChainCondition",
    "ToolChainAction",
    "ConditionOperator",
    "ConditionGroupOperator",
    "ActionType",
    "ExecutionMode",
    "StepPositionType",
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
    "GlobalSearchConfig",
    "SEARCHABLE_SERVICES",
]
