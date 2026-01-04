"""Health check scheduler for automatic service testing."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from ..database.connection import get_db_manager
from ..models.service_config import ServiceConfig
from ..models.alert_config import AlertConfiguration
from .service_tester import ServiceTester
from .alert_service import alert_service

logger = logging.getLogger(__name__)


class HealthCheckScheduler:
    """Scheduler for automatic service health checks."""

    _instance: Optional["HealthCheckScheduler"] = None
    _task: Optional[asyncio.Task] = None

    def __init__(self):
        self._enabled: bool = False
        self._interval_minutes: int = 15  # Default: 15 minutes
        self._running: bool = False
        self._last_run: Optional[datetime] = None
        self._next_run: Optional[datetime] = None

    @classmethod
    def get_instance(cls) -> "HealthCheckScheduler":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = HealthCheckScheduler()
        return cls._instance

    @property
    def status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        return {
            "enabled": self._enabled,
            "interval_minutes": self._interval_minutes,
            "running": self._running,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "next_run": self._next_run.isoformat() if self._next_run else None,
        }

    async def start(self, interval_minutes: int = 15) -> None:
        """Start the health check scheduler."""
        if self._enabled:
            logger.info("Scheduler already running")
            return

        self._interval_minutes = interval_minutes
        self._enabled = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info(f"Health check scheduler started with {interval_minutes} minute interval")

    async def stop(self) -> None:
        """Stop the health check scheduler."""
        self._enabled = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._next_run = None
        logger.info("Health check scheduler stopped")

    async def update_interval(self, interval_minutes: int) -> None:
        """Update the check interval."""
        self._interval_minutes = interval_minutes
        logger.info(f"Health check interval updated to {interval_minutes} minutes")
        # Restart if running
        if self._enabled:
            await self.stop()
            await self.start(interval_minutes)

    async def _run_scheduler(self) -> None:
        """Main scheduler loop."""
        while self._enabled:
            try:
                # Calculate next run time
                self._next_run = datetime.utcnow()

                # Wait for the interval
                await asyncio.sleep(self._interval_minutes * 60)

                if not self._enabled:
                    break

                # Run health checks
                await self._run_health_checks()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check scheduler: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(60)

    async def _run_health_checks(self) -> None:
        """Run health checks on all enabled services."""
        self._running = True
        self._last_run = datetime.utcnow()
        logger.info("Starting scheduled health checks")

        try:
            db_manager = get_db_manager()
            async with db_manager.session_factory() as session:
                # Get all enabled services
                result = await session.execute(select(ServiceConfig).where(ServiceConfig.enabled == True))
                services = result.scalars().all()

                success_count = 0
                error_count = 0
                failed_services: List[ServiceConfig] = []

                for service in services:
                    try:
                        test_result = await ServiceTester.test_service_connection(service, db_session=session)
                        if test_result.success:
                            success_count += 1
                        else:
                            error_count += 1
                            failed_services.append(service)
                    except Exception as e:
                        logger.error(f"Error testing service {service.name}: {e}")
                        error_count += 1
                        failed_services.append(service)

                logger.info(f"Scheduled health checks completed: {success_count} success, {error_count} errors")

                # Check alerts for service test failures
                await self._check_service_alerts(session, failed_services, error_count > 0)

        except Exception as e:
            logger.error(f"Error running scheduled health checks: {e}")
        finally:
            self._running = False

    async def _check_service_alerts(
        self,
        session,
        failed_services: List[ServiceConfig],
        has_failures: bool
    ) -> None:
        """Check and trigger alerts for service test failures."""
        try:
            # Get all enabled alerts for service_test_failed metric type
            alert_result = await session.execute(
                select(AlertConfiguration).where(
                    AlertConfiguration.enabled == True,
                    AlertConfiguration.metric_type.in_(["service_test_failed", "service_down"])
                )
            )
            alerts = list(alert_result.scalars().all())

            if not alerts:
                return

            # Build context with failed service names
            failed_service_names = [s.name for s in failed_services]

            for alert_config in alerts:
                # For event-based alerts (service_test_failed), trigger when there are failures
                if alert_config.metric_type == "service_test_failed":
                    # If alert is specific to a service, check only that service
                    if alert_config.service_id:
                        failed_ids = [s.id for s in failed_services]
                        failed_service = next((s for s in failed_services if s.id == alert_config.service_id), None)
                        if alert_config.service_id in failed_ids and failed_service:
                            # Service failed - trigger alert with context
                            context = {"service_name": failed_service.name}
                            await alert_service.check_and_trigger_alert(session, alert_config, 1, context)
                        else:
                            # Service is OK - resolve if firing
                            if alert_config.is_firing:
                                await alert_service.check_and_trigger_alert(session, alert_config, 0)
                    else:
                        # Global alert - trigger if any service failed
                        if has_failures:
                            context = {"failed_services": failed_service_names}
                            await alert_service.check_and_trigger_alert(session, alert_config, len(failed_services), context)
                        elif alert_config.is_firing:
                            await alert_service.check_and_trigger_alert(session, alert_config, 0)

            logger.info(f"Alert check completed for {len(alerts)} alert configurations")

        except Exception as e:
            logger.error(f"Error checking service alerts: {e}")

    async def run_now(self) -> Dict[str, Any]:
        """Run health checks immediately (manual trigger)."""
        if self._running:
            return {"status": "already_running", "message": "Health checks are already running"}

        await self._run_health_checks()
        return {"status": "completed", "last_run": self._last_run.isoformat() if self._last_run else None}


# Global instance
health_scheduler = HealthCheckScheduler.get_instance()
