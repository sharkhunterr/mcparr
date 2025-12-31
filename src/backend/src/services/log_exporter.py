"""Log export service for exporting logs in various formats."""

import csv
import io
import json
from datetime import datetime
from typing import List, Literal, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.log_entry import LogEntry
from src.services.log_service import log_service

ExportFormat = Literal["json", "csv", "text"]


class LogExporter:
    """Service for exporting logs in various formats."""

    async def export_logs(
        self,
        session: AsyncSession,
        format: ExportFormat = "json",
        level: Optional[str] = None,
        source: Optional[str] = None,
        service_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        search: Optional[str] = None,
        limit: int = 10000,
    ) -> tuple[str, str]:
        """
        Export logs in the specified format.

        Returns:
            tuple: (content, content_type) - The exported content and its MIME type
        """
        # Fetch logs with filters
        logs, _ = await log_service.get_logs(
            session,
            level=level,
            source=source,
            service_id=service_id,
            correlation_id=correlation_id,
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            search=search,
            skip=0,
            limit=limit,
        )

        if format == "json":
            return self._export_json(logs), "application/json"
        elif format == "csv":
            return self._export_csv(logs), "text/csv"
        elif format == "text":
            return self._export_text(logs), "text/plain"
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_json(self, logs: List[LogEntry]) -> str:
        """Export logs as JSON."""
        data = {
            "exported_at": datetime.utcnow().isoformat(),
            "total_logs": len(logs),
            "logs": [log.to_dict() for log in logs],
        }
        return json.dumps(data, indent=2, default=str)

    def _export_csv(self, logs: List[LogEntry]) -> str:
        """Export logs as CSV."""
        output = io.StringIO()

        fieldnames = [
            "id",
            "logged_at",
            "level",
            "source",
            "component",
            "message",
            "correlation_id",
            "request_id",
            "user_id",
            "service_id",
            "service_type",
            "exception_type",
            "exception_message",
            "duration_ms",
            "created_at",
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for log in logs:
            row = log.to_dict()
            # Flatten extra_data and stack_trace for CSV
            row.pop("extra_data", None)
            row.pop("stack_trace", None)
            writer.writerow(row)

        return output.getvalue()

    def _export_text(self, logs: List[LogEntry]) -> str:
        """Export logs as plain text (similar to traditional log files)."""
        lines = []
        lines.append(f"# Log Export - {datetime.utcnow().isoformat()}")
        lines.append(f"# Total logs: {len(logs)}")
        lines.append("")

        for log in logs:
            timestamp = log.logged_at.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            level = log.level.upper().ljust(8)
            source = f"{log.source}"
            if log.component:
                source += f"/{log.component}"
            source = source.ljust(30)

            line = f"[{timestamp}] {level} {source} {log.message}"

            if log.correlation_id:
                line += f" [cid:{log.correlation_id[:8]}]"

            if log.duration_ms:
                line += f" ({log.duration_ms}ms)"

            lines.append(line)

            # Add exception info if present
            if log.exception_type:
                lines.append(f"    Exception: {log.exception_type}: {log.exception_message}")
                if log.stack_trace:
                    for trace_line in log.stack_trace.split("\n"):
                        lines.append(f"    {trace_line}")

        return "\n".join(lines)

    def get_filename(self, format: ExportFormat) -> str:
        """Generate a filename for the export."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        extensions = {"json": "json", "csv": "csv", "text": "log"}
        return f"mcparr_logs_{timestamp}.{extensions[format]}"


# Global instance
log_exporter = LogExporter()
