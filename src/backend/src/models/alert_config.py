"""Alert configuration model for monitoring and notifications."""

from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import DateTime, String, Text, JSON, Boolean, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column

from .base import (
    Base,
    UUIDMixin,
    TimestampMixin,
    AlertSeverity,
    MetricType,
    ThresholdOperator,
    DestinationType
)


class AlertConfiguration(Base, UUIDMixin, TimestampMixin):
    """Alert configuration for monitoring thresholds and notifications."""

    __tablename__ = "alert_configurations"

    # Basic info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Alert type and severity
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AlertSeverity.MEDIUM.value
    )

    metric_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=MetricType.CPU.value
    )

    # Threshold configuration
    threshold_operator: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=ThresholdOperator.GT.value
    )

    threshold_value: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    # Duration before triggering (in seconds)
    duration_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60
    )

    # Service-specific alert (optional)
    service_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True
    )

    service_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )

    # Notification settings
    notification_channels: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list
    )  # List of destination types: ["email", "webhook", "slack"]

    notification_config: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict
    )  # Channel-specific config (emails, webhook URLs, etc.)

    # Cooldown to prevent alert spam
    cooldown_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=15
    )

    # Alert state
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )

    trigger_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    is_firing: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    # Additional metadata
    tags: Mapped[Dict[str, str]] = mapped_column(
        JSON,
        nullable=False,
        default=dict
    )

    def __repr__(self) -> str:
        return f"<AlertConfiguration {self.id[:8]} {self.name} [{self.severity}]>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "severity": self.severity,
            "metric_type": self.metric_type,
            "threshold_operator": self.threshold_operator,
            "threshold_value": self.threshold_value,
            "duration_seconds": self.duration_seconds,
            "service_id": self.service_id,
            "service_type": self.service_type,
            "notification_channels": self.notification_channels,
            "notification_config": self.notification_config,
            "cooldown_minutes": self.cooldown_minutes,
            "last_triggered_at": self.last_triggered_at.isoformat() if self.last_triggered_at else None,
            "trigger_count": self.trigger_count,
            "is_firing": self.is_firing,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def check_threshold(self, current_value: float) -> bool:
        """Check if current value triggers the alert based on threshold."""
        op = self.threshold_operator
        threshold = self.threshold_value

        if op == ThresholdOperator.GT.value:
            return current_value > threshold
        elif op == ThresholdOperator.LT.value:
            return current_value < threshold
        elif op == ThresholdOperator.GTE.value:
            return current_value >= threshold
        elif op == ThresholdOperator.LTE.value:
            return current_value <= threshold
        elif op == ThresholdOperator.EQ.value:
            return current_value == threshold
        elif op == ThresholdOperator.NE.value:
            return current_value != threshold

        return False


class AlertHistory(Base, UUIDMixin, TimestampMixin):
    """History of triggered alerts."""

    __tablename__ = "alert_history"

    # Reference to alert configuration
    alert_config_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True
    )

    alert_name: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)

    # Trigger details
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )

    is_resolved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    # Values at time of trigger
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)

    # Context
    service_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Notification status
    notifications_sent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    notification_details: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict
    )

    def __repr__(self) -> str:
        status = "resolved" if self.is_resolved else "firing"
        return f"<AlertHistory {self.id[:8]} {self.alert_name} [{status}]>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "alert_config_id": self.alert_config_id,
            "alert_name": self.alert_name,
            "severity": self.severity,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "is_resolved": self.is_resolved,
            "metric_value": self.metric_value,
            "threshold_value": self.threshold_value,
            "service_id": self.service_id,
            "message": self.message,
            "notifications_sent": self.notifications_sent,
            "notification_details": self.notification_details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
