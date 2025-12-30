"""Training session models for Ollama model training."""

from datetime import datetime
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from enum import Enum

from sqlalchemy import String, Text, DateTime, Boolean, JSON, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from .training_prompt import TrainingPrompt


class TrainingStatus(str, Enum):
    """Training session status."""
    PENDING = "pending"
    PREPARING = "preparing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrainingType(str, Enum):
    """Type of training/fine-tuning."""
    FINE_TUNE = "fine_tune"
    LORA = "lora"
    QLORA = "qlora"
    PROMPT_TUNE = "prompt_tune"


class TrainingSession(Base, UUIDMixin, TimestampMixin):
    """Training session for Ollama model fine-tuning."""

    __tablename__ = "training_sessions"

    # Basic information
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Model configuration
    base_model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    output_model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    training_type: Mapped[TrainingType] = mapped_column(
        String(20),
        default=TrainingType.FINE_TUNE,
        nullable=False
    )
    training_backend: Mapped[str] = mapped_column(
        String(50),
        default="ollama_modelfile",
        nullable=False
    )

    # Status tracking
    status: Mapped[TrainingStatus] = mapped_column(
        String(20),
        default=TrainingStatus.PENDING,
        nullable=False,
        index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Progress metrics
    current_epoch: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    total_epochs: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )
    current_step: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    total_steps: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    progress_percent: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False
    )

    # Training metrics (updated in real-time)
    loss: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    learning_rate: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    metrics_history: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False
    )

    # Final session summary (populated on completion)
    session_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Final summary with step durations, final metrics, and overall assessment"
    )

    # Training logs (stored after training completes)
    training_logs: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Training logs captured from the worker"
    )

    # Hyperparameters
    hyperparameters: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False
    )

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    estimated_completion: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )

    # Resource usage
    gpu_memory_used: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    cpu_usage: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )

    # Data source
    dataset_size: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    dataset_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    # Ollama service reference
    ollama_service_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("service_configs.id", ondelete="SET NULL"),
        nullable=True
    )

    # Training worker reference
    worker_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("training_workers.id", ondelete="SET NULL"),
        nullable=True
    )

    # Many-to-many relationship with prompts (via association table)
    prompts: Mapped[List["TrainingPrompt"]] = relationship(
        "TrainingPrompt",
        secondary="session_prompt_association",
        back_populates="sessions"
    )

    def __repr__(self) -> str:
        return (
            f"<TrainingSession(id={self.id}, "
            f"name={self.name}, "
            f"base_model={self.base_model}, "
            f"status={self.status})>"
        )

    @property
    def duration_seconds(self) -> Optional[int]:
        """Get training duration in seconds."""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.utcnow()
        return int((end_time - self.started_at).total_seconds())

    @property
    def is_active(self) -> bool:
        """Check if training is currently active."""
        return self.status in [TrainingStatus.RUNNING, TrainingStatus.PREPARING]

    @property
    def is_completed(self) -> bool:
        """Check if training is finished (success or failure)."""
        return self.status in [
            TrainingStatus.COMPLETED,
            TrainingStatus.FAILED,
            TrainingStatus.CANCELLED
        ]

    def update_progress(
        self,
        current_step: int,
        total_steps: int,
        current_epoch: int = None,
        loss: float = None,
        learning_rate: float = None
    ) -> None:
        """Update training progress."""
        self.current_step = current_step
        self.total_steps = total_steps
        if current_epoch is not None:
            self.current_epoch = current_epoch
        if loss is not None:
            self.loss = loss
        if learning_rate is not None:
            self.learning_rate = learning_rate

        # Calculate progress percentage
        if total_steps > 0:
            self.progress_percent = (current_step / total_steps) * 100

        # Add to metrics history
        metric_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "step": current_step,
            "epoch": self.current_epoch,
            "loss": loss,
            "learning_rate": learning_rate
        }
        if self.metrics_history is None:
            self.metrics_history = []
        self.metrics_history.append(metric_entry)

    def start_training(self) -> None:
        """Mark training as started."""
        self.status = TrainingStatus.RUNNING
        self.started_at = datetime.utcnow()

    def complete_training(self, output_model: str = None) -> None:
        """Mark training as completed."""
        self.status = TrainingStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.progress_percent = 100.0
        if output_model:
            self.output_model = output_model

    def fail_training(self, error_message: str) -> None:
        """Mark training as failed."""
        self.status = TrainingStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message

    def cancel_training(self) -> None:
        """Mark training as cancelled."""
        self.status = TrainingStatus.CANCELLED
        self.completed_at = datetime.utcnow()

    def generate_summary(self) -> Dict[str, Any]:
        """Generate a comprehensive session summary."""
        summary = {
            "session_id": self.id,
            "name": self.name,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "base_model": self.base_model,
            "output_model": self.output_model,
            "training_backend": self.training_backend,

            # Timing
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "duration_formatted": self._format_duration(self.duration_seconds),

            # Progress
            "total_epochs": self.total_epochs,
            "total_steps": self.total_steps,
            "final_step": self.current_step,
            "progress_percent": self.progress_percent,
            "dataset_size": self.dataset_size,

            # Final metrics
            "final_loss": self.loss,
            "final_learning_rate": self.learning_rate,

            # Metrics analysis
            "metrics_analysis": self._analyze_metrics(),

            # Error info
            "error_message": self.error_message,

            # Assessment
            "assessment": self._assess_training(),
        }

        return summary

    def _format_duration(self, seconds: Optional[int]) -> str:
        """Format duration in human-readable format."""
        if seconds is None:
            return "-"
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins}m {secs}s"
        else:
            hours = seconds // 3600
            mins = (seconds % 3600) // 60
            return f"{hours}h {mins}m"

    def _analyze_metrics(self) -> Dict[str, Any]:
        """Analyze metrics history to extract insights."""
        if not self.metrics_history:
            return {}

        losses = [m.get("loss") for m in self.metrics_history if m.get("loss") is not None]

        if not losses:
            return {}

        analysis = {
            "total_metrics_points": len(self.metrics_history),
            "initial_loss": losses[0] if losses else None,
            "final_loss": losses[-1] if losses else None,
            "min_loss": min(losses) if losses else None,
            "max_loss": max(losses) if losses else None,
            "avg_loss": sum(losses) / len(losses) if losses else None,
        }

        # Calculate loss improvement
        if analysis["initial_loss"] and analysis["final_loss"]:
            improvement = analysis["initial_loss"] - analysis["final_loss"]
            improvement_pct = (improvement / analysis["initial_loss"]) * 100 if analysis["initial_loss"] > 0 else 0
            analysis["loss_improvement"] = improvement
            analysis["loss_improvement_percent"] = round(improvement_pct, 2)

        # Determine trend
        if len(losses) >= 3:
            first_third = losses[:len(losses)//3]
            last_third = losses[-len(losses)//3:]
            avg_first = sum(first_third) / len(first_third) if first_third else 0
            avg_last = sum(last_third) / len(last_third) if last_third else 0

            if avg_last < avg_first * 0.95:
                analysis["trend"] = "decreasing"
            elif avg_last > avg_first * 1.05:
                analysis["trend"] = "increasing"
            else:
                analysis["trend"] = "stable"

        return analysis

    def _assess_training(self) -> Dict[str, Any]:
        """Generate an overall assessment of the training."""
        status_value = self.status.value if isinstance(self.status, Enum) else self.status

        assessment = {
            "health": "unknown",
            "message": "",
            "icon": "❓",
        }

        if status_value == "completed":
            metrics = self._analyze_metrics()
            loss_improvement_pct = metrics.get("loss_improvement_percent", 0)

            if loss_improvement_pct >= 20:
                assessment = {
                    "health": "excellent",
                    "message": f"Training réussi avec une amélioration significative du loss ({loss_improvement_pct:.1f}%)",
                    "icon": "✅",
                }
            elif loss_improvement_pct >= 5:
                assessment = {
                    "health": "good",
                    "message": f"Training terminé avec une amélioration modérée ({loss_improvement_pct:.1f}%)",
                    "icon": "👍",
                }
            elif loss_improvement_pct >= 0:
                assessment = {
                    "health": "warning",
                    "message": f"Training terminé mais amélioration limitée ({loss_improvement_pct:.1f}%)",
                    "icon": "⚠️",
                }
            else:
                assessment = {
                    "health": "warning",
                    "message": f"Training terminé mais le loss a augmenté ({loss_improvement_pct:.1f}%)",
                    "icon": "⚠️",
                }

        elif status_value == "failed":
            assessment = {
                "health": "critical",
                "message": self.error_message or "Le training a échoué",
                "icon": "❌",
            }

        elif status_value == "cancelled":
            assessment = {
                "health": "warning",
                "message": "Training annulé par l'utilisateur",
                "icon": "🚫",
            }

        elif status_value in ("running", "preparing"):
            assessment = {
                "health": "info",
                "message": "Training en cours...",
                "icon": "🔄",
            }

        elif status_value == "pending":
            assessment = {
                "health": "info",
                "message": "En attente de démarrage",
                "icon": "⏳",
            }

        return assessment
