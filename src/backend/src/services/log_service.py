"""Log collection and retention service."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.alert_config import AlertHistory
from src.models.base import LogLevel
from src.models.log_entry import LogEntry


class LogService:
    """Service for managing log entries and retention policies."""

    def __init__(self, retention_days: int = 30, max_entries: int = 100000, cleanup_interval_hours: int = 6):
        self.retention_days = retention_days
        self.max_entries = max_entries
        self.cleanup_interval_hours = cleanup_interval_hours
        self._cleanup_task: Optional[asyncio.Task] = None

    async def create_log(
        self,
        session: AsyncSession,
        level: str,
        message: str,
        source: str,
        component: Optional[str] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        service_id: Optional[str] = None,
        service_type: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        exception_type: Optional[str] = None,
        exception_message: Optional[str] = None,
        stack_trace: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> LogEntry:
        """Create a new log entry."""
        log_entry = LogEntry(
            level=level,
            message=message,
            source=source,
            component=component,
            correlation_id=correlation_id,
            request_id=request_id,
            user_id=user_id,
            service_id=service_id,
            service_type=service_type,
            extra_data=extra_data or {},
            exception_type=exception_type,
            exception_message=exception_message,
            stack_trace=stack_trace,
            duration_ms=duration_ms,
            logged_at=datetime.utcnow(),
        )
        session.add(log_entry)
        await session.commit()
        await session.refresh(log_entry)
        return log_entry

    async def get_logs(
        self,
        session: AsyncSession,
        level: Optional[str] = None,
        source: Optional[str] = None,
        service_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[LogEntry], int]:
        """Get logs with filtering and pagination."""
        query = select(LogEntry)

        # Apply filters
        if level:
            query = query.where(LogEntry.level == level)
        if source:
            query = query.where(LogEntry.source == source)
        if service_id:
            query = query.where(LogEntry.service_id == service_id)
        if correlation_id:
            query = query.where(LogEntry.correlation_id == correlation_id)
        if user_id:
            query = query.where(LogEntry.user_id == user_id)
        if start_time:
            query = query.where(LogEntry.logged_at >= start_time)
        if end_time:
            query = query.where(LogEntry.logged_at <= end_time)
        if search:
            query = query.where(LogEntry.message.ilike(f"%{search}%"))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await session.scalar(count_query)

        # Apply pagination and ordering
        query = query.order_by(LogEntry.logged_at.desc()).offset(skip).limit(limit)

        result = await session.execute(query)
        logs = list(result.scalars().all())

        return logs, total or 0

    async def get_log_by_id(self, session: AsyncSession, log_id: str) -> Optional[LogEntry]:
        """Get a single log entry by ID."""
        query = select(LogEntry).where(LogEntry.id == log_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def get_logs_by_correlation_id(self, session: AsyncSession, correlation_id: str) -> List[LogEntry]:
        """Get all logs for a specific correlation ID (request trace)."""
        query = select(LogEntry).where(LogEntry.correlation_id == correlation_id).order_by(LogEntry.logged_at.asc())
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_log_stats(self, session: AsyncSession, hours: int = 24) -> Dict[str, Any]:
        """Get log statistics for the specified time period."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        # Count by level
        level_query = (
            select(LogEntry.level, func.count(LogEntry.id)).where(LogEntry.logged_at >= cutoff).group_by(LogEntry.level)
        )
        level_result = await session.execute(level_query)
        level_counts = dict(level_result.all())

        # Count by source
        source_query = (
            select(LogEntry.source, func.count(LogEntry.id))
            .where(LogEntry.logged_at >= cutoff)
            .group_by(LogEntry.source)
        )
        source_result = await session.execute(source_query)
        source_counts = dict(source_result.all())

        # Total count
        total_query = select(func.count(LogEntry.id)).where(LogEntry.logged_at >= cutoff)
        total = await session.scalar(total_query) or 0

        # Error rate
        error_count = level_counts.get(LogLevel.ERROR.value, 0) + level_counts.get(LogLevel.CRITICAL.value, 0)
        error_rate = (error_count / total * 100) if total > 0 else 0

        return {
            "total": total,
            "by_level": level_counts,
            "by_source": source_counts,
            "error_rate": round(error_rate, 2),
            "period_hours": hours,
        }

    async def cleanup_old_logs(self, session: AsyncSession) -> int:
        """Remove logs older than retention period and enforce max entries."""
        deleted_count = 0

        # Delete logs older than retention period
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        delete_query = delete(LogEntry).where(LogEntry.logged_at < cutoff_date)
        result = await session.execute(delete_query)
        deleted_count += result.rowcount

        # Enforce max entries limit
        total_query = select(func.count(LogEntry.id))
        total = await session.scalar(total_query) or 0

        if total > self.max_entries:
            # Get IDs of oldest entries to delete
            excess = total - self.max_entries
            oldest_query = select(LogEntry.id).order_by(LogEntry.logged_at.asc()).limit(excess)
            oldest_result = await session.execute(oldest_query)
            oldest_ids = [row[0] for row in oldest_result.all()]

            if oldest_ids:
                delete_excess = delete(LogEntry).where(LogEntry.id.in_(oldest_ids))
                result = await session.execute(delete_excess)
                deleted_count += result.rowcount

        await session.commit()
        return deleted_count

    async def cleanup_old_alerts(self, session: AsyncSession, days: int = 90) -> int:
        """Remove resolved alert history older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        delete_query = delete(AlertHistory).where(
            AlertHistory.is_resolved == True, AlertHistory.resolved_at < cutoff_date
        )
        result = await session.execute(delete_query)
        await session.commit()
        return result.rowcount

    async def get_distinct_sources(self, session: AsyncSession) -> List[str]:
        """Get all distinct log sources."""
        query = select(LogEntry.source).distinct()
        result = await session.execute(query)
        return [row[0] for row in result.all()]

    async def get_distinct_components(self, session: AsyncSession, source: Optional[str] = None) -> List[str]:
        """Get all distinct log components, optionally filtered by source."""
        query = select(LogEntry.component).distinct().where(LogEntry.component.isnot(None))
        if source:
            query = query.where(LogEntry.source == source)
        result = await session.execute(query)
        return [row[0] for row in result.all() if row[0]]


# Global log service instance
log_service = LogService()
