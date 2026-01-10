"""MCP request auditing and analytics service."""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import McpRequest, McpRequestStatus


class McpAuditService:
    """Service for MCP request auditing and analytics."""

    async def get_requests(
        self,
        session: AsyncSession,
        tool_name: Optional[str] = None,
        category: Optional[str] = None,
        service: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[McpRequest], int]:
        """Get MCP requests with filtering and pagination."""
        query = select(McpRequest)
        count_query = select(func.count(McpRequest.id))

        conditions = []

        if tool_name:
            conditions.append(McpRequest.tool_name == tool_name)
        if category:
            conditions.append(McpRequest.tool_category == category)
        if service:
            # Filter by tool name prefix (e.g., "plex" matches "plex_search_media")
            conditions.append(McpRequest.tool_name.like(f"{service}_%"))
        if status:
            conditions.append(McpRequest.status == status)
        if start_time:
            conditions.append(McpRequest.created_at >= start_time)
        if end_time:
            conditions.append(McpRequest.created_at <= end_time)
        if user_id:
            conditions.append(McpRequest.user_id == user_id)

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # Get total count
        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        # Get paginated results
        query = query.order_by(McpRequest.created_at.desc()).offset(skip).limit(limit)
        result = await session.execute(query)
        requests = list(result.scalars().all())

        return requests, total

    async def get_request_by_id(
        self,
        session: AsyncSession,
        request_id: str,
    ) -> Optional[McpRequest]:
        """Get a specific MCP request by ID."""
        result = await session.execute(select(McpRequest).where(McpRequest.id == request_id))
        return result.scalar_one_or_none()

    async def _get_period_stats(
        self,
        session: AsyncSession,
        start_time: datetime,
        end_time: datetime,
    ) -> dict:
        """Get statistics for a specific time period."""
        # Total requests
        total_result = await session.execute(
            select(func.count(McpRequest.id)).where(
                and_(McpRequest.created_at >= start_time, McpRequest.created_at < end_time)
            )
        )
        total = total_result.scalar() or 0

        # By status
        status_result = await session.execute(
            select(McpRequest.status, func.count(McpRequest.id))
            .where(and_(McpRequest.created_at >= start_time, McpRequest.created_at < end_time))
            .group_by(McpRequest.status)
        )
        by_status = {row[0]: row[1] for row in status_result.fetchall()}

        # By category
        category_result = await session.execute(
            select(McpRequest.tool_category, func.count(McpRequest.id))
            .where(and_(McpRequest.created_at >= start_time, McpRequest.created_at < end_time))
            .group_by(McpRequest.tool_category)
        )
        by_category = {row[0]: row[1] for row in category_result.fetchall()}

        # By tool
        tool_result = await session.execute(
            select(McpRequest.tool_name, func.count(McpRequest.id))
            .where(and_(McpRequest.created_at >= start_time, McpRequest.created_at < end_time))
            .group_by(McpRequest.tool_name)
            .order_by(func.count(McpRequest.id).desc())
            .limit(10)
        )
        top_tools = {row[0]: row[1] for row in tool_result.fetchall()}

        # Average duration
        avg_duration_result = await session.execute(
            select(func.avg(McpRequest.duration_ms)).where(
                and_(
                    McpRequest.created_at >= start_time,
                    McpRequest.created_at < end_time,
                    McpRequest.duration_ms.isnot(None),
                )
            )
        )
        avg_duration = avg_duration_result.scalar() or 0

        # Success rate
        completed = by_status.get(McpRequestStatus.COMPLETED.value, 0) + by_status.get("completed", 0)
        failed = by_status.get(McpRequestStatus.FAILED.value, 0) + by_status.get("failed", 0)
        success_rate = (completed / (completed + failed) * 100) if (completed + failed) > 0 else 100

        return {
            "total": total,
            "by_status": by_status,
            "by_category": by_category,
            "top_tools": top_tools,
            "average_duration_ms": round(avg_duration, 2),
            "success_rate": round(success_rate, 2),
            "completed": completed,
            "failed": failed,
        }

    async def get_stats(
        self,
        session: AsyncSession,
        hours: int = 24,
    ) -> dict:
        """Get MCP request statistics for the specified time period."""
        now = datetime.utcnow()
        since = now - timedelta(hours=hours)

        stats = await self._get_period_stats(session, since, now)
        stats["period_hours"] = hours

        return stats

    async def get_stats_with_comparison(
        self,
        session: AsyncSession,
        hours: int = 24,
    ) -> dict:
        """Get MCP request statistics with comparison to previous period."""
        now = datetime.utcnow()
        current_start = now - timedelta(hours=hours)
        previous_start = current_start - timedelta(hours=hours)

        # Get current period stats
        current = await self._get_period_stats(session, current_start, now)

        # Get previous period stats
        previous = await self._get_period_stats(session, previous_start, current_start)

        # Calculate changes
        def calc_change(current_val: float, previous_val: float) -> Optional[float]:
            if previous_val == 0:
                return None if current_val == 0 else 100.0
            return round(((current_val - previous_val) / previous_val) * 100, 1)

        return {
            "total": current["total"],
            "by_status": current["by_status"],
            "by_category": current["by_category"],
            "top_tools": current["top_tools"],
            "average_duration_ms": current["average_duration_ms"],
            "success_rate": current["success_rate"],
            "period_hours": hours,
            "comparison": {
                "total": previous["total"],
                "total_change": calc_change(current["total"], previous["total"]),
                "average_duration_ms": previous["average_duration_ms"],
                "duration_change": calc_change(current["average_duration_ms"], previous["average_duration_ms"]),
                "success_rate": previous["success_rate"],
                "success_rate_change": round(current["success_rate"] - previous["success_rate"], 1)
                if previous["total"] > 0
                else None,
                "completed": previous.get("completed", 0),
                "completed_change": calc_change(current.get("completed", 0), previous.get("completed", 0)),
                "failed": previous.get("failed", 0),
                "failed_change": calc_change(current.get("failed", 0), previous.get("failed", 0)),
            },
        }

    async def get_tool_usage(
        self,
        session: AsyncSession,
        hours: int = 24,
    ) -> List[dict]:
        """Get tool usage statistics."""
        since = datetime.utcnow() - timedelta(hours=hours)

        result = await session.execute(
            select(
                McpRequest.tool_name,
                McpRequest.tool_category,
                func.count(McpRequest.id).label("count"),
                func.avg(McpRequest.duration_ms).label("avg_duration"),
                func.sum(case((McpRequest.status == McpRequestStatus.COMPLETED, 1), else_=0)).label("success_count"),
            )
            .where(McpRequest.created_at >= since)
            .group_by(McpRequest.tool_name, McpRequest.tool_category)
            .order_by(func.count(McpRequest.id).desc())
        )

        return [
            {
                "tool_name": row.tool_name,
                "category": row.tool_category,
                "usage_count": row.count,
                "avg_duration_ms": round(row.avg_duration or 0, 2),
                "success_rate": round((row.success_count / row.count) * 100, 2) if row.count > 0 else 0,
            }
            for row in result.fetchall()
        ]

    async def get_hourly_usage(
        self,
        session: AsyncSession,
        hours: int = 24,
    ) -> List[dict]:
        """Get hourly usage statistics with success/failure breakdown."""
        since = datetime.utcnow() - timedelta(hours=hours)

        # SQLite doesn't have date_trunc, use strftime instead
        result = await session.execute(
            select(
                func.strftime("%Y-%m-%d %H:00:00", McpRequest.created_at).label("hour"),
                func.count(McpRequest.id).label("count"),
                func.sum(case((McpRequest.status == McpRequestStatus.COMPLETED, 1), else_=0)).label("success_count"),
                func.sum(case((McpRequest.status == McpRequestStatus.FAILED, 1), else_=0)).label("failed_count"),
            )
            .where(McpRequest.created_at >= since)
            .group_by(func.strftime("%Y-%m-%d %H:00:00", McpRequest.created_at))
            .order_by(func.strftime("%Y-%m-%d %H:00:00", McpRequest.created_at))
        )

        return [
            {
                "hour": row.hour,
                "count": row.count,
                "success_count": row.success_count or 0,
                "failed_count": row.failed_count or 0,
            }
            for row in result.fetchall()
        ]

    async def cleanup_old_requests(
        self,
        session: AsyncSession,
        retention_days: int = 30,
    ) -> int:
        """Delete MCP requests older than retention period."""
        from sqlalchemy import delete

        cutoff = datetime.utcnow() - timedelta(days=retention_days)

        result = await session.execute(delete(McpRequest).where(McpRequest.created_at < cutoff))
        await session.commit()

        return result.rowcount

    async def get_user_stats(
        self,
        session: AsyncSession,
        hours: int = 24,
    ) -> List[dict]:
        """Get usage statistics per user."""
        since = datetime.utcnow() - timedelta(hours=hours)

        result = await session.execute(
            select(
                McpRequest.user_id,
                func.count(McpRequest.id).label("count"),
                func.avg(McpRequest.duration_ms).label("avg_duration"),
                func.sum(case((McpRequest.status == McpRequestStatus.COMPLETED, 1), else_=0)).label("success_count"),
                func.sum(case((McpRequest.status == McpRequestStatus.FAILED, 1), else_=0)).label("failed_count"),
            )
            .where(and_(McpRequest.created_at >= since, McpRequest.user_id.isnot(None)))
            .group_by(McpRequest.user_id)
            .order_by(func.count(McpRequest.id).desc())
        )

        return [
            {
                "user_id": row.user_id,
                "request_count": row.count,
                "avg_duration_ms": round(row.avg_duration or 0, 2),
                "success_count": row.success_count or 0,
                "failed_count": row.failed_count or 0,
                "success_rate": round((row.success_count / row.count) * 100, 2) if row.count > 0 else 0,
            }
            for row in result.fetchall()
        ]

    async def get_user_service_stats(
        self,
        session: AsyncSession,
        hours: int = 24,
    ) -> List[dict]:
        """Get usage statistics per user and service (extracted from tool name prefix)."""
        since = datetime.utcnow() - timedelta(hours=hours)

        # Extract service name from tool_name (prefix before first underscore)
        # e.g., "plex_search_media" -> "plex", "radarr_get_queue" -> "radarr"
        service_expr = func.substr(McpRequest.tool_name, 1, func.instr(McpRequest.tool_name, "_") - 1).label("service")

        result = await session.execute(
            select(
                McpRequest.user_id,
                service_expr,
                func.count(McpRequest.id).label("count"),
                func.sum(case((McpRequest.status == McpRequestStatus.COMPLETED, 1), else_=0)).label("success_count"),
            )
            .where(
                and_(
                    McpRequest.created_at >= since,
                    McpRequest.user_id.isnot(None),
                    McpRequest.tool_name.contains("_"),  # Only tools with underscore
                )
            )
            .group_by(McpRequest.user_id, service_expr)
            .order_by(func.count(McpRequest.id).desc())
        )

        return [
            {
                "user_id": row.user_id,
                "service": row.service,
                "request_count": row.count,
                "success_count": row.success_count or 0,
                "success_rate": round((row.success_count / row.count) * 100, 2) if row.count > 0 else 0,
            }
            for row in result.fetchall()
        ]

    async def get_hourly_usage_by_user(
        self,
        session: AsyncSession,
        hours: int = 24,
    ) -> List[dict]:
        """Get hourly usage statistics broken down by user."""
        since = datetime.utcnow() - timedelta(hours=hours)

        result = await session.execute(
            select(
                func.strftime("%Y-%m-%d %H:00:00", McpRequest.created_at).label("hour"),
                McpRequest.user_id,
                func.count(McpRequest.id).label("count"),
            )
            .where(and_(McpRequest.created_at >= since, McpRequest.user_id.isnot(None)))
            .group_by(func.strftime("%Y-%m-%d %H:00:00", McpRequest.created_at), McpRequest.user_id)
            .order_by(func.strftime("%Y-%m-%d %H:00:00", McpRequest.created_at))
        )

        return [
            {
                "hour": row.hour,
                "user_id": row.user_id,
                "count": row.count,
            }
            for row in result.fetchall()
        ]


# Singleton instance
mcp_audit_service = McpAuditService()
