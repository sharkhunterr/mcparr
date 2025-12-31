"""Group models for access control and permissions."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class Group(Base, UUIDMixin, TimestampMixin):
    """Group for organizing users and managing tool access permissions."""

    __tablename__ = "groups"

    # Group identity
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Display settings
    color: Mapped[Optional[str]] = mapped_column(
        String(7), nullable=True, default="#6366f1"  # Hex color code #RRGGBB  # Indigo default
    )
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Icon name for frontend

    # Priority for permission resolution (higher = more priority)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # System groups cannot be deleted
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Group status
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    memberships: Mapped[List["GroupMembership"]] = relationship(
        "GroupMembership", back_populates="group", cascade="all, delete-orphan"
    )
    tool_permissions: Mapped[List["GroupToolPermission"]] = relationship(
        "GroupToolPermission", back_populates="group", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Group(id={self.id}, name={self.name}, enabled={self.enabled})>"

    @property
    def member_count(self) -> int:
        """Get number of members in this group."""
        return len([m for m in self.memberships if m.enabled])

    @property
    def tool_count(self) -> int:
        """Get number of tools accessible by this group."""
        return len([p for p in self.tool_permissions if p.enabled])


class GroupMembership(Base, UUIDMixin, TimestampMixin):
    """Association between users and groups."""

    __tablename__ = "group_memberships"

    # Group reference
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("groups.id"), nullable=False, index=True)

    # User reference (central_user_id from UserMapping)
    central_user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Membership status
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # When membership was granted
    granted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Who granted the membership (optional)
    granted_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="memberships")

    def __repr__(self) -> str:
        return f"<GroupMembership(group_id={self.group_id}, central_user_id={self.central_user_id})>"


class GroupToolPermission(Base, UUIDMixin, TimestampMixin):
    """Permission linking groups to specific tools they can access."""

    __tablename__ = "group_tool_permissions"

    # Group reference
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("groups.id"), nullable=False, index=True)

    # Tool identification
    # Can be specific tool name or "*" for all tools of a service
    tool_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    # Optional service filter (if set, permission only applies to this service)
    # If None and tool_name is "*", means ALL tools from ALL services
    service_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    # Permission status
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Optional description for this permission
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="tool_permissions")

    def __repr__(self) -> str:
        return f"<GroupToolPermission(group_id={self.group_id}, tool={self.tool_name}, service={self.service_type})>"

    def matches_tool(self, tool_name: str, service_type: Optional[str] = None) -> bool:
        """Check if this permission matches the given tool."""
        if not self.enabled:
            return False

        # Check service type if specified
        if self.service_type and service_type and self.service_type != service_type:
            return False

        # Wildcard match for all tools
        if self.tool_name == "*":
            return True

        # Exact tool name match
        return self.tool_name == tool_name
