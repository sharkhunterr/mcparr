"""WebSocket endpoint for real-time log streaming."""

import asyncio
import json
from datetime import datetime
from typing import Set, Optional, Dict, Any

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from src.models.log_entry import LogEntry


class LogStreamManager:
    """Manager for WebSocket connections streaming logs."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.connection_filters: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, filters: Optional[Dict[str, Any]] = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.connection_filters[websocket] = filters or {}
        logger.info(f"Log WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        self.connection_filters.pop(websocket, None)
        logger.info(f"Log WebSocket disconnected. Total connections: {len(self.active_connections)}")

    def update_filters(self, websocket: WebSocket, filters: Dict[str, Any]):
        """Update filters for a connection."""
        if websocket in self.active_connections:
            self.connection_filters[websocket] = filters

    def _matches_filter(self, log_data: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if a log entry matches the connection's filters."""
        if not filters:
            return True

        # Filter by level
        if 'level' in filters and filters['level']:
            if log_data.get('level') != filters['level']:
                return False

        # Filter by source
        if 'source' in filters and filters['source']:
            if log_data.get('source') != filters['source']:
                return False

        # Filter by service_id
        if 'service_id' in filters and filters['service_id']:
            if log_data.get('service_id') != filters['service_id']:
                return False

        # Filter by minimum level severity
        if 'min_level' in filters and filters['min_level']:
            level_order = ['debug', 'info', 'warning', 'error', 'critical']
            log_level = log_data.get('level', 'info').lower()
            min_level = filters['min_level'].lower()
            if log_level in level_order and min_level in level_order:
                if level_order.index(log_level) < level_order.index(min_level):
                    return False

        return True

    async def broadcast_log(self, log_entry: LogEntry):
        """Broadcast a new log entry to all connected clients."""
        if not self.active_connections:
            return

        log_data = log_entry.to_dict()
        message = {
            "type": "log",
            "data": log_data,
            "timestamp": datetime.utcnow().isoformat()
        }

        disconnected = set()

        for websocket in self.active_connections:
            # Check if log matches this connection's filters
            filters = self.connection_filters.get(websocket, {})
            if not self._matches_filter(log_data, filters):
                continue

            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send log to WebSocket: {e}")
                disconnected.add(websocket)

        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws)

    async def broadcast_log_dict(self, log_data: Dict[str, Any]):
        """Broadcast a log entry from a dictionary."""
        if not self.active_connections:
            return

        message = {
            "type": "log",
            "data": log_data,
            "timestamp": datetime.utcnow().isoformat()
        }

        disconnected = set()

        for websocket in self.active_connections:
            filters = self.connection_filters.get(websocket, {})
            if not self._matches_filter(log_data, filters):
                continue

            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send log to WebSocket: {e}")
                disconnected.add(websocket)

        for ws in disconnected:
            self.disconnect(ws)


# Global instance
log_stream_manager = LogStreamManager()


async def websocket_logs_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time log streaming."""
    # Parse query params for initial filters
    params = dict(websocket.query_params)
    filters = {
        'level': params.get('level'),
        'source': params.get('source'),
        'service_id': params.get('service_id'),
        'min_level': params.get('min_level'),
    }

    await log_stream_manager.connect(websocket, filters)

    try:
        # Send initial connection success message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to log stream",
            "filters": {k: v for k, v in filters.items() if v is not None}
        })

        # Listen for filter updates from client
        while True:
            try:
                data = await websocket.receive_json()

                if data.get('type') == 'update_filters':
                    new_filters = data.get('filters', {})
                    log_stream_manager.update_filters(websocket, new_filters)
                    await websocket.send_json({
                        "type": "filters_updated",
                        "filters": new_filters
                    })

                elif data.get('type') == 'ping':
                    await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })

    except WebSocketDisconnect:
        pass
    finally:
        log_stream_manager.disconnect(websocket)
