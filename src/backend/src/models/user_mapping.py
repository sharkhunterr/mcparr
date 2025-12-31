"""User mapping models for cross-service user management."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .service_config import ServiceConfig


class UserRole(str, Enum):
    """User roles across services."""

    ADMIN = "admin"
    USER = "user"
    MODERATOR = "moderator"
    VIEWER = "viewer"
    CUSTOM = "custom"


class MappingStatus(str, Enum):
    """User mapping status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    FAILED = "failed"
    SYNCING = "syncing"


class UserMapping(Base, UUIDMixin, TimestampMixin):
    """User mapping between homelab services and central user management."""

    __tablename__ = "user_mappings"

    # Central user identity
    central_user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    central_username: Mapped[str] = mapped_column(String(100), nullable=False)
    central_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Service-specific mapping
    service_config_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("service_configs.id"), nullable=False, index=True
    )
    service_user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    service_username: Mapped[str] = mapped_column(String(100), nullable=False)
    service_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Role and permissions
    role: Mapped[UserRole] = mapped_column(String(20), default=UserRole.USER, nullable=False)
    permissions: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Mapping status
    status: Mapped[MappingStatus] = mapped_column(String(20), default=MappingStatus.ACTIVE, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Synchronization tracking
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_sync_success: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    last_sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Service-specific metadata
    service_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Sync settings
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sync_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    service_config: Mapped["ServiceConfig"] = relationship("ServiceConfig", back_populates="user_mappings")
    sync_logs: Mapped[list["UserSync"]] = relationship(
        "UserSync", back_populates="user_mapping", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<UserMapping(id={self.id}, "
            f"central_user={self.central_username}, "
            f"service_user={self.service_username}, "
            f"service_config_id={self.service_config_id}, "
            f"status={self.status})>"
        )

    @property
    def is_active(self) -> bool:
        """Check if mapping is active and healthy."""
        return self.status == MappingStatus.ACTIVE and self.enabled and self.last_sync_success is not False

    def update_sync_result(self, success: bool, error: Optional[str] = None) -> None:
        """Update synchronization result."""
        self.last_sync_at = datetime.utcnow()
        self.last_sync_success = success
        self.last_sync_error = error
        self.sync_attempts += 1

        if success:
            if self.status == MappingStatus.PENDING:
                self.status = MappingStatus.ACTIVE
            elif self.status == MappingStatus.SYNCING:
                self.status = MappingStatus.ACTIVE
        else:
            self.status = MappingStatus.FAILED

    def needs_sync(self) -> bool:
        """Check if user mapping needs synchronization."""
        if not self.sync_enabled:
            return False

        if self.last_sync_at is None:
            return True

        # Check if sync frequency has elapsed (default 1 hour)
        sync_frequency = 3600  # 1 hour in seconds
        time_since_sync = (datetime.utcnow() - self.last_sync_at).total_seconds()
        return time_since_sync >= sync_frequency

    def get_service_permissions(self) -> Dict[str, Any]:
        """Get service-specific permissions."""
        base_permissions = {"read": True, "write": False, "admin": False}

        # Override with role-based permissions
        if self.role == UserRole.ADMIN:
            base_permissions.update({"read": True, "write": True, "admin": True})
        elif self.role == UserRole.MODERATOR:
            base_permissions.update({"read": True, "write": True, "admin": False})
        elif self.role == UserRole.USER:
            base_permissions.update({"read": True, "write": True, "admin": False})
        elif self.role == UserRole.VIEWER:
            base_permissions.update({"read": True, "write": False, "admin": False})

        # Merge with custom permissions
        base_permissions.update(self.permissions)
        return base_permissions

    def mark_sync_attempt(self, success: bool, error: Optional[str] = None) -> None:
        """Mark a sync attempt - alias for update_sync_result for API compatibility."""
        self.update_sync_result(success, error)


class UserSync(Base, UUIDMixin, TimestampMixin):
    """User synchronization log for audit and troubleshooting."""

    __tablename__ = "user_syncs"

    user_mapping_id: Mapped[str] = mapped_column(String(36), ForeignKey("user_mappings.id"), nullable=False, index=True)

    # Sync details
    sync_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "create", "update", "delete", "check"
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sync_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Changed data
    changes: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    user_mapping: Mapped["UserMapping"] = relationship("UserMapping", back_populates="sync_logs")

    def __repr__(self) -> str:
        return (
            f"<UserSync(id={self.id}, "
            f"user_mapping_id={self.user_mapping_id}, "
            f"sync_type={self.sync_type}, "
            f"success={self.success})>"
        )
