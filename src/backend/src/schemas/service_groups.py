"""Service Group schemas for API validation and serialization."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# --- Service Group Membership Schemas ---


class ServiceGroupMembershipCreate(BaseModel):
    """Schema for adding a service to a group."""

    service_type: str = Field(..., description="Service type to add (e.g., 'plex', 'sonarr')")
    enabled: bool = Field(True, description="Whether membership is active")


class ServiceGroupMembershipResponse(BaseModel):
    """Schema for membership API responses."""

    id: str
    group_id: str
    service_type: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
    # Additional info about the service (if configured)
    service_name: Optional[str] = None
    service_configured: bool = False

    @classmethod
    def model_validate(cls, obj, service_info: Optional[dict] = None):
        """Create response from database object."""
        service_info = service_info or {}
        return cls(
            id=str(obj.id),
            group_id=str(obj.group_id),
            service_type=obj.service_type,
            enabled=obj.enabled,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            service_name=service_info.get("name"),
            service_configured=service_info.get("configured", False),
        )


# --- Service Group Schemas ---


class ServiceGroupCreate(BaseModel):
    """Schema for creating a new service group."""

    name: str = Field(..., description="Group name (unique)")
    description: Optional[str] = Field(None, description="Group description")
    color: Optional[str] = Field("#6366f1", description="Display color (hex)")
    icon: Optional[str] = Field(None, description="Icon name")
    priority: int = Field(0, description="Priority for display ordering")
    enabled: bool = Field(True, description="Whether group is active")
    # Optional: add services on creation
    service_types: Optional[List[str]] = Field(None, description="Service types to add initially")


class ServiceGroupUpdate(BaseModel):
    """Schema for updating an existing service group."""

    name: Optional[str] = Field(None, description="Group name")
    description: Optional[str] = Field(None, description="Group description")
    color: Optional[str] = Field(None, description="Display color (hex)")
    icon: Optional[str] = Field(None, description="Icon name")
    priority: Optional[int] = Field(None, description="Priority for display ordering")
    enabled: Optional[bool] = Field(None, description="Whether group is active")


class ServiceGroupResponse(BaseModel):
    """Schema for service group API responses."""

    id: str
    name: str
    description: Optional[str]
    color: Optional[str]
    icon: Optional[str]
    priority: int
    is_system: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime
    # Computed fields
    member_count: int = 0
    service_types: List[str] = []

    @classmethod
    def model_validate(cls, obj):
        """Create response from database object."""
        return cls(
            id=str(obj.id),
            name=obj.name,
            description=obj.description,
            color=obj.color,
            icon=obj.icon,
            priority=obj.priority,
            is_system=obj.is_system,
            enabled=obj.enabled,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            member_count=len([m for m in obj.memberships if m.enabled]) if obj.memberships else 0,
            service_types=[m.service_type for m in obj.memberships if m.enabled] if obj.memberships else [],
        )


class ServiceGroupDetailResponse(ServiceGroupResponse):
    """Detailed service group response with members."""

    memberships: List[ServiceGroupMembershipResponse] = []

    @classmethod
    def model_validate(cls, obj, service_infos: Optional[dict] = None):
        """Create detailed response from database object."""
        service_infos = service_infos or {}
        return cls(
            id=str(obj.id),
            name=obj.name,
            description=obj.description,
            color=obj.color,
            icon=obj.icon,
            priority=obj.priority,
            is_system=obj.is_system,
            enabled=obj.enabled,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            member_count=len([m for m in obj.memberships if m.enabled]) if obj.memberships else 0,
            service_types=[m.service_type for m in obj.memberships if m.enabled] if obj.memberships else [],
            memberships=[
                ServiceGroupMembershipResponse.model_validate(m, service_infos.get(m.service_type))
                for m in obj.memberships
            ]
            if obj.memberships
            else [],
        )


class ServiceGroupListResponse(BaseModel):
    """Schema for paginated service group list responses."""

    groups: List[ServiceGroupResponse]
    total: int
    skip: int
    limit: int


# --- Bulk Operations ---


class BulkServiceUpdate(BaseModel):
    """Schema for bulk updating service memberships."""

    service_types: List[str] = Field(..., description="List of service types to add/remove")
    action: str = Field(..., description="Action: 'add' or 'remove'")


# --- Available Services ---


class AvailableService(BaseModel):
    """Schema for available service info."""

    service_type: str
    display_name: str
    configured: bool
    tool_count: int = 0


class AvailableServicesResponse(BaseModel):
    """Schema for listing available services."""

    services: List[AvailableService]
    total: int
