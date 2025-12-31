"""Dashboard overview endpoints."""

from datetime import datetime, timedelta
from typing import Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db_session
from src.services.system_monitor import SystemMonitorService
from src.utils.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/api/v1/dashboard")


class ServiceStats(BaseModel):
    """Service statistics."""

    total: int
    active: int
    failing: int


class UserStats(BaseModel):
    """User statistics."""

    total: int
    active_sessions: int


class TrainingStats(BaseModel):
    """Training statistics."""

    active_sessions: int
    completed_today: int


class LogStats(BaseModel):
    """Log statistics."""

    recent_errors: int
    total_today: int


class McpStats(BaseModel):
    """MCP statistics."""

    requests_today: int
    average_response_time: float


class SystemStatus(BaseModel):
    """System status."""

    cpu_percent: float
    memory_used_mb: int
    memory_total_mb: int
    disk_used_gb: float
    disk_total_gb: float
    uptime_seconds: int
    docker_containers: Dict[str, int]


class DashboardOverview(BaseModel):
    """Dashboard overview response."""

    services: ServiceStats
    users: UserStats
    training: TrainingStats
    logs: LogStats
    mcp: McpStats
    system: SystemStatus


@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(db: AsyncSession = Depends(get_db_session)) -> DashboardOverview:
    """Get dashboard overview with system metrics and statistics."""

    logger.info("Dashboard overview requested", extra={"component": "dashboard", "action": "get_overview"})

    # Get system monitor service
    system_monitor = SystemMonitorService()

    # Get current system status
    system_status = await system_monitor.get_current_system_status()

    # Get recent system metrics for calculations
    datetime.utcnow() - timedelta(days=1)

    # Query recent metrics (this would be more complex with actual tables)
    # For now, return mock data with some real system metrics

    # Get docker container info
    docker_info = await system_monitor.get_docker_status()

    # Build response
    overview = DashboardOverview(
        services=ServiceStats(total=0, active=0, failing=0),  # Would query service_configurations table
        users=UserStats(total=0, active_sessions=1),  # Would query user_mappings table  # Current dashboard user
        training=TrainingStats(active_sessions=0, completed_today=0),  # Would query training_sessions table
        logs=LogStats(recent_errors=0, total_today=50),  # Would query log_entries table  # Mock data
        mcp=McpStats(requests_today=0, average_response_time=0.0),  # Would query mcp_requests table
        system=SystemStatus(
            cpu_percent=system_status.get("cpu_percent", 0.0),
            memory_used_mb=system_status.get("memory_used_mb", 0),
            memory_total_mb=system_status.get("memory_total_mb", 0),
            disk_used_gb=system_status.get("disk_used_gb", 0.0),
            disk_total_gb=system_status.get("disk_total_gb", 0.0),
            uptime_seconds=system_status.get("uptime_seconds", 0),
            docker_containers={
                "running": docker_info.get("containers_running", 0),
                "stopped": docker_info.get("containers_stopped", 0),
            },
        ),
    )

    logger.info(
        "Dashboard overview generated",
        extra={
            "component": "dashboard",
            "action": "overview_generated",
            "services_total": overview.services.total,
            "system_cpu": overview.system.cpu_percent,
            "system_memory_mb": overview.system.memory_used_mb,
        },
    )

    return overview
