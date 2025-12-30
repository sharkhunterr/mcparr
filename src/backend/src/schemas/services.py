"""Pydantic schemas for services."""

from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict

from ..models.service_config import ServiceType, ServiceStatus


class ServiceConfigBase(BaseModel):
    """Base service configuration schema."""
    name: str = Field(..., min_length=1, max_length=100)
    service_type: ServiceType
    description: Optional[str] = None
    base_url: str = Field(..., min_length=1, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    health_check_interval: int = Field(300, ge=60)  # minimum 1 minute
    health_check_enabled: bool = True
    version: Optional[str] = Field(None, max_length=50)
    tags: Dict[str, Any] = Field(default_factory=dict)


class ServiceConfigCreate(ServiceConfigBase):
    """Schema for creating a service configuration."""
    api_key: Optional[str] = Field(None, max_length=2000)  # JWT tokens can be long
    username: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, max_length=255)


class ServiceConfigUpdate(BaseModel):
    """Schema for updating a service configuration."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    base_url: Optional[str] = Field(None, min_length=1, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    api_key: Optional[str] = Field(None, max_length=2000)  # JWT tokens can be long
    username: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, max_length=255)
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    health_check_interval: Optional[int] = Field(None, ge=60)
    health_check_enabled: Optional[bool] = None
    version: Optional[str] = Field(None, max_length=50)
    tags: Optional[Dict[str, Any]] = None


class ServiceConfigResponse(ServiceConfigBase):
    """Schema for service configuration responses."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    status: ServiceStatus
    last_test_at: Optional[datetime] = None
    last_test_success: Optional[bool] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Computed properties
    @property
    def full_url(self) -> str:
        """Get the full URL for the service."""
        if self.port:
            return f"{self.base_url}:{self.port}"
        return self.base_url

    @property
    def is_healthy(self) -> bool:
        """Check if service is healthy based on last test."""
        return (
            self.status == ServiceStatus.ACTIVE and
            self.last_test_success is True and
            self.enabled
        )


class ServiceTestResult(BaseModel):
    """Schema for service connection test results."""
    service_id: str
    success: bool
    error_message: Optional[str] = None
    response_time_ms: Optional[int] = None
    tested_at: datetime = Field(default_factory=datetime.utcnow)


class ServiceHealthStatus(BaseModel):
    """Schema for service health status."""
    service_id: str
    name: str
    status: ServiceStatus
    enabled: bool
    healthy: bool
    last_test_at: Optional[datetime] = None
    last_test_success: Optional[bool] = None
    last_error: Optional[str] = None