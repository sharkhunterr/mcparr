"""WebSocket connection manager."""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4

from fastapi import WebSocket
from loguru import logger


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, connection_id: str = None) -> str:
        """Accept WebSocket connection and return connection ID."""
        await websocket.accept()

        # Generate connection ID if not provided
        if connection_id is None:
            connection_id = str(uuid4())

        self.active_connections[connection_id] = websocket
        self.subscriptions[connection_id] = {}

        logger.info(
            f"WebSocket connection established: {connection_id}",
            extra={
                "component": "websocket",
                "action": "connect",
                "connection_id": connection_id,
            }
        )

        return connection_id

    async def disconnect(self, connection_id: str):
        """Remove WebSocket connection."""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            del self.subscriptions[connection_id]

            logger.info(
                f"WebSocket connection closed: {connection_id}",
                extra={
                    "component": "websocket",
                    "action": "disconnect",
                    "connection_id": connection_id,
                }
            )

    async def send_message(
        self,
        connection_id: str,
        message: Dict[str, Any]
    ) -> bool:
        """Send message to specific connection."""
        if connection_id not in self.active_connections:
            return False

        websocket = self.active_connections[connection_id]

        try:
            # Add timestamp to message
            message["timestamp"] = datetime.utcnow().isoformat()

            await websocket.send_text(json.dumps(message, default=str))
            return True
        except Exception as e:
            logger.error(
                f"Failed to send message to {connection_id}: {str(e)}",
                extra={
                    "component": "websocket",
                    "action": "send_message",
                    "connection_id": connection_id,
                    "error": str(e),
                }
            )
            # Remove broken connection
            await self.disconnect(connection_id)
            return False

    async def broadcast(self, message: Dict[str, Any], channel: str = None):
        """Broadcast message to all or filtered connections."""
        message["timestamp"] = datetime.utcnow().isoformat()

        connections_to_remove = []

        for connection_id, websocket in self.active_connections.items():
            # Check if connection is subscribed to channel
            if channel and not self._is_subscribed(connection_id, channel):
                continue

            try:
                await websocket.send_text(json.dumps(message, default=str))
            except Exception as e:
                logger.error(
                    f"Failed to broadcast to {connection_id}: {str(e)}",
                    extra={
                        "component": "websocket",
                        "action": "broadcast",
                        "connection_id": connection_id,
                        "channel": channel,
                        "error": str(e),
                    }
                )
                connections_to_remove.append(connection_id)

        # Clean up broken connections
        for connection_id in connections_to_remove:
            await self.disconnect(connection_id)

    def subscribe(
        self,
        connection_id: str,
        channel: str,
        filters: Dict[str, Any] = None
    ):
        """Subscribe connection to a channel with optional filters."""
        if connection_id not in self.subscriptions:
            self.subscriptions[connection_id] = {}

        self.subscriptions[connection_id][channel] = {
            "filters": filters or {},
            "subscribed_at": datetime.utcnow(),
        }

        logger.info(
            f"Connection {connection_id} subscribed to {channel}",
            extra={
                "component": "websocket",
                "action": "subscribe",
                "connection_id": connection_id,
                "channel": channel,
                "filters": filters,
            }
        )

    def unsubscribe(self, connection_id: str, channel: str):
        """Unsubscribe connection from channel."""
        if (connection_id in self.subscriptions and
                channel in self.subscriptions[connection_id]):
            del self.subscriptions[connection_id][channel]

            logger.info(
                f"Connection {connection_id} unsubscribed from {channel}",
                extra={
                    "component": "websocket",
                    "action": "unsubscribe",
                    "connection_id": connection_id,
                    "channel": channel,
                }
            )

    def _is_subscribed(self, connection_id: str, channel: str) -> bool:
        """Check if connection is subscribed to channel."""
        return (connection_id in self.subscriptions and
                channel in self.subscriptions[connection_id])

    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)

    def get_subscriptions(self, connection_id: str) -> Dict[str, Any]:
        """Get subscriptions for a connection."""
        return self.subscriptions.get(connection_id, {})


# Global connection manager instance
connection_manager = ConnectionManager()