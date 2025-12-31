"""System metrics model."""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, MetricType, UUIDMixin


class SystemMetric(Base, UUIDMixin):
    """System metrics for monitoring and performance tracking."""

    __tablename__ = "system_metrics"

    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    metric_type: Mapped[MetricType] = mapped_column(String(50), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, default="localhost")
    component: Mapped[str] = mapped_column(String(100), nullable=True)
    labels: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<SystemMetric(id={self.id}, "
            f"metric_type={self.metric_type}, "
            f"metric_name={self.metric_name}, "
            f"value={self.value}, "
            f"timestamp={self.timestamp})>"
        )
