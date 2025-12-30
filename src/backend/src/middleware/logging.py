"""Logging middleware for HTTP requests."""

import asyncio
import time
from datetime import datetime
from typing import Callable, Optional
from collections import deque

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.logging import log_request, setup_logging


# Queue for async log persistence
_log_queue: deque = deque(maxlen=1000)
_db_log_task: Optional[asyncio.Task] = None


async def _persist_logs_to_db():
    """Background task to persist logs to database."""
    from src.database.connection import database_manager
    from src.models.log_entry import LogEntry

    while True:
        try:
            if _log_queue and database_manager:
                logs_to_save = []
                while _log_queue:
                    try:
                        logs_to_save.append(_log_queue.popleft())
                    except IndexError:
                        break

                if logs_to_save:
                    async with database_manager.session_factory() as session:
                        for log_data in logs_to_save:
                            log_entry = LogEntry(
                                level=log_data.get("level", "info"),
                                message=log_data.get("message", ""),
                                source=log_data.get("source", "backend"),
                                component=log_data.get("component"),
                                correlation_id=log_data.get("correlation_id"),
                                request_id=log_data.get("request_id"),
                                extra_data=log_data.get("extra_data", {}),
                                duration_ms=log_data.get("duration_ms"),
                                logged_at=log_data.get("logged_at", datetime.utcnow()),
                            )
                            session.add(log_entry)
                        await session.commit()
        except Exception as e:
            # Don't crash the background task on errors
            print(f"Error persisting logs: {e}")

        await asyncio.sleep(1)  # Batch logs every second


def start_log_persistence():
    """Start the background log persistence task."""
    global _db_log_task
    if _db_log_task is None or _db_log_task.done():
        _db_log_task = asyncio.create_task(_persist_logs_to_db())


def queue_log_entry(
    level: str,
    message: str,
    source: str = "backend",
    component: Optional[str] = None,
    correlation_id: Optional[str] = None,
    request_id: Optional[str] = None,
    extra_data: Optional[dict] = None,
    duration_ms: Optional[float] = None,
):
    """Queue a log entry for database persistence."""
    _log_queue.append({
        "level": level,
        "message": message,
        "source": source,
        "component": component,
        "correlation_id": correlation_id,
        "request_id": request_id,
        "extra_data": extra_data or {},
        "duration_ms": int(duration_ms) if duration_ms else None,
        "logged_at": datetime.utcnow(),
    })


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests and responses."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response]
    ) -> Response:
        """Log request and response details."""
        # Start log persistence task if not running
        start_log_persistence()

        start_time = time.time()

        # Get request details
        method = request.method
        path = request.url.path
        correlation_id = getattr(request.state, "correlation_id", None)
        user_agent = request.headers.get("user-agent")
        ip_address = self._get_client_ip(request)

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log request to console/file
        log_request(
            method=method,
            path=path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        # Skip logging for static assets and health checks to reduce noise
        skip_paths = ["/health", "/favicon.ico", "/static", "/ws"]
        should_log = not any(path.startswith(p) for p in skip_paths)

        if should_log:
            # Determine log level based on status code
            if response.status_code >= 500:
                level = "error"
            elif response.status_code >= 400:
                level = "warning"
            else:
                level = "info"

            # Queue log for database persistence
            queue_log_entry(
                level=level,
                message=f"{method} {path} - {response.status_code}",
                source="backend",
                component="http",
                correlation_id=correlation_id,
                extra_data={
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "user_agent": user_agent,
                    "ip_address": ip_address,
                },
                duration_ms=duration_ms,
            )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check X-Forwarded-For header (proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Check X-Real-IP header (nginx proxy)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to client host
        if hasattr(request, "client") and request.client:
            return request.client.host

        return "unknown"
