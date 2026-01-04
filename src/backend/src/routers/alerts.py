"""Alerts API router."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db_session
from src.models.base import AlertSeverity, MetricType, ThresholdOperator
from src.services.alert_service import alert_service

router = APIRouter(prefix="/api/alerts")


class AlertConfigCreate(BaseModel):
    """Schema for creating an alert configuration."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    enabled: bool = True
    severity: str = AlertSeverity.MEDIUM.value
    metric_type: str = MetricType.CPU.value
    threshold_operator: str = ThresholdOperator.GT.value
    threshold_value: float
    duration_seconds: int = Field(default=60, ge=0)
    service_id: Optional[str] = None
    service_type: Optional[str] = None
    notification_channels: List[str] = []
    notification_config: dict = {}
    cooldown_minutes: int = Field(default=15, ge=0)
    tags: dict = {}


class AlertConfigUpdate(BaseModel):
    """Schema for updating an alert configuration."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    enabled: Optional[bool] = None
    severity: Optional[str] = None
    metric_type: Optional[str] = None
    threshold_operator: Optional[str] = None
    threshold_value: Optional[float] = None
    duration_seconds: Optional[int] = None
    service_id: Optional[str] = None
    service_type: Optional[str] = None
    notification_channels: Optional[List[str]] = None
    notification_config: Optional[dict] = None
    cooldown_minutes: Optional[int] = None
    tags: Optional[dict] = None


class AlertConfigResponse(BaseModel):
    """Schema for alert configuration response."""

    id: str
    name: str
    description: Optional[str]
    enabled: bool
    severity: str
    metric_type: str
    threshold_operator: str
    threshold_value: float
    duration_seconds: int
    service_id: Optional[str]
    service_type: Optional[str]
    notification_channels: List[str]
    notification_config: dict
    cooldown_minutes: int
    last_triggered_at: Optional[datetime]
    trigger_count: int
    is_firing: bool
    tags: dict
    created_at: datetime
    updated_at: datetime


class AlertConfigListResponse(BaseModel):
    """Schema for paginated alert config list response."""

    items: List[AlertConfigResponse]
    total: int
    skip: int
    limit: int


class AlertHistoryResponse(BaseModel):
    """Schema for alert history response."""

    id: str
    alert_config_id: str
    alert_name: str
    severity: str
    triggered_at: datetime
    resolved_at: Optional[datetime]
    is_resolved: bool
    metric_value: float
    threshold_value: float
    service_id: Optional[str]
    message: str
    notifications_sent: bool
    notification_details: dict
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    created_at: datetime


class AlertHistoryListResponse(BaseModel):
    """Schema for paginated alert history list response."""

    items: List[AlertHistoryResponse]
    total: int
    skip: int
    limit: int


class AlertStatsResponse(BaseModel):
    """Schema for alert statistics response."""

    total_triggered: int
    active_count: int
    by_severity: dict
    mttr_seconds: float
    mttr_formatted: str
    period_hours: int


# Alert Configurations endpoints


@router.get("/configs", response_model=AlertConfigListResponse)
async def list_alert_configs(
    enabled_only: bool = Query(False, description="Only show enabled alerts"),
    service_id: Optional[str] = Query(None, description="Filter by service ID"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_db_session),
):
    """List alert configurations with filtering."""
    configs, total = await alert_service.get_alert_configs(
        session,
        enabled_only=enabled_only,
        service_id=service_id,
        severity=severity,
        skip=skip,
        limit=limit,
    )
    return AlertConfigListResponse(
        items=[AlertConfigResponse(**config.to_dict()) for config in configs],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/configs/{config_id}", response_model=AlertConfigResponse)
async def get_alert_config(
    config_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get a single alert configuration by ID."""
    config = await alert_service.get_alert_config_by_id(session, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Alert configuration not found")
    return AlertConfigResponse(**config.to_dict())


@router.post("/configs", response_model=AlertConfigResponse, status_code=201)
async def create_alert_config(
    config_data: AlertConfigCreate,
    session: AsyncSession = Depends(get_db_session),
):
    """Create a new alert configuration."""
    config = await alert_service.create_alert_config(session, **config_data.model_dump())
    return AlertConfigResponse(**config.to_dict())


@router.patch("/configs/{config_id}", response_model=AlertConfigResponse)
async def update_alert_config(
    config_id: str,
    config_data: AlertConfigUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    """Update an alert configuration."""
    config = await alert_service.update_alert_config(session, config_id, **config_data.model_dump(exclude_unset=True))
    if not config:
        raise HTTPException(status_code=404, detail="Alert configuration not found")
    return AlertConfigResponse(**config.to_dict())


@router.delete("/configs/{config_id}")
async def delete_alert_config(
    config_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Delete an alert configuration."""
    deleted = await alert_service.delete_alert_config(session, config_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Alert configuration not found")
    return {"deleted": True, "id": config_id}


@router.post("/configs/{config_id}/toggle")
async def toggle_alert_config(
    config_id: str,
    enabled: bool = Query(..., description="Enable or disable the alert"),
    session: AsyncSession = Depends(get_db_session),
):
    """Enable or disable an alert configuration."""
    config = await alert_service.toggle_alert_config(session, config_id, enabled)
    if not config:
        raise HTTPException(status_code=404, detail="Alert configuration not found")
    return AlertConfigResponse(**config.to_dict())


# Alert History endpoints


@router.get("/history", response_model=AlertHistoryListResponse)
async def list_alert_history(
    config_id: Optional[str] = Query(None, description="Filter by alert config ID"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    is_resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    start_time: Optional[datetime] = Query(None, description="Filter alerts after this time"),
    end_time: Optional[datetime] = Query(None, description="Filter alerts before this time"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_db_session),
):
    """List alert history with filtering."""
    history, total = await alert_service.get_alert_history(
        session,
        config_id=config_id,
        severity=severity,
        is_resolved=is_resolved,
        start_time=start_time,
        end_time=end_time,
        skip=skip,
        limit=limit,
    )
    return AlertHistoryListResponse(
        items=[AlertHistoryResponse(**h.to_dict()) for h in history],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/active", response_model=List[AlertHistoryResponse])
async def get_active_alerts(
    session: AsyncSession = Depends(get_db_session),
):
    """Get all currently active (unresolved) alerts."""
    alerts = await alert_service.get_active_alerts(session)
    return [AlertHistoryResponse(**alert.to_dict()) for alert in alerts]


@router.post("/history/{history_id}/resolve", response_model=AlertHistoryResponse)
async def resolve_alert(
    history_id: str,
    message: Optional[str] = Query(None, description="Resolution message"),
    session: AsyncSession = Depends(get_db_session),
):
    """Manually resolve an alert."""
    history = await alert_service.resolve_alert(session, history_id, message)
    if not history:
        raise HTTPException(status_code=404, detail="Alert not found or already resolved")
    return AlertHistoryResponse(**history.to_dict())


@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_stats(
    hours: int = Query(24, ge=1, le=720, description="Time period in hours"),
    session: AsyncSession = Depends(get_db_session),
):
    """Get alert statistics for the specified time period."""
    stats = await alert_service.get_alert_stats(session, hours=hours)
    return AlertStatsResponse(**stats)


# Metadata endpoints


@router.get("/severities")
async def get_alert_severities():
    """Get all available alert severities."""
    return {"severities": [severity.value for severity in AlertSeverity]}


@router.get("/metric-types")
async def get_metric_types():
    """Get all available metric types."""
    return {"metric_types": [metric.value for metric in MetricType]}


@router.get("/operators")
async def get_threshold_operators():
    """Get all available threshold operators."""
    return {"operators": [{"value": op.value, "label": op.name.replace("_", " ").title()} for op in ThresholdOperator]}
