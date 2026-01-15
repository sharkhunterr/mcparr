"""Services management API routes."""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db_session
from ..models.service_config import ServiceConfig, ServiceHealthHistory, ServiceType
from ..schemas.services import (
    ServiceConfigCreate,
    ServiceConfigResponse,
    ServiceConfigUpdate,
    ServiceTestResult,
)

router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("/", response_model=List[ServiceConfigResponse])
async def list_services(
    service_type: Optional[ServiceType] = None, enabled_only: bool = False, db: AsyncSession = Depends(get_db_session)
):
    """List all configured services."""
    query = select(ServiceConfig)

    if service_type:
        query = query.where(ServiceConfig.service_type == service_type)

    if enabled_only:
        query = query.where(ServiceConfig.enabled == True)

    result = await db.execute(query)
    services = result.scalars().all()

    return [ServiceConfigResponse.model_validate(service) for service in services]


@router.get("/{service_id}", response_model=ServiceConfigResponse)
async def get_service(service_id: str, db: AsyncSession = Depends(get_db_session)):
    """Get a specific service configuration."""
    result = await db.execute(select(ServiceConfig).where(ServiceConfig.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    return ServiceConfigResponse.model_validate(service)


@router.post("/", response_model=ServiceConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_service(service_data: ServiceConfigCreate, db: AsyncSession = Depends(get_db_session)):
    """Create a new service configuration."""
    # Check if service name already exists
    existing_service = (
        await db.execute(select(ServiceConfig).where(ServiceConfig.name == service_data.name))
    ).scalar_one_or_none()

    if existing_service:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Service with this name already exists")

    # Create new service
    service = ServiceConfig(**service_data.model_dump())
    db.add(service)
    await db.commit()
    await db.refresh(service)

    return ServiceConfigResponse.model_validate(service)


@router.put("/{service_id}", response_model=ServiceConfigResponse)
async def update_service(
    service_id: str, service_data: ServiceConfigUpdate, db: AsyncSession = Depends(get_db_session)
):
    """Update an existing service configuration."""
    result = await db.execute(select(ServiceConfig).where(ServiceConfig.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    # Update only provided fields
    update_data = service_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service, field, value)

    await db.commit()
    await db.refresh(service)

    return ServiceConfigResponse.model_validate(service)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(service_id: str, db: AsyncSession = Depends(get_db_session)):
    """Delete a service configuration."""
    result = await db.execute(select(ServiceConfig).where(ServiceConfig.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    await db.delete(service)
    await db.commit()


@router.post("/{service_id}/test", response_model=ServiceTestResult)
async def test_service_connection(service_id: str, db: AsyncSession = Depends(get_db_session)):
    """Test connection to a service."""
    result = await db.execute(select(ServiceConfig).where(ServiceConfig.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    # Import the service tester
    from ..models.alert_config import AlertConfiguration
    from ..services.alert_service import alert_service
    from ..services.service_tester import ServiceTester

    # Test the connection using the appropriate adapter
    test_result = await ServiceTester.test_service_connection(service, db)

    # Check alerts for this service test
    try:
        alert_result = await db.execute(
            select(AlertConfiguration).where(
                AlertConfiguration.enabled == True,
                AlertConfiguration.metric_type.in_(["service_test_failed", "service_down"]),
            )
        )
        alerts = list(alert_result.scalars().all())

        for alert_config in alerts:
            # Check if alert applies to this service or is global
            if alert_config.service_id is None or alert_config.service_id == service_id:
                # Build context with service info
                context = {
                    "service_name": service.name,
                    "error_message": test_result.message if not test_result.success else None,
                }
                if test_result.success:
                    # Service is OK - resolve if firing
                    if alert_config.is_firing:
                        await alert_service.check_and_trigger_alert(db, alert_config, 0, context)
                else:
                    # Service failed - trigger alert
                    await alert_service.check_and_trigger_alert(db, alert_config, 1, context)
    except Exception as e:
        # Don't fail the test response if alert check fails
        import logging

        logging.getLogger(__name__).error(f"Error checking alerts: {e}")

    return ServiceTestResult(
        service_id=service_id,
        success=test_result.success,
        error_message=test_result.message if not test_result.success else None,
        response_time_ms=test_result.response_time_ms,
    )


@router.patch("/{service_id}/enable")
async def enable_service(service_id: str, db: AsyncSession = Depends(get_db_session)):
    """Enable a service configuration."""
    result = await db.execute(select(ServiceConfig).where(ServiceConfig.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    service.enabled = True
    await db.commit()

    return {"message": "Service enabled successfully"}


@router.patch("/{service_id}/disable")
async def disable_service(service_id: str, db: AsyncSession = Depends(get_db_session)):
    """Disable a service configuration."""
    result = await db.execute(select(ServiceConfig).where(ServiceConfig.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    service.enabled = False
    await db.commit()

    return {"message": "Service disabled successfully"}


@router.get("/{service_id}/health", response_model=dict)
async def get_service_health(service_id: str, db: AsyncSession = Depends(get_db_session)):
    """Get service health status."""
    result = await db.execute(select(ServiceConfig).where(ServiceConfig.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    # Handle status - could be string or enum depending on how it was loaded
    status_value = service.status.value if hasattr(service.status, "value") else service.status

    return {
        "id": service_id,
        "name": service.name,
        "status": status_value,
        "enabled": service.enabled,
        "healthy": service.is_healthy,
        "last_test_at": service.last_test_at.isoformat() if service.last_test_at else None,
        "last_test_success": service.last_test_success,
        "last_error": service.last_error,
    }


@router.get("/health/history", response_model=List[dict])
async def get_all_services_health_history(hours: int = 24, db: AsyncSession = Depends(get_db_session)):
    """Get health history for all services for the specified time range."""
    since = datetime.utcnow() - timedelta(hours=hours)

    # Get all enabled services
    services_result = await db.execute(select(ServiceConfig).where(ServiceConfig.enabled == True))
    services = services_result.scalars().all()

    result = []
    for service in services:
        # Get health history for this service
        history_result = await db.execute(
            select(ServiceHealthHistory)
            .where(ServiceHealthHistory.service_id == service.id)
            .where(ServiceHealthHistory.tested_at >= since)
            .order_by(desc(ServiceHealthHistory.tested_at))
        )
        history = history_result.scalars().all()

        # Handle service_type - could be string or enum
        service_type_value = (
            service.service_type.value if hasattr(service.service_type, "value") else service.service_type
        )

        result.append(
            {
                "service_id": service.id,
                "service_name": service.name,
                "service_type": service_type_value,
                "enabled": service.enabled,
                "history": [
                    {
                        "tested_at": h.tested_at.isoformat(),
                        "success": h.success,
                        "response_time_ms": h.response_time_ms,
                        "error_message": h.error_message,
                    }
                    for h in history
                ],
            }
        )

    return result


@router.get("/{service_id}/health/history", response_model=dict)
async def get_service_health_history(service_id: str, hours: int = 24, db: AsyncSession = Depends(get_db_session)):
    """Get health history for a specific service."""
    # Get the service
    result = await db.execute(select(ServiceConfig).where(ServiceConfig.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    since = datetime.utcnow() - timedelta(hours=hours)

    # Get health history
    history_result = await db.execute(
        select(ServiceHealthHistory)
        .where(ServiceHealthHistory.service_id == service_id)
        .where(ServiceHealthHistory.tested_at >= since)
        .order_by(desc(ServiceHealthHistory.tested_at))
    )
    history = history_result.scalars().all()

    # Handle service_type - could be string or enum
    service_type_value = service.service_type.value if hasattr(service.service_type, "value") else service.service_type

    return {
        "service_id": service_id,
        "service_name": service.name,
        "service_type": service_type_value,
        "enabled": service.enabled,
        "history": [
            {
                "tested_at": h.tested_at.isoformat(),
                "success": h.success,
                "response_time_ms": h.response_time_ms,
                "error_message": h.error_message,
            }
            for h in history
        ],
        "summary": {
            "total_tests": len(history),
            "success_count": sum(1 for h in history if h.success),
            "failure_count": sum(1 for h in history if not h.success),
            "uptime_percentage": (sum(1 for h in history if h.success) / len(history) * 100) if history else 0,
            "avg_response_time_ms": (
                sum(h.response_time_ms or 0 for h in history if h.success)
                / max(1, sum(1 for h in history if h.success))
            ),
        },
    }


# =====================
# Health Check Scheduler Endpoints
# =====================


@router.get("/health/scheduler/status", response_model=dict)
async def get_scheduler_status():
    """Get the current status of the health check scheduler."""
    from ..services.health_scheduler import health_scheduler

    return health_scheduler.status


@router.post("/health/scheduler/start", response_model=dict)
async def start_scheduler(interval_minutes: int = 15):
    """Start the automatic health check scheduler."""
    from ..services.health_scheduler import health_scheduler

    if interval_minutes < 1 or interval_minutes > 1440:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Interval must be between 1 and 1440 minutes"
        )

    await health_scheduler.start(interval_minutes)
    return {"message": f"Scheduler started with {interval_minutes} minute interval", "status": health_scheduler.status}


@router.post("/health/scheduler/stop", response_model=dict)
async def stop_scheduler():
    """Stop the automatic health check scheduler."""
    from ..services.health_scheduler import health_scheduler

    await health_scheduler.stop()
    return {"message": "Scheduler stopped", "status": health_scheduler.status}


@router.put("/health/scheduler/interval", response_model=dict)
async def update_scheduler_interval(interval_minutes: int):
    """Update the health check interval."""
    from ..services.health_scheduler import health_scheduler

    if interval_minutes < 1 or interval_minutes > 1440:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Interval must be between 1 and 1440 minutes"
        )

    await health_scheduler.update_interval(interval_minutes)
    return {"message": f"Interval updated to {interval_minutes} minutes", "status": health_scheduler.status}


@router.post("/health/scheduler/run-now", response_model=dict)
async def run_health_checks_now():
    """Manually trigger health checks immediately."""
    from ..services.health_scheduler import health_scheduler

    result = await health_scheduler.run_now()
    return result
