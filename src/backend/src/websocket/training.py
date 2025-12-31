"""Training progress WebSocket endpoints."""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from src.services.ollama_service import OllamaMetricsCollector, OllamaService
from src.websocket.manager import connection_manager


class TrainingWebSocketHandler:
    """WebSocket handler for training progress streaming."""

    def __init__(self):
        self.active_subscriptions: Dict[str, Dict[str, Any]] = {}
        self._ollama_service: Optional[OllamaService] = None
        self._metrics_collector: Optional[OllamaMetricsCollector] = None

    def set_ollama_service(self, service: OllamaService):
        """Set the Ollama service instance."""
        self._ollama_service = service
        self._metrics_collector = OllamaMetricsCollector(service)

    async def handle_connection(self, websocket: WebSocket):
        """Handle WebSocket connection for training progress."""
        connection_id = await connection_manager.connect(websocket)

        try:
            # Send initial connection confirmation
            await connection_manager.send_message(
                connection_id, {"type": "connected", "message": "Connected to training WebSocket"}
            )

            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)

                await self.handle_message(connection_id, message)

        except WebSocketDisconnect:
            logger.info(f"Training WebSocket disconnected: {connection_id}")
        except Exception as e:
            logger.error(f"Training WebSocket error: {e}")
        finally:
            await self._cleanup_connection(connection_id)

    async def _cleanup_connection(self, connection_id: str):
        """Clean up connection resources."""
        await connection_manager.disconnect(connection_id)
        if connection_id in self.active_subscriptions:
            subscription = self.active_subscriptions[connection_id]
            task = subscription.get("task")
            if task:
                task.cancel()
            del self.active_subscriptions[connection_id]

    async def handle_message(self, connection_id: str, message: Dict[str, Any]):
        """Handle incoming WebSocket message."""
        message_type = message.get("type")

        handlers = {
            "subscribe_training": self.handle_training_subscribe,
            "unsubscribe_training": self.handle_training_unsubscribe,
            "subscribe_session": self.handle_session_subscribe,
            "unsubscribe_session": self.handle_session_unsubscribe,
            "subscribe_ollama_metrics": self.handle_ollama_metrics_subscribe,
            "unsubscribe_ollama_metrics": self.handle_ollama_metrics_unsubscribe,
            "ping": self.handle_ping,
        }

        handler = handlers.get(message_type)
        if handler:
            await handler(connection_id, message)
        else:
            logger.warning(f"Unknown training message type: {message_type}")
            await connection_manager.send_message(
                connection_id, {"type": "error", "message": f"Unknown message type: {message_type}"}
            )

    async def handle_ping(self, connection_id: str, message: Dict[str, Any]):
        """Handle ping message."""
        await connection_manager.send_message(
            connection_id, {"type": "pong", "timestamp": datetime.utcnow().isoformat()}
        )

    async def handle_training_subscribe(self, connection_id: str, message: Dict[str, Any]):
        """Subscribe to general training updates."""
        interval_seconds = message.get("interval_seconds", 5)

        # Validate interval
        if interval_seconds < 1 or interval_seconds > 60:
            interval_seconds = 5

        # Cancel existing subscription if any
        await self._cancel_subscription(connection_id, "training")

        subscription = {"type": "training", "interval_seconds": interval_seconds, "task": None}

        # Start training updates streaming task
        task = asyncio.create_task(self.stream_training_updates(connection_id, subscription))
        subscription["task"] = task

        self.active_subscriptions[connection_id] = subscription

        # Send confirmation
        await connection_manager.send_message(
            connection_id, {"type": "training_subscribed", "interval_seconds": interval_seconds}
        )

        logger.info(
            f"Training subscription started for {connection_id}",
            extra={
                "component": "websocket",
                "action": "training_subscribe",
                "connection_id": connection_id,
                "interval": interval_seconds,
            },
        )

    async def handle_training_unsubscribe(self, connection_id: str, message: Dict[str, Any]):
        """Unsubscribe from training updates."""
        await self._cancel_subscription(connection_id, "training")

        await connection_manager.send_message(connection_id, {"type": "training_unsubscribed"})

        logger.info(
            f"Training subscription stopped for {connection_id}",
            extra={"component": "websocket", "action": "training_unsubscribe", "connection_id": connection_id},
        )

    async def handle_session_subscribe(self, connection_id: str, message: Dict[str, Any]):
        """Subscribe to specific training session updates."""
        session_id = message.get("session_id")
        if not session_id:
            await connection_manager.send_message(connection_id, {"type": "error", "message": "session_id is required"})
            return

        interval_seconds = message.get("interval_seconds", 2)

        # Validate interval
        if interval_seconds < 1 or interval_seconds > 30:
            interval_seconds = 2

        # Cancel existing subscription if any
        await self._cancel_subscription(connection_id, "session")

        subscription = {"type": "session", "session_id": session_id, "interval_seconds": interval_seconds, "task": None}

        # Start session progress streaming task
        task = asyncio.create_task(self.stream_session_progress(connection_id, subscription))
        subscription["task"] = task

        self.active_subscriptions[connection_id] = subscription

        # Send confirmation
        await connection_manager.send_message(
            connection_id,
            {"type": "session_subscribed", "session_id": session_id, "interval_seconds": interval_seconds},
        )

        logger.info(
            f"Session subscription started for {connection_id}",
            extra={
                "component": "websocket",
                "action": "session_subscribe",
                "connection_id": connection_id,
                "session_id": session_id,
                "interval": interval_seconds,
            },
        )

    async def handle_session_unsubscribe(self, connection_id: str, message: Dict[str, Any]):
        """Unsubscribe from session updates."""
        await self._cancel_subscription(connection_id, "session")

        await connection_manager.send_message(connection_id, {"type": "session_unsubscribed"})

        logger.info(
            f"Session subscription stopped for {connection_id}",
            extra={"component": "websocket", "action": "session_unsubscribe", "connection_id": connection_id},
        )

    async def handle_ollama_metrics_subscribe(self, connection_id: str, message: Dict[str, Any]):
        """Subscribe to Ollama metrics updates."""
        interval_seconds = message.get("interval_seconds", 10)
        ollama_url = message.get("ollama_url")

        # Validate interval
        if interval_seconds < 5 or interval_seconds > 120:
            interval_seconds = 10

        # Cancel existing subscription if any
        await self._cancel_subscription(connection_id, "ollama_metrics")

        # Create Ollama service if URL provided or use existing
        ollama_service = self._ollama_service
        if ollama_url:
            ollama_service = OllamaService(base_url=ollama_url)

        if not ollama_service:
            ollama_service = OllamaService()  # Use default URL

        subscription = {
            "type": "ollama_metrics",
            "interval_seconds": interval_seconds,
            "ollama_service": ollama_service,
            "task": None,
        }

        # Start Ollama metrics streaming task
        task = asyncio.create_task(self.stream_ollama_metrics(connection_id, subscription))
        subscription["task"] = task

        self.active_subscriptions[connection_id] = subscription

        # Send confirmation
        await connection_manager.send_message(
            connection_id, {"type": "ollama_metrics_subscribed", "interval_seconds": interval_seconds}
        )

        logger.info(
            f"Ollama metrics subscription started for {connection_id}",
            extra={
                "component": "websocket",
                "action": "ollama_metrics_subscribe",
                "connection_id": connection_id,
                "interval": interval_seconds,
            },
        )

    async def handle_ollama_metrics_unsubscribe(self, connection_id: str, message: Dict[str, Any]):
        """Unsubscribe from Ollama metrics updates."""
        await self._cancel_subscription(connection_id, "ollama_metrics")

        await connection_manager.send_message(connection_id, {"type": "ollama_metrics_unsubscribed"})

        logger.info(
            f"Ollama metrics subscription stopped for {connection_id}",
            extra={"component": "websocket", "action": "ollama_metrics_unsubscribe", "connection_id": connection_id},
        )

    async def _cancel_subscription(self, connection_id: str, subscription_type: str):
        """Cancel existing subscription."""
        if connection_id in self.active_subscriptions:
            subscription = self.active_subscriptions[connection_id]
            if subscription.get("type") == subscription_type:
                task = subscription.get("task")
                if task:
                    task.cancel()
                del self.active_subscriptions[connection_id]

    async def stream_training_updates(self, connection_id: str, subscription: Dict[str, Any]):
        """Stream general training updates to WebSocket connection."""
        interval_seconds = subscription["interval_seconds"]

        try:
            while True:
                # Get training stats from database
                # For now, using mock data - in production, would query database
                training_data = {
                    "type": "training_update",
                    "stats": {
                        "active_sessions": 0,
                        "queued_sessions": 0,
                        "completed_today": 0,
                        "total_prompts": 0,
                        "validated_prompts": 0,
                    },
                    "recent_activity": [],
                }

                success = await connection_manager.send_message(connection_id, training_data)
                if not success:
                    break

                await asyncio.sleep(interval_seconds)

        except asyncio.CancelledError:
            logger.info(f"Training updates streaming cancelled for {connection_id}")
        except Exception as e:
            logger.error(f"Error streaming training updates for {connection_id}: {e}")

    async def stream_session_progress(self, connection_id: str, subscription: Dict[str, Any]):
        """Stream specific session progress to WebSocket connection."""
        interval_seconds = subscription["interval_seconds"]
        session_id = subscription["session_id"]

        try:
            while True:
                # Get session progress from database
                # For now, using mock data - in production, would query database
                session_data = {
                    "type": "session_progress",
                    "session_id": session_id,
                    "status": "idle",
                    "progress": {
                        "current_step": 0,
                        "total_steps": 0,
                        "percent_complete": 0,
                        "current_prompt": None,
                        "prompts_processed": 0,
                        "prompts_total": 0,
                    },
                    "metrics": {
                        "loss": None,
                        "accuracy": None,
                        "learning_rate": None,
                        "elapsed_seconds": 0,
                        "estimated_remaining_seconds": None,
                    },
                }

                success = await connection_manager.send_message(connection_id, session_data)
                if not success:
                    break

                await asyncio.sleep(interval_seconds)

        except asyncio.CancelledError:
            logger.info(f"Session progress streaming cancelled for {connection_id}")
        except Exception as e:
            logger.error(f"Error streaming session progress for {connection_id}: {e}")

    async def stream_ollama_metrics(self, connection_id: str, subscription: Dict[str, Any]):
        """Stream Ollama metrics to WebSocket connection."""
        interval_seconds = subscription["interval_seconds"]
        ollama_service: OllamaService = subscription["ollama_service"]

        try:
            while True:
                # Get Ollama health and metrics
                health = await ollama_service.health_check()

                ollama_data = {
                    "type": "ollama_metrics",
                    "health": health,
                    "models": [],
                    "running_models": [],
                }

                if health.get("status") == "healthy":
                    try:
                        # Get models list
                        models = await ollama_service.list_models()
                        ollama_data["models"] = [m.to_dict() for m in models]
                        ollama_data["model_count"] = len(models)
                        ollama_data["total_size_gb"] = sum(m.size_gb for m in models)

                        # Get running models
                        running = await ollama_service.get_running_models()
                        ollama_data["running_models"] = running
                        ollama_data["running_count"] = len(running)
                    except Exception as e:
                        logger.warning(f"Error fetching Ollama models: {e}")
                        ollama_data["error"] = str(e)

                success = await connection_manager.send_message(connection_id, ollama_data)
                if not success:
                    break

                await asyncio.sleep(interval_seconds)

        except asyncio.CancelledError:
            logger.info(f"Ollama metrics streaming cancelled for {connection_id}")
        except Exception as e:
            logger.error(f"Error streaming Ollama metrics for {connection_id}: {e}")

    async def broadcast_training_event(self, event_type: str, data: Dict[str, Any]):
        """Broadcast training event to all subscribed connections."""
        message = {"type": event_type, **data, "timestamp": datetime.utcnow().isoformat()}

        for connection_id, subscription in self.active_subscriptions.items():
            if subscription.get("type") in ["training", "session"]:
                await connection_manager.send_message(connection_id, message)

    async def broadcast_session_event(self, session_id: str, event_type: str, data: Dict[str, Any]):
        """Broadcast session-specific event to subscribed connections."""
        message = {"type": event_type, "session_id": session_id, **data, "timestamp": datetime.utcnow().isoformat()}

        for connection_id, subscription in self.active_subscriptions.items():
            if subscription.get("type") == "session":
                if subscription.get("session_id") == session_id:
                    await connection_manager.send_message(connection_id, message)


# Global handler instance
training_ws_handler = TrainingWebSocketHandler()


async def handle_training_websocket(websocket: WebSocket):
    """WebSocket endpoint for training progress."""
    await training_ws_handler.handle_connection(websocket)
