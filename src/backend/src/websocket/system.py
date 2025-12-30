"""System metrics WebSocket endpoints."""

import asyncio
import json
from typing import Dict, Any

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from src.websocket.manager import connection_manager
from src.services.system_monitor import SystemMonitorService


class SystemWebSocketHandler:
    """WebSocket handler for system metrics streaming."""

    def __init__(self):
        self.system_monitor = SystemMonitorService()
        self.active_subscriptions: Dict[str, Dict[str, Any]] = {}

    async def handle_connection(self, websocket: WebSocket):
        """Handle WebSocket connection for system metrics."""
        connection_id = await connection_manager.connect(websocket)

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)

                await self.handle_message(connection_id, message)

        except WebSocketDisconnect:
            logger.info(f"System WebSocket disconnected: {connection_id}")
        except Exception as e:
            logger.error(f"System WebSocket error: {e}")
        finally:
            await connection_manager.disconnect(connection_id)
            if connection_id in self.active_subscriptions:
                del self.active_subscriptions[connection_id]

    async def handle_message(self, connection_id: str, message: Dict[str, Any]):
        """Handle incoming WebSocket message."""
        message_type = message.get("type")

        if message_type == "metrics_subscribe":
            await self.handle_metrics_subscribe(connection_id, message)
        elif message_type == "metrics_unsubscribe":
            await self.handle_metrics_unsubscribe(connection_id)
        else:
            logger.warning(f"Unknown message type: {message_type}")

    async def handle_metrics_subscribe(self, connection_id: str, message: Dict[str, Any]):
        """Handle metrics subscription request."""
        metrics_types = message.get("metrics", ["system"])
        interval_seconds = message.get("interval_seconds", 5)

        # Validate interval
        if interval_seconds < 1 or interval_seconds > 60:
            interval_seconds = 5

        subscription = {
            "metrics_types": metrics_types,
            "interval_seconds": interval_seconds,
            "task": None
        }

        # Cancel existing subscription if any
        if connection_id in self.active_subscriptions:
            existing_task = self.active_subscriptions[connection_id].get("task")
            if existing_task:
                existing_task.cancel()

        # Start metrics streaming task
        task = asyncio.create_task(
            self.stream_metrics(connection_id, subscription)
        )
        subscription["task"] = task

        self.active_subscriptions[connection_id] = subscription

        # Send confirmation
        await connection_manager.send_message(connection_id, {
            "type": "metrics_subscribed",
            "metrics_types": metrics_types,
            "interval_seconds": interval_seconds
        })

        logger.info(
            f"Metrics subscription started for {connection_id}",
            extra={
                "component": "websocket",
                "action": "metrics_subscribe",
                "connection_id": connection_id,
                "metrics_types": metrics_types,
                "interval": interval_seconds
            }
        )

    async def handle_metrics_unsubscribe(self, connection_id: str):
        """Handle metrics unsubscription request."""
        if connection_id in self.active_subscriptions:
            subscription = self.active_subscriptions[connection_id]
            task = subscription.get("task")
            if task:
                task.cancel()

            del self.active_subscriptions[connection_id]

            await connection_manager.send_message(connection_id, {
                "type": "metrics_unsubscribed"
            })

            logger.info(
                f"Metrics subscription stopped for {connection_id}",
                extra={
                    "component": "websocket",
                    "action": "metrics_unsubscribe",
                    "connection_id": connection_id
                }
            )

    async def stream_metrics(self, connection_id: str, subscription: Dict[str, Any]):
        """Stream metrics to WebSocket connection."""
        interval_seconds = subscription["interval_seconds"]
        metrics_types = subscription["metrics_types"]

        try:
            while True:
                # Collect metrics data
                metrics_data = {}

                if "system" in metrics_types:
                    system_status = await self.system_monitor.get_current_system_status()
                    metrics_data["system"] = {
                        "cpu_percent": system_status.get("cpu_percent", 0),
                        "memory_used_mb": system_status.get("memory_used_mb", 0),
                        "memory_total_mb": system_status.get("memory_total_mb", 0),
                        "memory_percent": system_status.get("memory_percent", 0),
                        "disk_used_gb": system_status.get("disk_used_gb", 0),
                        "disk_total_gb": system_status.get("disk_total_gb", 0),
                        "disk_percent": system_status.get("disk_percent", 0),
                        "network_sent_mb": system_status.get("network_sent_mb", 0),
                        "network_recv_mb": system_status.get("network_recv_mb", 0),
                        "load_average": [0.1, 0.2, 0.15]  # Mock data
                    }

                if "docker" in metrics_types:
                    docker_status = await self.system_monitor.get_docker_status()
                    metrics_data["docker"] = {
                        "containers_running": docker_status.get("containers_running", 0),
                        "containers_stopped": docker_status.get("containers_stopped", 0),
                        "containers_paused": docker_status.get("containers_paused", 0),
                        "images_count": docker_status.get("images_count", 0),
                        "volumes_count": docker_status.get("volumes_count", 0)
                    }

                if "services" in metrics_types:
                    # Mock services data (would be real when services are implemented)
                    metrics_data["services"] = [
                        {
                            "service_id": "mock-service-1",
                            "name": "Mock Service",
                            "status": "online",
                            "response_time_ms": 45.2,
                            "last_check": system_status.get("timestamp")
                        }
                    ]

                # Send metrics update
                message = {
                    "type": "metrics_update",
                    **metrics_data
                }

                success = await connection_manager.send_message(connection_id, message)
                if not success:
                    break

                # Wait for next interval
                await asyncio.sleep(interval_seconds)

        except asyncio.CancelledError:
            logger.info(f"Metrics streaming cancelled for {connection_id}")
        except Exception as e:
            logger.error(f"Error streaming metrics for {connection_id}: {e}")


# Global handler instance
system_ws_handler = SystemWebSocketHandler()


async def handle_system_websocket(websocket: WebSocket):
    """WebSocket endpoint for system metrics."""
    await system_ws_handler.handle_connection(websocket)