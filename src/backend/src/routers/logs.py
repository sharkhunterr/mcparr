"""Logs API router."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db_session
from src.models.base import LogLevel
from src.services.log_exporter import ExportFormat, log_exporter
from src.services.log_service import log_service

router = APIRouter(prefix="/api/logs")


class LogEntryCreate(BaseModel):
    """Schema for creating a log entry."""

    level: str = Field(default=LogLevel.INFO.value)
    message: str
    source: str
    component: Optional[str] = None
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    service_id: Optional[str] = None
    service_type: Optional[str] = None
    extra_data: Optional[dict] = None
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    stack_trace: Optional[str] = None
    duration_ms: Optional[int] = None


class LogEntryResponse(BaseModel):
    """Schema for log entry response."""

    id: str
    level: str
    message: str
    source: str
    component: Optional[str]
    correlation_id: Optional[str]
    request_id: Optional[str]
    user_id: Optional[str]
    service_id: Optional[str]
    service_type: Optional[str]
    extra_data: dict
    exception_type: Optional[str]
    exception_message: Optional[str]
    stack_trace: Optional[str]
    duration_ms: Optional[int]
    logged_at: datetime
    created_at: datetime


class LogListResponse(BaseModel):
    """Schema for paginated log list response."""

    items: List[LogEntryResponse]
    total: int
    skip: int
    limit: int


class LogStatsResponse(BaseModel):
    """Schema for log statistics response."""

    total: int
    by_level: dict
    by_source: dict
    error_rate: float
    period_hours: int


@router.get("/", response_model=LogListResponse)
async def list_logs(
    level: Optional[str] = Query(None, description="Filter by log level"),
    source: Optional[str] = Query(None, description="Filter by source"),
    service_id: Optional[str] = Query(None, description="Filter by service ID"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_time: Optional[datetime] = Query(None, description="Filter logs after this time"),
    end_time: Optional[datetime] = Query(None, description="Filter logs before this time"),
    search: Optional[str] = Query(None, description="Search in log message"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_db_session),
):
    """List log entries with filtering and pagination."""
    logs, total = await log_service.get_logs(
        session,
        level=level,
        source=source,
        service_id=service_id,
        correlation_id=correlation_id,
        user_id=user_id,
        start_time=start_time,
        end_time=end_time,
        search=search,
        skip=skip,
        limit=limit,
    )
    return LogListResponse(
        items=[LogEntryResponse(**log.to_dict()) for log in logs],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/stats", response_model=LogStatsResponse)
async def get_log_stats(
    hours: int = Query(24, ge=1, le=720, description="Time period in hours"),
    session: AsyncSession = Depends(get_db_session),
):
    """Get log statistics for the specified time period."""
    stats = await log_service.get_log_stats(session, hours=hours)
    return LogStatsResponse(**stats)


@router.get("/sources")
async def get_log_sources(
    session: AsyncSession = Depends(get_db_session),
):
    """Get all distinct log sources."""
    sources = await log_service.get_distinct_sources(session)
    return {"sources": sources}


@router.get("/components")
async def get_log_components(
    source: Optional[str] = Query(None, description="Filter by source"),
    session: AsyncSession = Depends(get_db_session),
):
    """Get all distinct log components."""
    components = await log_service.get_distinct_components(session, source=source)
    return {"components": components}


@router.get("/trace/{correlation_id}")
async def get_request_trace(
    correlation_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get all logs for a specific request trace (correlation ID)."""
    logs = await log_service.get_logs_by_correlation_id(session, correlation_id)
    return {
        "correlation_id": correlation_id,
        "logs": [LogEntryResponse(**log.to_dict()) for log in logs],
        "total": len(logs),
    }


@router.get("/levels/available")
async def get_log_levels():
    """Get all available log levels."""
    return {"levels": [level.value for level in LogLevel]}


@router.get("/export")
async def export_logs(
    format: ExportFormat = Query("json", description="Export format: json, csv, or text"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    source: Optional[str] = Query(None, description="Filter by source"),
    service_id: Optional[str] = Query(None, description="Filter by service ID"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_time: Optional[datetime] = Query(None, description="Filter logs after this time"),
    end_time: Optional[datetime] = Query(None, description="Filter logs before this time"),
    search: Optional[str] = Query(None, description="Search in log message"),
    limit: int = Query(10000, ge=1, le=100000, description="Maximum logs to export"),
    session: AsyncSession = Depends(get_db_session),
):
    """Export logs in the specified format (JSON, CSV, or text)."""
    content, content_type = await log_exporter.export_logs(
        session,
        format=format,
        level=level,
        source=source,
        service_id=service_id,
        correlation_id=correlation_id,
        user_id=user_id,
        start_time=start_time,
        end_time=end_time,
        search=search,
        limit=limit,
    )

    filename = log_exporter.get_filename(format)

    return Response(
        content=content, media_type=content_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{log_id}", response_model=LogEntryResponse)
async def get_log(
    log_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get a single log entry by ID."""
    log = await log_service.get_log_by_id(session, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log entry not found")
    return LogEntryResponse(**log.to_dict())


@router.post("/", response_model=LogEntryResponse)
async def create_log(
    log_data: LogEntryCreate,
    session: AsyncSession = Depends(get_db_session),
):
    """Create a new log entry."""
    log = await log_service.create_log(session, **log_data.model_dump())
    return LogEntryResponse(**log.to_dict())


@router.post("/cleanup")
async def cleanup_logs(
    session: AsyncSession = Depends(get_db_session),
):
    """Manually trigger log cleanup based on retention policy."""
    deleted_count = await log_service.cleanup_old_logs(session)
    return {
        "deleted": deleted_count,
        "retention_days": log_service.retention_days,
        "max_entries": log_service.max_entries,
    }
