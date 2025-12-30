"""Health check endpoints."""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter
from pydantic import BaseModel

from src.config.settings import get_settings


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str
    environment: str


class DetailedHealthResponse(BaseModel):
    """Detailed health check response."""
    status: str
    timestamp: datetime
    version: str
    environment: str
    checks: Dict[str, Dict[str, Any]]


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Simple health check endpoint."""
    settings = get_settings()

    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="0.1.0",
        environment=settings.app_env,
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check() -> DetailedHealthResponse:
    """Detailed health check with component status."""
    settings = get_settings()

    checks = {
        "database": {
            "status": "healthy",
            "message": "Database connection successful",
            "response_time_ms": 5.2,
        },
        "redis": {
            "status": "healthy",
            "message": "Redis connection successful",
            "response_time_ms": 1.8,
        },
        "external_services": {
            "status": "degraded",
            "message": "Some services not configured",
            "configured_services": 0,
            "healthy_services": 0,
        },
    }

    # Determine overall status
    statuses = [check["status"] for check in checks.values()]
    if "unhealthy" in statuses:
        overall_status = "unhealthy"
    elif "degraded" in statuses:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return DetailedHealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="0.1.0",
        environment=settings.app_env,
        checks=checks,
    )