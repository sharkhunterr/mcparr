"""Service configuration models for homelab services management."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .user_mapping import UserMapping


class ServiceType(str, Enum):
    """Supported service types."""

    PLEX = "plex"
    OVERSEERR = "overseerr"
    ZAMMAD = "zammad"
    TAUTULLI = "tautulli"
    AUTHENTIK = "authentik"
    OPENWEBUI = "openwebui"
    OLLAMA = "ollama"
    RADARR = "radarr"
    SONARR = "sonarr"
    PROWLARR = "prowlarr"
    JACKETT = "jackett"
    DELUGE = "deluge"
    KOMGA = "komga"
    ROMM = "romm"
    AUDIOBOOKSHELF = "audiobookshelf"
    WIKIJS = "wikijs"
    MONITORING = "monitoring"
    CUSTOM = "custom"


class ServiceStatus(str, Enum):
    """Service connection status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    TESTING = "testing"
    UNKNOWN = "unknown"


class ServiceConfig(Base, UUIDMixin, TimestampMixin):
    """Configuration for homelab services."""

    __tablename__ = "service_configs"

    # Basic service information
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    service_type: Mapped[ServiceType] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Connection details
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Authentication
    api_key: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)  # JWT tokens can be long
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Service-specific configuration
    config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Status and monitoring
    status: Mapped[ServiceStatus] = mapped_column(String(20), default=ServiceStatus.UNKNOWN, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Connection testing
    last_test_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_test_success: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Health monitoring
    health_check_interval: Mapped[int] = mapped_column(Integer, default=300, nullable=False)  # 5 minutes
    health_check_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Metadata
    version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tags: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    user_mappings: Mapped[list["UserMapping"]] = relationship(
        "UserMapping", back_populates="service_config", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<ServiceConfig(id={self.id}, "
            f"name={self.name}, "
            f"service_type={self.service_type}, "
            f"status={self.status}, "
            f"enabled={self.enabled})>"
        )

    @property
    def full_url(self) -> str:
        """Get the full URL for the service."""
        if self.port:
            return f"{self.base_url}:{self.port}"
        return self.base_url

    @property
    def is_healthy(self) -> bool:
        """Check if service is healthy based on last test."""
        return self.status == ServiceStatus.ACTIVE and self.last_test_success is True and self.enabled

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API calls."""
        headers = {}

        if self.api_key:
            # Common API key patterns
            if self.service_type == ServiceType.PLEX:
                headers["X-Plex-Token"] = self.api_key
            elif self.service_type in [ServiceType.OVERSEERR, ServiceType.TAUTULLI]:
                headers["X-API-Key"] = self.api_key
            elif self.service_type == ServiceType.AUTHENTIK:
                headers["Authorization"] = f"Bearer {self.api_key}"
            else:
                headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    def update_test_result(self, success: bool, error: Optional[str] = None) -> None:
        """Update the last test result."""
        self.last_test_at = datetime.utcnow()
        self.last_test_success = success
        self.last_error = error

        if success:
            self.status = ServiceStatus.ACTIVE
        else:
            self.status = ServiceStatus.ERROR

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a value from the service configuration."""
        return self.config.get(key, default)


class ServiceHealthHistory(Base, UUIDMixin):
    """History of service health check results for uptime tracking."""

    __tablename__ = "service_health_history"

    # Foreign key to service
    service_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Test timestamp
    tested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Test result
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Response time in milliseconds
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Error message if failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<ServiceHealthHistory(id={self.id}, "
            f"service_id={self.service_id}, "
            f"tested_at={self.tested_at}, "
            f"success={self.success})>"
        )
