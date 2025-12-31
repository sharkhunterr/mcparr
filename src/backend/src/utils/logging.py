"""Structured logging configuration."""

import json
import sys
from typing import Any, Dict, Optional

from loguru import logger


def structured_format(record: Dict[str, Any]) -> str:
    """Format log record as JSON string."""
    # Extract correlation ID if available
    correlation_id = None
    extra = record.get("extra", {})
    if isinstance(extra, dict) and "correlation_id" in extra:
        correlation_id = extra["correlation_id"]

    log_entry = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record.get("name", ""),
        "function": record.get("function", ""),
        "line": record.get("line", 0),
        "correlation_id": correlation_id,
    }

    # Add extra fields
    if extra and isinstance(extra, dict):
        for key, value in extra.items():
            if key not in ["correlation_id"]:
                log_entry[key] = value

    record["extra"]["serialized"] = json.dumps(log_entry, default=str)
    return "{extra[serialized]}\n"


def setup_logging(log_level: str = "INFO") -> None:
    """Setup structured logging configuration."""
    # Remove default logger
    logger.remove()

    # Add console logger with JSON format
    logger.add(
        sys.stdout,
        format=structured_format,
        level=log_level.upper(),
        colorize=False,
    )

    # Add file logger for persistent logs
    logger.add(
        "logs/mcparr.log",
        format=structured_format,
        level=log_level.upper(),
        rotation="100 MB",
        retention="7 days",
        compression="gz",
        colorize=False,
    )


def get_logger() -> Any:
    """Get configured logger instance."""
    return logger


def log_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    correlation_id: Optional[str] = None,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Log HTTP request."""
    logger.info(
        f"{method} {path} - {status_code} ({duration_ms:.2f}ms)",
        extra={
            "component": "http",
            "action": "request",
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "correlation_id": correlation_id,
            "user_agent": user_agent,
            "ip_address": ip_address,
        },
    )


def log_error(
    error: Exception,
    correlation_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Log error with context."""
    logger.error(
        f"Error: {str(error)}",
        extra={
            "component": "error_handler",
            "action": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "correlation_id": correlation_id,
            "context": context or {},
        },
    )


def log_service_call(
    service: str,
    action: str,
    success: bool,
    duration_ms: float,
    correlation_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Log external service call."""
    level = "info" if success else "warning"
    message = f"{service}.{action} - {'success' if success else 'failed'} ({duration_ms:.2f}ms)"

    logger.log(
        level.upper(),
        message,
        extra={
            "component": "service_adapter",
            "action": "external_call",
            "service": service,
            "service_action": action,
            "success": success,
            "duration_ms": duration_ms,
            "correlation_id": correlation_id,
            "details": details or {},
        },
    )
