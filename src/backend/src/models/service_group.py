"""Service Group models for organizing services into logical groups."""

from typing import List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class ServiceGroup(Base, UUIDMixin, TimestampMixin):
    """Group for organizing services into logical categories.

    Service groups allow users to create custom groupings of services
    for use in Open WebUI auto-configuration and other features.
    Each group can generate its own OpenAPI endpoint with the combined
    tools from all member services.
    """

    __tablename__ = "service_groups"

    # Group identity
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Display settings
    color: Mapped[Optional[str]] = mapped_column(
        String(7), nullable=True, default="#6366f1"  # Hex color code #RRGGBB (Indigo default)
    )
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Icon name for frontend

    # Priority for display ordering (higher = shown first)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # System groups cannot be deleted (e.g., default groups)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Group status
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    memberships: Mapped[List["ServiceGroupMembership"]] = relationship(
        "ServiceGroupMembership", back_populates="group", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ServiceGroup(id={self.id}, name={self.name}, enabled={self.enabled})>"

    @property
    def member_count(self) -> int:
        """Get number of services in this group."""
        return len([m for m in self.memberships if m.enabled])

    @property
    def service_types(self) -> List[str]:
        """Get list of service types in this group."""
        return [m.service_type for m in self.memberships if m.enabled]


class ServiceGroupMembership(Base, UUIDMixin, TimestampMixin):
    """Association between service types and service groups.

    Note: We store service_type (e.g., 'plex', 'sonarr') rather than
    service_config_id because:
    1. A service type may not have a configured instance yet
    2. Users want to group by service type, not specific instances
    3. This allows the group to work even if a service is reconfigured
    """

    __tablename__ = "service_group_memberships"

    # Ensure unique service_type per group
    __table_args__ = (
        UniqueConstraint('group_id', 'service_type', name='uix_group_service'),
    )

    # Group reference
    group_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("service_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Service type (e.g., 'plex', 'sonarr', 'radarr')
    service_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Membership status
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    group: Mapped["ServiceGroup"] = relationship("ServiceGroup", back_populates="memberships")

    def __repr__(self) -> str:
        return f"<ServiceGroupMembership(group_id={self.group_id}, service_type={self.service_type})>"
