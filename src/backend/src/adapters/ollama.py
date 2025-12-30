"""Ollama adapter for local LLM server integration."""

from typing import Dict, Any, List
import httpx
from datetime import datetime

from .base import (
    BaseServiceAdapter,
    ServiceCapability,
    ConnectionTestResult,
)


class OllamaAdapter(BaseServiceAdapter):
    """
    Adapter for Ollama local LLM server.

    Ollama is a local LLM server that provides an easy way to run
    large language models on your own hardware.

    Capabilities:
        - API_ACCESS: Access to Ollama API for model management and inference

    Auth:
        Ollama doesn't require authentication by default
    """

    @property
    def service_type(self) -> str:
        return "ollama"

    @property
    def supported_capabilities(self) -> List[ServiceCapability]:
        return [
            ServiceCapability.API_ACCESS
        ]

    def get_auth_headers(self) -> Dict[str, str]:
        """Ollama doesn't require authentication headers."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def validate_config(self) -> List[str]:
        """Validate Ollama configuration."""
        errors = []
        if not self.service_config.base_url:
            errors.append("Base URL is required")
        return errors

    async def test_connection(self) -> ConnectionTestResult:
        """Test connection to Ollama server."""
        start_time = datetime.utcnow()

        try:
            # Test by getting version info
            response = await self._make_request("GET", "/api/version")

            end_time = datetime.utcnow()
            response_time = int((end_time - start_time).total_seconds() * 1000)

            data = response.json()

            if "version" in data:
                # Also try to get list of models
                models_response = await self._safe_request("GET", "/api/tags")
                model_count = 0
                models = []
                if models_response and "models" in models_response:
                    model_count = len(models_response["models"])
                    models = [m.get("name", "unknown") for m in models_response["models"][:5]]

                return ConnectionTestResult(
                    success=True,
                    message=f"Connected to Ollama v{data['version']}",
                    response_time_ms=response_time,
                    details={
                        "status": "connected",
                        "version": data.get("version"),
                        "model_count": model_count,
                        "models": models
                    }
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message="Connected but response doesn't appear to be from Ollama",
                    response_time_ms=response_time,
                    details={"status": "invalid_response"}
                )

        except httpx.HTTPStatusError as e:
            return ConnectionTestResult(
                success=False,
                message=f"HTTP error: {e.response.status_code}",
                details={"status": "http_error", "status_code": e.response.status_code}
            )
        except httpx.RequestError as e:
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                details={"status": "connection_failed", "error": str(e)}
            )
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Unexpected error: {str(e)}",
                details={"status": "unexpected_error", "error": str(e)}
            )

    async def get_service_info(self) -> Dict[str, Any]:
        """Get Ollama service information."""
        info = {
            "service_type": self.service_type,
            "base_url": self.base_url
        }

        try:
            # Get version
            version_response = await self._safe_request("GET", "/api/version")
            if version_response:
                info["version"] = version_response.get("version", "unknown")

            # Get models
            models_response = await self._safe_request("GET", "/api/tags")
            if models_response and "models" in models_response:
                models = models_response["models"]
                info["models"] = [
                    {
                        "name": m.get("name"),
                        "size": m.get("size", 0),
                        "modified_at": m.get("modified_at"),
                        "details": m.get("details", {})
                    }
                    for m in models
                ]
                info["model_count"] = len(models)
                info["total_size"] = sum(m.get("size", 0) for m in models)

            # Get running models
            ps_response = await self._safe_request("GET", "/api/ps")
            if ps_response and "models" in ps_response:
                info["running_models"] = ps_response["models"]
                info["running_count"] = len(ps_response["models"])

        except Exception as e:
            self.logger.error(f"Error getting Ollama service info: {e}")
            info["error"] = str(e)

        return info

    async def get_statistics(self) -> Dict[str, Any]:
        """Get Ollama statistics."""
        stats = {
            "models": [],
            "running_models": [],
            "total_size_bytes": 0
        }

        try:
            # Get models
            models_response = await self._safe_request("GET", "/api/tags")
            if models_response and "models" in models_response:
                models = models_response["models"]
                stats["models"] = models
                stats["model_count"] = len(models)
                stats["total_size_bytes"] = sum(m.get("size", 0) for m in models)
                stats["total_size_gb"] = round(stats["total_size_bytes"] / (1024**3), 2)

            # Get running models
            ps_response = await self._safe_request("GET", "/api/ps")
            if ps_response and "models" in ps_response:
                stats["running_models"] = ps_response["models"]
                stats["running_count"] = len(ps_response["models"])

        except Exception as e:
            self.logger.error(f"Error getting Ollama statistics: {e}")
            stats["error"] = str(e)

        return stats

    async def list_models(self) -> List[Dict[str, Any]]:
        """List all available models."""
        models_response = await self._safe_request("GET", "/api/tags")
        if models_response and "models" in models_response:
            return models_response["models"]
        return []

    async def get_running_models(self) -> List[Dict[str, Any]]:
        """Get list of currently running/loaded models."""
        ps_response = await self._safe_request("GET", "/api/ps")
        if ps_response and "models" in ps_response:
            return ps_response["models"]
        return []
