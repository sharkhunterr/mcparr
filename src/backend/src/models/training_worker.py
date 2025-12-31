"""Training Worker model for GPU training workers."""

import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, Float, Integer, String, Text

from .base import Base, TimestampMixin, UUIDMixin


class WorkerStatus(str, enum.Enum):
    """Worker status."""

    ONLINE = "online"
    OFFLINE = "offline"
    TRAINING = "training"
    ERROR = "error"
    UNKNOWN = "unknown"


class TrainingWorker(Base, UUIDMixin, TimestampMixin):
    """A training worker configuration."""

    __tablename__ = "training_workers"

    # Basic info
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Connection
    url = Column(String(500), nullable=False)  # e.g., http://192.168.1.100:8080
    api_key = Column(String(200), nullable=True)  # Optional API key for auth

    # Status
    status = Column(Enum(WorkerStatus), default=WorkerStatus.UNKNOWN, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    last_seen_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    # GPU info (cached from worker)
    gpu_available = Column(Boolean, default=False, nullable=False)
    gpu_count = Column(Integer, default=0, nullable=False)
    gpu_names = Column(JSON, default=list, nullable=False)  # List of GPU names
    gpu_memory_total_mb = Column(Float, default=0, nullable=False)

    # Worker info (cached from worker)
    worker_version = Column(String(50), nullable=True)
    platform = Column(String(100), nullable=True)

    # Ollama service to use for model import
    ollama_service_id = Column(String(36), nullable=True)

    # Current job (if training)
    current_job_id = Column(String(36), nullable=True)
    current_session_id = Column(String(36), nullable=True)

    # Statistics
    total_jobs_completed = Column(Integer, default=0, nullable=False)
    total_training_time_seconds = Column(Float, default=0, nullable=False)

    def __repr__(self):
        return f"<TrainingWorker {self.name} ({self.status.value})>"


class WorkerMetricsSnapshot(Base, UUIDMixin):
    """Snapshot of worker metrics."""

    __tablename__ = "worker_metrics_snapshots"

    # Worker reference
    worker_id = Column(String(36), nullable=False, index=True)

    # Timestamp
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # CPU metrics
    cpu_percent = Column(Float, nullable=True)
    cpu_temperature_c = Column(Float, nullable=True)

    # Memory metrics
    memory_used_mb = Column(Float, nullable=True)
    memory_total_mb = Column(Float, nullable=True)
    memory_percent = Column(Float, nullable=True)

    # GPU metrics (aggregated for first GPU or average)
    gpu_utilization_percent = Column(Float, nullable=True)
    gpu_memory_used_mb = Column(Float, nullable=True)
    gpu_memory_total_mb = Column(Float, nullable=True)
    gpu_memory_percent = Column(Float, nullable=True)
    gpu_temperature_c = Column(Float, nullable=True)
    gpu_power_draw_w = Column(Float, nullable=True)

    # Training metrics (if training)
    training_job_id = Column(String(36), nullable=True)
    training_progress_percent = Column(Float, nullable=True)
    training_loss = Column(Float, nullable=True)
    training_epoch = Column(Integer, nullable=True)
    training_step = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<WorkerMetricsSnapshot {self.worker_id} @ {self.recorded_at}>"
