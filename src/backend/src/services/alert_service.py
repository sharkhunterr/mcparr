"""Alert management service."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.alert_config import AlertConfiguration, AlertHistory
from src.models.base import AlertSeverity


class AlertService:
    """Service for managing alerts and alert configurations."""

    async def create_alert_config(
        self,
        session: AsyncSession,
        name: str,
        metric_type: str,
        threshold_operator: str,
        threshold_value: float,
        severity: str = AlertSeverity.MEDIUM.value,
        description: Optional[str] = None,
        enabled: bool = True,
        duration_seconds: int = 60,
        service_id: Optional[str] = None,
        service_type: Optional[str] = None,
        notification_channels: Optional[List[str]] = None,
        notification_config: Optional[Dict[str, Any]] = None,
        cooldown_minutes: int = 15,
        tags: Optional[Dict[str, str]] = None,
    ) -> AlertConfiguration:
        """Create a new alert configuration."""
        config = AlertConfiguration(
            name=name,
            description=description,
            enabled=enabled,
            severity=severity,
            metric_type=metric_type,
            threshold_operator=threshold_operator,
            threshold_value=threshold_value,
            duration_seconds=duration_seconds,
            service_id=service_id,
            service_type=service_type,
            notification_channels=notification_channels or [],
            notification_config=notification_config or {},
            cooldown_minutes=cooldown_minutes,
            tags=tags or {},
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)
        return config

    async def get_alert_configs(
        self,
        session: AsyncSession,
        enabled_only: bool = False,
        service_id: Optional[str] = None,
        severity: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[AlertConfiguration], int]:
        """Get alert configurations with filtering."""
        query = select(AlertConfiguration)

        if enabled_only:
            query = query.where(AlertConfiguration.enabled == True)
        if service_id:
            query = query.where(AlertConfiguration.service_id == service_id)
        if severity:
            query = query.where(AlertConfiguration.severity == severity)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await session.scalar(count_query)

        # Apply pagination
        query = query.order_by(AlertConfiguration.created_at.desc()).offset(skip).limit(limit)

        result = await session.execute(query)
        configs = list(result.scalars().all())

        return configs, total or 0

    async def get_alert_config_by_id(self, session: AsyncSession, config_id: str) -> Optional[AlertConfiguration]:
        """Get a single alert configuration by ID."""
        query = select(AlertConfiguration).where(AlertConfiguration.id == config_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def update_alert_config(
        self, session: AsyncSession, config_id: str, **updates
    ) -> Optional[AlertConfiguration]:
        """Update an alert configuration."""
        config = await self.get_alert_config_by_id(session, config_id)
        if not config:
            return None

        for key, value in updates.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)

        await session.commit()
        await session.refresh(config)
        return config

    async def delete_alert_config(self, session: AsyncSession, config_id: str) -> bool:
        """Delete an alert configuration."""
        config = await self.get_alert_config_by_id(session, config_id)
        if not config:
            return False

        await session.delete(config)
        await session.commit()
        return True

    async def toggle_alert_config(
        self, session: AsyncSession, config_id: str, enabled: bool
    ) -> Optional[AlertConfiguration]:
        """Enable or disable an alert configuration."""
        return await self.update_alert_config(session, config_id, enabled=enabled)

    async def check_and_trigger_alert(
        self,
        session: AsyncSession,
        config: AlertConfiguration,
        current_value: float,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[AlertHistory]:
        """Check if an alert should be triggered and create history entry.

        Args:
            session: Database session
            config: Alert configuration to check
            current_value: Current metric value
            context: Optional context dict with extra info:
                - service_name: Name of the affected service
                - error_message: Error message from the test
                - failed_services: List of failed service names (for global alerts)
        """
        should_trigger = config.check_threshold(current_value)
        context = context or {}

        if should_trigger and not config.is_firing:
            # Check cooldown
            if config.last_triggered_at:
                cooldown_until = config.last_triggered_at + timedelta(minutes=config.cooldown_minutes)
                if datetime.utcnow() < cooldown_until:
                    return None

            # Trigger alert
            config.is_firing = True
            config.trigger_count += 1
            config.last_triggered_at = datetime.utcnow()

            # Build a clear, informative message
            message = self._build_alert_message(config, current_value, context)

            history = AlertHistory(
                alert_config_id=config.id,
                alert_name=config.name,
                severity=config.severity,
                triggered_at=datetime.utcnow(),
                metric_value=current_value,
                threshold_value=config.threshold_value,
                service_id=config.service_id,
                message=message,
            )
            session.add(history)
            await session.commit()
            await session.refresh(history)
            return history

        elif not should_trigger and config.is_firing:
            # Resolve alert
            config.is_firing = False
            await session.commit()

        return None

    async def resolve_alert(
        self,
        session: AsyncSession,
        history_id: str,
        message: Optional[str] = None,
    ) -> Optional[AlertHistory]:
        """Manually resolve an alert."""
        query = select(AlertHistory).where(AlertHistory.id == history_id)
        result = await session.execute(query)
        history = result.scalar_one_or_none()

        if not history or history.is_resolved:
            return None

        history.is_resolved = True
        history.resolved_at = datetime.utcnow()
        # Also acknowledge the alert when resolving
        if not history.acknowledged:
            history.acknowledged = True
            history.acknowledged_at = datetime.utcnow()
        if message:
            history.message = f"{history.message}\nResolution: {message}"

        # Update the config's firing state
        config_query = select(AlertConfiguration).where(AlertConfiguration.id == history.alert_config_id)
        config_result = await session.execute(config_query)
        config = config_result.scalar_one_or_none()
        if config:
            config.is_firing = False

        await session.commit()
        await session.refresh(history)
        return history

    async def get_alert_history(
        self,
        session: AsyncSession,
        config_id: Optional[str] = None,
        severity: Optional[str] = None,
        is_resolved: Optional[bool] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[AlertHistory], int]:
        """Get alert history with filtering."""
        query = select(AlertHistory)

        if config_id:
            query = query.where(AlertHistory.alert_config_id == config_id)
        if severity:
            query = query.where(AlertHistory.severity == severity)
        if is_resolved is not None:
            query = query.where(AlertHistory.is_resolved == is_resolved)
        if start_time:
            query = query.where(AlertHistory.triggered_at >= start_time)
        if end_time:
            query = query.where(AlertHistory.triggered_at <= end_time)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await session.scalar(count_query)

        # Apply pagination
        query = query.order_by(AlertHistory.triggered_at.desc()).offset(skip).limit(limit)

        result = await session.execute(query)
        history = list(result.scalars().all())

        return history, total or 0

    async def get_active_alerts(self, session: AsyncSession) -> List[AlertHistory]:
        """Get all currently active (unresolved) alerts."""
        query = select(AlertHistory).where(AlertHistory.is_resolved == False).order_by(AlertHistory.triggered_at.desc())
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_alert_stats(self, session: AsyncSession, hours: int = 24) -> Dict[str, Any]:
        """Get alert statistics for the specified time period."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        # Count by severity
        severity_query = (
            select(AlertHistory.severity, func.count(AlertHistory.id))
            .where(AlertHistory.triggered_at >= cutoff)
            .group_by(AlertHistory.severity)
        )
        severity_result = await session.execute(severity_query)
        severity_counts = dict(severity_result.all())

        # Count unacknowledged alerts (for notification badge)
        active_query = select(func.count(AlertHistory.id)).where(
            AlertHistory.is_resolved == False,
            AlertHistory.acknowledged == False
        )
        active_count = await session.scalar(active_query) or 0

        # Total triggered in period
        total_query = select(func.count(AlertHistory.id)).where(AlertHistory.triggered_at >= cutoff)
        total = await session.scalar(total_query) or 0

        # Mean time to resolution
        resolved_query = select(AlertHistory).where(
            AlertHistory.triggered_at >= cutoff,
            AlertHistory.is_resolved == True,
            AlertHistory.resolved_at.isnot(None),
        )
        resolved_result = await session.execute(resolved_query)
        resolved_alerts = list(resolved_result.scalars().all())

        mttr_seconds = 0
        if resolved_alerts:
            total_resolution_time = sum(
                (alert.resolved_at - alert.triggered_at).total_seconds()
                for alert in resolved_alerts
                if alert.resolved_at
            )
            mttr_seconds = total_resolution_time / len(resolved_alerts)

        return {
            "total_triggered": total,
            "active_count": active_count,
            "by_severity": severity_counts,
            "mttr_seconds": round(mttr_seconds, 2),
            "mttr_formatted": self._format_duration(mttr_seconds),
            "period_hours": hours,
        }

    def _format_duration(self, seconds: float) -> str:
        """Format seconds into human readable duration."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds / 60)}m"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"

    def _build_alert_message(
        self,
        config: AlertConfiguration,
        current_value: float,
        context: Dict[str, Any],
    ) -> str:
        """Build a clear, human-readable alert message.

        Args:
            config: Alert configuration
            current_value: Current metric value
            context: Context dict with service_name, error_message, failed_services, etc.
        """
        service_name = context.get("service_name")
        error_message = context.get("error_message")
        failed_services = context.get("failed_services", [])

        # For service-specific alerts (service down, test failed)
        if config.metric_type in ("service_test_failed", "service_down"):
            if service_name:
                # Single service alert
                msg = f"Service '{service_name}' is down"
                if error_message:
                    msg += f": {error_message}"
                return msg
            elif failed_services:
                # Global alert with multiple services
                if len(failed_services) == 1:
                    return f"Service '{failed_services[0]}' is down"
                else:
                    services_str = ", ".join(failed_services[:3])
                    if len(failed_services) > 3:
                        services_str += f" (+{len(failed_services) - 3} more)"
                    return f"{len(failed_services)} services down: {services_str}"
            else:
                return f"Service test failed"

        # For metric-based alerts (CPU, memory, etc.)
        operator_symbols = {
            "gt": ">",
            "lt": "<",
            "eq": "=",
            "ne": "≠",
            "gte": "≥",
            "lte": "≤",
        }
        op_symbol = operator_symbols.get(config.threshold_operator, config.threshold_operator)

        # Add unit based on metric type
        units = {
            "cpu": "%",
            "memory": "%",
            "disk": "%",
            "response_time": "ms",
        }
        unit = units.get(config.metric_type, "")

        msg = f"{config.metric_type}: {current_value}{unit} {op_symbol} {config.threshold_value}{unit}"

        # Add description if available
        if config.description:
            msg = f"{config.description} ({msg})"

        # Add service name if available
        if service_name:
            msg = f"[{service_name}] {msg}"

        return msg


# Global alert service instance
alert_service = AlertService()
