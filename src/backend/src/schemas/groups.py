"""Group schemas for API validation and serialization."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# --- Tool Permission Schemas ---


class GroupToolPermissionCreate(BaseModel):
    """Schema for creating a tool permission."""

    tool_name: str = Field(..., description="Tool name or '*' for all tools")
    service_type: Optional[str] = Field(None, description="Service type filter (optional)")
    enabled: bool = Field(True, description="Whether permission is enabled")
    description: Optional[str] = Field(None, description="Permission description")


class GroupToolPermissionUpdate(BaseModel):
    """Schema for updating a tool permission."""

    tool_name: Optional[str] = Field(None, description="Tool name or '*' for all tools")
    service_type: Optional[str] = Field(None, description="Service type filter")
    enabled: Optional[bool] = Field(None, description="Whether permission is enabled")
    description: Optional[str] = Field(None, description="Permission description")


class GroupToolPermissionResponse(BaseModel):
    """Schema for tool permission API responses."""

    id: str
    group_id: str
    tool_name: str
    service_type: Optional[str]
    enabled: bool
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def model_validate(cls, obj):
        """Create response from database object."""
        return cls(
            id=str(obj.id),
            group_id=str(obj.group_id),
            tool_name=obj.tool_name,
            service_type=obj.service_type,
            enabled=obj.enabled,
            description=obj.description,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )


# --- Group Membership Schemas ---


class GroupMembershipCreate(BaseModel):
    """Schema for adding a user to a group."""

    central_user_id: str = Field(..., description="Central user ID to add")
    enabled: bool = Field(True, description="Whether membership is active")
    granted_by: Optional[str] = Field(None, description="Who granted this membership")


class GroupMembershipUpdate(BaseModel):
    """Schema for updating a membership."""

    enabled: Optional[bool] = Field(None, description="Whether membership is active")


class GroupMembershipResponse(BaseModel):
    """Schema for membership API responses."""

    id: str
    group_id: str
    central_user_id: str
    enabled: bool
    granted_at: datetime
    granted_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    # Include user display name if available
    central_username: Optional[str] = None

    @classmethod
    def model_validate(cls, obj, username: Optional[str] = None):
        """Create response from database object."""
        return cls(
            id=str(obj.id),
            group_id=str(obj.group_id),
            central_user_id=obj.central_user_id,
            enabled=obj.enabled,
            granted_at=obj.granted_at,
            granted_by=obj.granted_by,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            central_username=username,
        )


# --- Group Schemas ---


class GroupCreate(BaseModel):
    """Schema for creating a new group."""

    name: str = Field(..., description="Group name (unique)")
    description: Optional[str] = Field(None, description="Group description")
    color: Optional[str] = Field("#6366f1", description="Display color (hex)")
    icon: Optional[str] = Field(None, description="Icon name")
    priority: int = Field(0, description="Priority for permission resolution")
    enabled: bool = Field(True, description="Whether group is active")


class GroupUpdate(BaseModel):
    """Schema for updating an existing group."""

    name: Optional[str] = Field(None, description="Group name")
    description: Optional[str] = Field(None, description="Group description")
    color: Optional[str] = Field(None, description="Display color (hex)")
    icon: Optional[str] = Field(None, description="Icon name")
    priority: Optional[int] = Field(None, description="Priority for permission resolution")
    enabled: Optional[bool] = Field(None, description="Whether group is active")


class GroupResponse(BaseModel):
    """Schema for group API responses."""

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
    tool_count: int = 0

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
            tool_count=len([p for p in obj.tool_permissions if p.enabled]) if obj.tool_permissions else 0,
        )


class GroupDetailResponse(GroupResponse):
    """Detailed group response with members and permissions."""

    memberships: List[GroupMembershipResponse] = []
    tool_permissions: List[GroupToolPermissionResponse] = []

    @classmethod
    def model_validate(cls, obj, usernames: Optional[dict] = None):
        """Create detailed response from database object."""
        usernames = usernames or {}
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
            tool_count=len([p for p in obj.tool_permissions if p.enabled]) if obj.tool_permissions else 0,
            memberships=[
                GroupMembershipResponse.model_validate(m, usernames.get(m.central_user_id)) for m in obj.memberships
            ]
            if obj.memberships
            else [],
            tool_permissions=[GroupToolPermissionResponse.model_validate(p) for p in obj.tool_permissions]
            if obj.tool_permissions
            else [],
        )


class GroupListResponse(BaseModel):
    """Schema for paginated group list responses."""

    groups: List[GroupResponse]
    total: int
    skip: int
    limit: int


# --- Bulk Operations ---


class BulkPermissionUpdate(BaseModel):
    """Schema for bulk updating tool permissions."""

    service_type: Optional[str] = Field(None, description="Service type to update")
    tool_names: List[str] = Field(..., description="List of tool names to add/enable")
    enabled: bool = Field(True, description="Enable or disable these permissions")


class BulkMembershipUpdate(BaseModel):
    """Schema for bulk updating group memberships."""

    central_user_ids: List[str] = Field(..., description="List of user IDs to add/remove")
    action: str = Field(..., description="Action: 'add' or 'remove'")


# --- Permission Check ---


class PermissionCheckRequest(BaseModel):
    """Schema for checking if a user has access to a tool."""

    central_user_id: str = Field(..., description="User to check")
    tool_name: str = Field(..., description="Tool to check access for")
    service_type: Optional[str] = Field(None, description="Service type context")


class PermissionCheckResponse(BaseModel):
    """Schema for permission check results."""

    has_access: bool
    central_user_id: str
    tool_name: str
    service_type: Optional[str]
    granted_by_group: Optional[str] = None
    granted_by_group_id: Optional[str] = None


# --- User Groups ---


class UserGroupsResponse(BaseModel):
    """Schema for listing groups a user belongs to."""

    central_user_id: str
    groups: List[GroupResponse]
    total_groups: int
