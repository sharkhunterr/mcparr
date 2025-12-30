"""User mapping schemas for API validation and serialization."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from ..models.user_mapping import UserRole, MappingStatus


class UserMappingCreate(BaseModel):
    """Schema for creating a new user mapping."""
    central_user_id: str = Field(..., description="Central user identifier")
    central_username: str = Field(..., description="Central username")
    central_email: Optional[str] = Field(None, description="Central user email")
    service_config_id: str = Field(..., description="Service configuration ID")
    service_user_id: str = Field(..., description="User ID in the service")
    service_username: str = Field(..., description="Username in the service")
    service_email: Optional[str] = Field(None, description="Email in the service")
    role: UserRole = Field(UserRole.USER, description="User role in the service")
    status: MappingStatus = Field(MappingStatus.ACTIVE, description="Mapping status")
    sync_enabled: bool = Field(True, description="Whether sync is enabled for this mapping")
    service_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class UserMappingUpdate(BaseModel):
    """Schema for updating an existing user mapping."""
    service_user_id: Optional[str] = Field(None, description="User ID in the service")
    service_username: Optional[str] = Field(None, description="Username in the service")
    service_email: Optional[str] = Field(None, description="Email in the service")
    role: Optional[UserRole] = Field(None, description="User role in the service")
    status: Optional[MappingStatus] = Field(None, description="Mapping status")
    sync_enabled: Optional[bool] = Field(None, description="Whether sync is enabled for this mapping")
    service_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ServiceConfigInfo(BaseModel):
    """Basic service configuration info for user mapping responses."""
    id: str
    name: str
    service_type: str
    base_url: str


class UserMappingResponse(BaseModel):
    """Schema for user mapping API responses."""
    id: str
    central_user_id: str
    central_username: str
    central_email: Optional[str]
    service_config_id: str
    service_user_id: Optional[str]
    service_username: Optional[str]
    service_email: Optional[str]
    role: UserRole
    status: MappingStatus
    sync_enabled: bool
    last_sync_at: Optional[datetime]
    last_sync_success: Optional[bool]
    last_sync_error: Optional[str]
    sync_attempts: int
    service_metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    service_config: Optional[ServiceConfigInfo] = None

    @classmethod
    def model_validate(cls, obj):
        """Create response from database object."""
        data = {
            "id": str(obj.id),
            "central_user_id": obj.central_user_id,
            "central_username": obj.central_username,
            "central_email": obj.central_email,
            "service_config_id": str(obj.service_config_id),
            "service_user_id": obj.service_user_id,
            "service_username": obj.service_username,
            "service_email": obj.service_email,
            "role": obj.role,
            "status": obj.status,
            "sync_enabled": obj.sync_enabled,
            "last_sync_at": obj.last_sync_at,
            "last_sync_success": obj.last_sync_success,
            "last_sync_error": obj.last_sync_error,
            "sync_attempts": obj.sync_attempts,
            "service_metadata": obj.service_metadata,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at
        }

        # Add service config info if available
        if hasattr(obj, 'service_config') and obj.service_config:
            data["service_config"] = ServiceConfigInfo(
                id=str(obj.service_config.id),
                name=obj.service_config.name,
                service_type=obj.service_config.service_type,
                base_url=obj.service_config.base_url
            )

        return cls(**data)


class UserMappingListResponse(BaseModel):
    """Schema for paginated user mapping list responses."""
    mappings: List[UserMappingResponse]
    total: int
    skip: int
    limit: int


class UserSyncRequest(BaseModel):
    """Schema for user synchronization requests."""
    central_user_id: str = Field(..., description="Central user identifier to sync")
    force_sync: bool = Field(False, description="Force sync even if recently synced")
    sync_services: Optional[List[str]] = Field(None, description="Specific service IDs to sync (all if None)")


class UserSyncServiceResult(BaseModel):
    """Result for a single service sync operation."""
    service_id: str
    service_name: str
    success: bool
    error: Optional[str] = None
    sync_time: Optional[datetime] = None


class UserSyncResult(BaseModel):
    """Schema for user synchronization results."""
    central_user_id: str
    total_services: int
    successful_syncs: int
    failed_syncs: int
    sync_results: List[Dict[str, Any]]
    sync_started_at: datetime = Field(default_factory=datetime.utcnow)
    sync_completed_at: Optional[datetime] = None
    error: Optional[str] = None


class UserMappingStats(BaseModel):
    """User mapping statistics schema."""
    total_mappings: int
    unique_users: int
    status_breakdown: Dict[str, int]
    service_breakdown: Dict[str, int]
    average_mappings_per_user: float


class BulkUserMappingCreate(BaseModel):
    """Schema for creating multiple user mappings at once."""
    mappings: List[UserMappingCreate] = Field(..., description="List of user mappings to create")
    skip_existing: bool = Field(True, description="Skip mappings that already exist")
    validate_services: bool = Field(True, description="Validate that all services exist")


class BulkUserMappingResult(BaseModel):
    """Result of bulk user mapping creation."""
    total_requested: int
    created: int
    skipped: int
    failed: int
    errors: List[Dict[str, str]] = Field(default_factory=list)
    created_mappings: List[UserMappingResponse] = Field(default_factory=list)


class UserServiceInfo(BaseModel):
    """Information about a user in a specific service."""
    service_id: str
    service_name: str
    service_type: str
    user_id: Optional[str]
    username: Optional[str]
    email: Optional[str]
    role: UserRole
    status: MappingStatus
    last_sync: Optional[datetime]
    sync_status: Optional[str]


class CentralUserProfile(BaseModel):
    """Complete profile of a central user across all services."""
    central_user_id: str
    display_name: Optional[str]
    email: Optional[str]
    total_services: int
    active_services: int
    service_mappings: List[UserServiceInfo]
    last_activity: Optional[datetime]
    created_at: datetime