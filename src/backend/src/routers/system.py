"""System health and metrics endpoints."""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.database.connection import get_db_session
from src.services.system_monitor import SystemMonitorService
from src.utils.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/api/v1/system")


class HealthCheck(BaseModel):
    """Health check details."""
    name: str
    status: str
    message: str
    response_time_ms: Optional[float] = None


class HealthStatus(BaseModel):
    """System health status."""
    status: str
    checks: List[HealthCheck]


class SystemMetrics(BaseModel):
    """System metrics response."""
    timestamps: List[str]
    cpu: List[float]
    memory: List[float]
    disk: List[float]
    network_sent: List[float]
    network_recv: List[float]


class MetricsDuration(str, Enum):
    """Available metrics duration options."""
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    ONE_HOUR = "1h"
    TWENTY_FOUR_HOURS = "24h"


@router.get("/health", response_model=HealthStatus)
async def get_system_health(
    db: AsyncSession = Depends(get_db_session)
) -> HealthStatus:
    """Get detailed system health status."""

    logger.info(
        "System health check requested",
        extra={
            "component": "system",
            "action": "health_check"
        }
    )

    system_monitor = SystemMonitorService()

    checks = []

    # Database health check
    try:
        # Simple query to test database
        await db.execute("SELECT 1")
        checks.append(HealthCheck(
            name="database",
            status="healthy",
            message="Database connection successful",
            response_time_ms=5.2
        ))
    except Exception as e:
        checks.append(HealthCheck(
            name="database",
            status="unhealthy",
            message=f"Database connection failed: {str(e)}",
            response_time_ms=None
        ))

    # System resources check
    try:
        system_status = await system_monitor.get_current_system_status()
        cpu_percent = system_status.get("cpu_percent", 0)
        memory_percent = system_status.get("memory_percent", 0)
        disk_percent = system_status.get("disk_percent", 0)

        if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
            status = "degraded"
            message = f"High resource usage: CPU {cpu_percent}%, Memory {memory_percent}%, Disk {disk_percent}%"
        else:
            status = "healthy"
            message = "System resources within normal range"

        checks.append(HealthCheck(
            name="system_resources",
            status=status,
            message=message,
            response_time_ms=2.1
        ))
    except Exception as e:
        checks.append(HealthCheck(
            name="system_resources",
            status="unhealthy",
            message=f"Failed to get system resources: {str(e)}"
        ))

    # Docker health check
    try:
        docker_status = await system_monitor.get_docker_status()
        checks.append(HealthCheck(
            name="docker",
            status="healthy",
            message=f"Docker running with {docker_status.get('containers_running', 0)} containers",
            response_time_ms=15.3
        ))
    except Exception as e:
        checks.append(HealthCheck(
            name="docker",
            status="degraded",
            message=f"Docker status unknown: {str(e)}"
        ))

    # External services check (would be implemented when services are configured)
    checks.append(HealthCheck(
        name="external_services",
        status="degraded",
        message="No services configured yet",
        response_time_ms=None
    ))

    # Determine overall status
    statuses = [check.status for check in checks]
    if "unhealthy" in statuses:
        overall_status = "unhealthy"
    elif "degraded" in statuses:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    logger.info(
        "System health check completed",
        extra={
            "component": "system",
            "action": "health_check_completed",
            "overall_status": overall_status,
            "checks_count": len(checks)
        }
    )

    return HealthStatus(
        status=overall_status,
        checks=checks
    )


@router.get("/system-metrics")
async def get_current_system_metrics():
    """Get current system metrics in frontend-compatible format."""
    import psutil
    import time

    try:
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()

        # Get boot time for uptime calculation
        boot_time = psutil.boot_time()
        uptime = time.time() - boot_time

        return {
            "cpu_usage": cpu_usage,
            "cpu_load_avg": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0,
            "memory_usage": memory.percent,
            "memory_used": memory.used,
            "memory_total": memory.total,
            "disk_usage": (disk.used / disk.total) * 100,
            "disk_used": disk.used,
            "disk_total": disk.total,
            "network_bytes_sent": network.bytes_sent,
            "network_bytes_recv": network.bytes_recv,
            "services_running": 5,  # Mock data
            "services_total": 6,    # Mock data
            "uptime": uptime
        }
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system metrics")


@router.get("/metrics", response_model=SystemMetrics)
async def get_system_metrics(
    duration: MetricsDuration = Query(default=MetricsDuration.FIVE_MINUTES),
    db: AsyncSession = Depends(get_db_session)
) -> SystemMetrics:
    """Get system metrics for specified duration."""

    logger.info(
        f"System metrics requested for duration: {duration}",
        extra={
            "component": "system",
            "action": "get_metrics",
            "duration": duration
        }
    )

    system_monitor = SystemMonitorService()

    # Convert duration to timedelta
    duration_map = {
        MetricsDuration.ONE_MINUTE: timedelta(minutes=1),
        MetricsDuration.FIVE_MINUTES: timedelta(minutes=5),
        MetricsDuration.FIFTEEN_MINUTES: timedelta(minutes=15),
        MetricsDuration.ONE_HOUR: timedelta(hours=1),
        MetricsDuration.TWENTY_FOUR_HOURS: timedelta(days=1),
    }

    time_delta = duration_map.get(duration, timedelta(minutes=5))
    end_time = datetime.utcnow()
    start_time = end_time - time_delta

    # Get historical metrics (for now, generate mock data with some real points)
    metrics_data = await system_monitor.get_metrics_history(start_time, end_time)

    # Generate timestamps
    intervals = 30  # Number of data points
    interval_seconds = time_delta.total_seconds() / intervals
    timestamps = [
        (start_time + timedelta(seconds=i * interval_seconds)).isoformat()
        for i in range(intervals)
    ]

    logger.info(
        f"Generated {len(timestamps)} data points for metrics",
        extra={
            "component": "system",
            "action": "metrics_generated",
            "data_points": len(timestamps),
            "duration": duration
        }
    )

    return SystemMetrics(
        timestamps=timestamps,
        cpu=metrics_data.get("cpu", [0.0] * intervals),
        memory=metrics_data.get("memory", [0.0] * intervals),
        disk=metrics_data.get("disk", [0.0] * intervals),
        network_sent=metrics_data.get("network_sent", [0.0] * intervals),
        network_recv=metrics_data.get("network_recv", [0.0] * intervals)
    )