"""WebSocket service for real-time training updates."""

from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Set

from fastapi import WebSocket
from loguru import logger


class WSMessageType(str, Enum):
    """WebSocket message types."""

    # Worker → Backend
    CONNECTED = "connected"
    PROGRESS_UPDATE = "progress_update"
    METRICS_UPDATE = "metrics_update"
    LOG_LINE = "log_line"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    JOB_CANCELLED = "job_cancelled"

    # Backend → Worker
    CANCEL_JOB = "cancel_job"
    PING = "ping"
    PONG = "pong"

    # Backend → Frontend
    SESSION_UPDATE = "session_update"
    WORKER_STATUS = "worker_status"


class ConnectionManager:
    """Manages WebSocket connections for workers and frontend clients."""

    def __init__(self):
        # Worker connections: job_id -> WebSocket
        self._worker_connections: Dict[str, WebSocket] = {}
        # Frontend connections: set of WebSockets subscribed to updates
        self._frontend_connections: Set[WebSocket] = set()
        # Session subscriptions: session_id -> set of frontend WebSockets
        self._session_subscriptions: Dict[str, Set[WebSocket]] = {}
        # Callbacks for session updates
        self._session_update_callbacks: List[Callable] = []

    # ============= Worker Connections =============

    async def connect_worker(self, websocket: WebSocket, job_id: str):
        """Register a worker connection for a job."""
        await websocket.accept()
        self._worker_connections[job_id] = websocket
        logger.info(f"Worker connected for job {job_id}")

    def disconnect_worker(self, job_id: str):
        """Remove a worker connection."""
        if job_id in self._worker_connections:
            del self._worker_connections[job_id]
            logger.info(f"Worker disconnected for job {job_id}")

    async def send_to_worker(self, job_id: str, message: Dict[str, Any]):
        """Send a message to a worker."""
        if job_id in self._worker_connections:
            try:
                await self._worker_connections[job_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to worker {job_id}: {e}")
                self.disconnect_worker(job_id)

    async def cancel_worker_job(self, job_id: str):
        """Send cancel request to worker."""
        await self.send_to_worker(
            job_id,
            {
                "type": WSMessageType.CANCEL_JOB.value,
                "job_id": job_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    # ============= Frontend Connections =============

    async def connect_frontend(self, websocket: WebSocket):
        """Register a frontend client connection."""
        await websocket.accept()
        self._frontend_connections.add(websocket)
        logger.info(f"Frontend client connected (total: {len(self._frontend_connections)})")

    def disconnect_frontend(self, websocket: WebSocket):
        """Remove a frontend client connection."""
        self._frontend_connections.discard(websocket)
        # Remove from all subscriptions
        for session_id in list(self._session_subscriptions.keys()):
            self._session_subscriptions[session_id].discard(websocket)
            if not self._session_subscriptions[session_id]:
                del self._session_subscriptions[session_id]
        logger.info(f"Frontend client disconnected (remaining: {len(self._frontend_connections)})")

    def subscribe_to_session(self, websocket: WebSocket, session_id: str):
        """Subscribe a frontend client to session updates."""
        if session_id not in self._session_subscriptions:
            self._session_subscriptions[session_id] = set()
        self._session_subscriptions[session_id].add(websocket)
        logger.debug(f"Frontend subscribed to session {session_id}")

    def unsubscribe_from_session(self, websocket: WebSocket, session_id: str):
        """Unsubscribe a frontend client from session updates."""
        if session_id in self._session_subscriptions:
            self._session_subscriptions[session_id].discard(websocket)

    async def broadcast_to_frontend(self, message: Dict[str, Any]):
        """Broadcast a message to all frontend clients."""
        if not self._frontend_connections:
            return

        disconnected = []
        for ws in self._frontend_connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to frontend client: {e}")
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect_frontend(ws)

    async def send_to_session_subscribers(self, session_id: str, message: Dict[str, Any]):
        """Send a message to all clients subscribed to a session."""
        if session_id not in self._session_subscriptions:
            return

        disconnected = []
        for ws in self._session_subscriptions[session_id]:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to session subscriber: {e}")
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect_frontend(ws)

    # ============= Message Handling =============

    async def handle_worker_message(self, job_id: str, message: Dict[str, Any]):
        """Handle a message from a worker."""
        msg_type = message.get("type")
        session_id = message.get("data", {}).get("session_id")

        logger.debug(f"Worker message: {msg_type} for job {job_id}")

        if msg_type == WSMessageType.PROGRESS_UPDATE.value:
            await self._handle_progress_update(session_id, message)

        elif msg_type == WSMessageType.METRICS_UPDATE.value:
            await self._handle_metrics_update(session_id, message)

        elif msg_type == WSMessageType.LOG_LINE.value:
            await self._handle_log_line(session_id, message)

        elif msg_type == WSMessageType.JOB_STARTED.value:
            await self._handle_job_started(session_id, message)

        elif msg_type == WSMessageType.JOB_COMPLETED.value:
            await self._handle_job_completed(session_id, message)

        elif msg_type == WSMessageType.JOB_FAILED.value:
            await self._handle_job_failed(session_id, message)

        elif msg_type == WSMessageType.JOB_CANCELLED.value:
            await self._handle_job_cancelled(session_id, message)

    async def _handle_progress_update(self, session_id: str, message: Dict[str, Any]):
        """Handle progress update from worker."""
        metrics = message.get("data", {}).get("metrics", {})

        # Forward to frontend subscribers
        await self.send_to_session_subscribers(
            session_id,
            {
                "type": WSMessageType.SESSION_UPDATE.value,
                "session_id": session_id,
                "update_type": "progress",
                "data": metrics,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        # Also broadcast to all frontend clients
        await self.broadcast_to_frontend(
            {
                "type": WSMessageType.SESSION_UPDATE.value,
                "session_id": session_id,
                "update_type": "progress",
                "data": metrics,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Trigger callbacks for database update
        for callback in self._session_update_callbacks:
            try:
                await callback(session_id, "progress", metrics)
            except Exception as e:
                logger.error(f"Session update callback error: {e}")

    async def _handle_metrics_update(self, session_id: str, message: Dict[str, Any]):
        """Handle metrics update from worker."""
        metrics = message.get("data", {}).get("metrics", {})

        await self.send_to_session_subscribers(
            session_id,
            {
                "type": WSMessageType.SESSION_UPDATE.value,
                "session_id": session_id,
                "update_type": "metrics",
                "data": metrics,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def _handle_log_line(self, session_id: str, message: Dict[str, Any]):
        """Handle log line from worker."""
        log = message.get("data", {}).get("log", {})

        await self.send_to_session_subscribers(
            session_id,
            {
                "type": WSMessageType.LOG_LINE.value,
                "session_id": session_id,
                "data": log,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def _handle_job_started(self, session_id: str, message: Dict[str, Any]):
        """Handle job started notification."""
        data = message.get("data", {})

        await self.broadcast_to_frontend(
            {
                "type": WSMessageType.SESSION_UPDATE.value,
                "session_id": session_id,
                "update_type": "started",
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        for callback in self._session_update_callbacks:
            try:
                await callback(session_id, "started", data)
            except Exception as e:
                logger.error(f"Session update callback error: {e}")

    async def _handle_job_completed(self, session_id: str, message: Dict[str, Any]):
        """Handle job completed notification."""
        data = message.get("data", {})

        await self.broadcast_to_frontend(
            {
                "type": WSMessageType.SESSION_UPDATE.value,
                "session_id": session_id,
                "update_type": "completed",
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        for callback in self._session_update_callbacks:
            try:
                await callback(session_id, "completed", data)
            except Exception as e:
                logger.error(f"Session update callback error: {e}")

    async def _handle_job_failed(self, session_id: str, message: Dict[str, Any]):
        """Handle job failed notification."""
        data = message.get("data", {})

        await self.broadcast_to_frontend(
            {
                "type": WSMessageType.SESSION_UPDATE.value,
                "session_id": session_id,
                "update_type": "failed",
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        for callback in self._session_update_callbacks:
            try:
                await callback(session_id, "failed", data)
            except Exception as e:
                logger.error(f"Session update callback error: {e}")

    async def _handle_job_cancelled(self, session_id: str, message: Dict[str, Any]):
        """Handle job cancelled notification."""
        data = message.get("data", {})

        await self.broadcast_to_frontend(
            {
                "type": WSMessageType.SESSION_UPDATE.value,
                "session_id": session_id,
                "update_type": "cancelled",
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        for callback in self._session_update_callbacks:
            try:
                await callback(session_id, "cancelled", data)
            except Exception as e:
                logger.error(f"Session update callback error: {e}")

    # ============= Callbacks =============

    def on_session_update(self, callback: Callable):
        """Register a callback for session updates (for database persistence)."""
        self._session_update_callbacks.append(callback)

    # ============= Stats =============

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "worker_connections": len(self._worker_connections),
            "frontend_connections": len(self._frontend_connections),
            "active_sessions": list(self._session_subscriptions.keys()),
            "active_jobs": list(self._worker_connections.keys()),
        }


# Global connection manager
connection_manager = ConnectionManager()
