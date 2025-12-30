"""Ollama integration service for model management and training."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, AsyncGenerator
from enum import Enum

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models import ServiceConfig, ServiceType, ServiceStatus

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Base exception for Ollama service errors."""
    pass


class OllamaConnectionError(OllamaError):
    """Raised when unable to connect to Ollama."""
    pass


class OllamaModelError(OllamaError):
    """Raised when there's a model-related error."""
    pass


class OllamaModel:
    """Representation of an Ollama model."""

    def __init__(self, data: Dict[str, Any]):
        self.name = data.get("name", "")
        self.model = data.get("model", self.name)
        self.modified_at = data.get("modified_at")
        self.size = data.get("size", 0)
        self.digest = data.get("digest", "")
        self.details = data.get("details", {})

    @property
    def size_gb(self) -> float:
        """Get model size in GB."""
        return round(self.size / (1024 ** 3), 2)

    @property
    def family(self) -> str:
        """Get model family (e.g., llama, mistral)."""
        return self.details.get("family", "unknown")

    @property
    def parameter_size(self) -> str:
        """Get parameter size (e.g., 7B, 13B)."""
        return self.details.get("parameter_size", "")

    @property
    def quantization_level(self) -> str:
        """Get quantization level (e.g., Q4_0, Q8_0)."""
        return self.details.get("quantization_level", "")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "model": self.model,
            "modified_at": self.modified_at,
            "size": self.size,
            "size_gb": self.size_gb,
            "digest": self.digest,
            "family": self.family,
            "parameter_size": self.parameter_size,
            "quantization_level": self.quantization_level,
            "details": self.details
        }


class OllamaService:
    """Service for interacting with Ollama API."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(30.0, read=300.0)  # Longer read timeout for generation

    @classmethod
    async def from_service_config(
        cls,
        session: AsyncSession,
        service_id: Optional[str] = None
    ) -> Optional["OllamaService"]:
        """Create OllamaService from database configuration."""
        query = select(ServiceConfig).where(
            ServiceConfig.service_type == ServiceType.OLLAMA,
            ServiceConfig.enabled == True
        )
        if service_id:
            query = query.where(ServiceConfig.id == service_id)

        result = await session.execute(query)
        config = result.scalar_one_or_none()

        if not config:
            return None

        return cls(base_url=config.full_url)

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request to Ollama API."""
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                # Handle empty responses (e.g., DELETE returns 200 with no body)
                if response.headers.get("content-length") == "0" or not response.content:
                    return {}
                return response.json()
            except httpx.ConnectError as e:
                raise OllamaConnectionError(
                    f"Unable to connect to Ollama at {self.base_url}: {e}"
                )
            except httpx.HTTPStatusError as e:
                raise OllamaError(f"Ollama API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                raise OllamaError(f"Ollama request failed: {e}")

    async def _stream_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Make streaming HTTP request to Ollama API."""
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(method, url, **kwargs) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                yield json.loads(line)
                            except json.JSONDecodeError:
                                continue
            except httpx.ConnectError as e:
                raise OllamaConnectionError(
                    f"Unable to connect to Ollama at {self.base_url}: {e}"
                )
            except httpx.HTTPStatusError as e:
                raise OllamaError(f"Ollama API error: {e.response.status_code}")

    async def health_check(self) -> Dict[str, Any]:
        """Check Ollama server health."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(f"{self.base_url}/api/version")
                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "version": response.json().get("version", "unknown"),
                        "url": self.base_url
                    }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "url": self.base_url
            }
        return {"status": "unknown", "url": self.base_url}

    async def list_models(self) -> List[OllamaModel]:
        """List all available models."""
        data = await self._request("GET", "/api/tags")
        models = data.get("models", [])
        return [OllamaModel(m) for m in models]

    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get detailed information about a model."""
        data = await self._request("POST", "/api/show", json={"name": model_name})
        return data

    async def pull_model(
        self,
        model_name: str,
        progress_callback: Optional[callable] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Pull a model from Ollama registry with progress updates."""
        async for update in self._stream_request(
            "POST",
            "/api/pull",
            json={"name": model_name, "stream": True}
        ):
            if progress_callback:
                await progress_callback(update)
            yield update

    async def delete_model(self, model_name: str) -> bool:
        """Delete a model."""
        await self._request("DELETE", "/api/delete", json={"name": model_name})
        return True

    async def copy_model(self, source: str, destination: str) -> bool:
        """Copy a model to a new name."""
        try:
            await self._request("POST", "/api/copy", json={
                "source": source,
                "destination": destination
            })
            return True
        except OllamaError:
            return False

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate completion from a model (non-streaming)."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        if system:
            payload["system"] = system
        if options:
            payload["options"] = options

        return await self._request("POST", "/api/generate", json=payload)

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate completion from a model (streaming)."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True
        }
        if system:
            payload["system"] = system
        if options:
            payload["options"] = options

        async for chunk in self._stream_request("POST", "/api/generate", json=payload):
            yield chunk

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Chat completion from a model (non-streaming)."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        if options:
            payload["options"] = options

        return await self._request("POST", "/api/chat", json=payload)

    async def chat_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Chat completion from a model (streaming)."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }
        if options:
            payload["options"] = options

        async for chunk in self._stream_request("POST", "/api/chat", json=payload):
            yield chunk

    async def create_model(
        self,
        name: str,
        modelfile: str,
        progress_callback: Optional[callable] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Create a new model from a Modelfile."""
        async for update in self._stream_request(
            "POST",
            "/api/create",
            json={"name": name, "modelfile": modelfile, "stream": True}
        ):
            if progress_callback:
                await progress_callback(update)
            yield update

    async def get_running_models(self) -> List[Dict[str, Any]]:
        """Get list of currently loaded/running models."""
        try:
            data = await self._request("GET", "/api/ps")
            return data.get("models", [])
        except OllamaError:
            return []

    async def load_model(self, model_name: str) -> bool:
        """Load a model into memory (warm it up)."""
        try:
            # Use generate with empty prompt to load the model
            await self._request("POST", "/api/generate", json={
                "model": model_name,
                "prompt": "",
                "stream": False,
                "keep_alive": "10m"  # Keep in memory for 10 minutes
            })
            return True
        except OllamaError as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            return False

    async def unload_model(self, model_name: str) -> bool:
        """Unload a model from memory."""
        try:
            await self._request("POST", "/api/generate", json={
                "model": model_name,
                "prompt": "",
                "stream": False,
                "keep_alive": 0  # Immediately unload
            })
            return True
        except OllamaError as e:
            logger.error(f"Failed to unload model {model_name}: {e}")
            return False

    async def get_embeddings(
        self,
        model: str,
        prompt: str
    ) -> List[float]:
        """Get embeddings for text."""
        data = await self._request("POST", "/api/embeddings", json={
            "model": model,
            "prompt": prompt
        })
        return data.get("embedding", [])


class OllamaMetricsCollector:
    """Collect real-time metrics from Ollama."""

    def __init__(self, ollama_service: OllamaService):
        self.ollama = ollama_service
        self._collecting = False
        self._metrics_history: List[Dict[str, Any]] = []

    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect current Ollama metrics."""
        health = await self.ollama.health_check()

        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": health.get("status"),
            "version": health.get("version"),
            "models": [],
            "running_models": []
        }

        if health.get("status") == "healthy":
            try:
                models = await self.ollama.list_models()
                metrics["models"] = [m.to_dict() for m in models]
                metrics["model_count"] = len(models)
                metrics["total_size_gb"] = sum(m.size_gb for m in models)

                running = await self.ollama.get_running_models()
                metrics["running_models"] = running
                metrics["running_count"] = len(running)
            except Exception as e:
                logger.error(f"Error collecting Ollama metrics: {e}")

        self._metrics_history.append(metrics)
        # Keep last 100 metrics
        if len(self._metrics_history) > 100:
            self._metrics_history = self._metrics_history[-100:]

        return metrics

    def get_metrics_history(self) -> List[Dict[str, Any]]:
        """Get collected metrics history."""
        return self._metrics_history

    async def start_collection(self, interval: int = 30):
        """Start periodic metrics collection."""
        self._collecting = True
        while self._collecting:
            await self.collect_metrics()
            await asyncio.sleep(interval)

    def stop_collection(self):
        """Stop metrics collection."""
        self._collecting = False


# Singleton instance
_ollama_service: Optional[OllamaService] = None
_metrics_collector: Optional[OllamaMetricsCollector] = None


async def get_ollama_service(
    session: AsyncSession = None,
    service_id: str = None,
    allow_fallback: bool = False
) -> Optional[OllamaService]:
    """Get or create Ollama service instance.

    Args:
        session: Database session to fetch service config
        service_id: Optional specific service ID
        allow_fallback: If True, fallback to localhost:11434 when no config found

    Returns:
        OllamaService instance or None if no configuration found and fallback disabled
    """
    global _ollama_service

    if session:
        service = await OllamaService.from_service_config(session, service_id)
        if service:
            _ollama_service = service
            return service

    # Only use cached service if it was properly configured
    if _ollama_service is not None:
        return _ollama_service

    # Only fallback to default URL if explicitly allowed
    if allow_fallback:
        return OllamaService()

    return None


def get_metrics_collector(ollama_service: OllamaService = None) -> OllamaMetricsCollector:
    """Get or create metrics collector instance."""
    global _metrics_collector

    if _metrics_collector is None and ollama_service:
        _metrics_collector = OllamaMetricsCollector(ollama_service)

    return _metrics_collector
