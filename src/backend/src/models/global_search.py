"""Global search configuration model for multi-service search."""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .service_config import ServiceConfig


# Map of service types that have search capability and their search tool name
SEARCHABLE_SERVICES = {
    "overseerr": {"tool": "overseerr_search_media"},
    "radarr": {"tool": "radarr_search_movie"},
    "sonarr": {"tool": "sonarr_search_series"},
    "plex": {"tool": "plex_search_media"},
    "jackett": {"tool": "jackett_search"},
    "prowlarr": {"tool": "prowlarr_search"},
    "komga": {"tool": "komga_search"},
    "audiobookshelf": {"tool": "audiobookshelf_search"},
    "wikijs": {"tool": "wikijs_search"},
    "zammad": {"tool": "zammad_search_tickets"},
    "romm": {"tool": "romm_search_roms"},
}


class GlobalSearchConfig(Base, UUIDMixin, TimestampMixin):
    """Configuration for global search per service."""

    __tablename__ = "global_search_configs"

    # Foreign key to service configuration
    service_config_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("service_configs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Enable/disable this service in global search
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Priority for display order (lower = higher priority)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationship to service config
    service_config: Mapped["ServiceConfig"] = relationship(
        "ServiceConfig",
        foreign_keys=[service_config_id],
    )

    def __repr__(self) -> str:
        return (
            f"<GlobalSearchConfig(id={self.id}, "
            f"service_config_id={self.service_config_id}, "
            f"enabled={self.enabled}, "
            f"priority={self.priority})>"
        )

    @classmethod
    def get_searchable_services(cls) -> dict:
        """Get the map of searchable services and their configuration."""
        return SEARCHABLE_SERVICES

    @classmethod
    def is_service_searchable(cls, service_type: str) -> bool:
        """Check if a service type has search capability."""
        return service_type.lower() in SEARCHABLE_SERVICES

    @classmethod
    def get_service_search_info(cls, service_type: str) -> Optional[dict]:
        """Get search info for a service type."""
        return SEARCHABLE_SERVICES.get(service_type.lower())
