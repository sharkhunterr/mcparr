"""Training Worker Client - Communicates with GPU training worker."""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import httpx
from loguru import logger

from src.config.settings import get_settings


@dataclass
class WorkerStatus:
    """Training worker status."""
    online: bool
    worker_id: str = ""
    worker_name: str = ""
    status: str = "unknown"
    gpu_available: bool = False
    gpu_count: int = 0
    gpu_names: List[str] = None
    current_job_id: Optional[str] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.gpu_names is None:
            self.gpu_names = []


@dataclass
class TrainingJobStatus:
    """Training job status from worker."""
    job_id: str
    session_id: str
    status: str
    progress_percent: float
    current_step: int
    total_steps: int
    current_epoch: int
    total_epochs: int
    loss: Optional[float]
    learning_rate: Optional[float]
    message: str
    started_at: Optional[str]
    eta_seconds: Optional[float]
    error: Optional[str]
    output_path: Optional[str]
    samples_per_second: float = 0.0
    gradient_norm: Optional[float] = None
    loss_history: Optional[List[float]] = None  # Full loss history from worker


class WorkerClientError(Exception):
    """Worker client error."""
    pass


class WorkerClient:
    """Client for communicating with the training worker."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        settings = get_settings()
        self.base_url = (base_url or settings.training_worker_url).rstrip("/")
        self.api_key = api_key or settings.training_worker_api_key
        self.timeout = httpx.Timeout(30.0, connect=10.0)

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def health_check(self) -> WorkerStatus:
        """Check if worker is online and get its status."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    headers=self._get_headers()
                )
                if response.status_code == 200:
                    data = response.json()
                    return WorkerStatus(
                        online=True,
                        worker_id=data.get("worker_id", ""),
                        status="healthy",
                        gpu_available=data.get("gpu_available", False)
                    )
                return WorkerStatus(online=False, error=f"HTTP {response.status_code}")
        except httpx.ConnectError:
            return WorkerStatus(online=False, error="Connection refused")
        except httpx.TimeoutException:
            return WorkerStatus(online=False, error="Connection timeout")
        except Exception as e:
            return WorkerStatus(online=False, error=str(e))

    async def get_worker_info(self) -> WorkerStatus:
        """Get detailed worker information."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/",
                    headers=self._get_headers()
                )
                if response.status_code == 200:
                    data = response.json()
                    return WorkerStatus(
                        online=True,
                        worker_id=data.get("worker_id", ""),
                        worker_name=data.get("worker_name", ""),
                        status=data.get("status", "unknown"),
                        gpu_available=data.get("gpu_available", False),
                        gpu_count=data.get("gpu_count", 0),
                        gpu_names=data.get("gpu_names", []),
                        current_job_id=data.get("current_job_id")
                    )
                return WorkerStatus(online=False, error=f"HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to get worker info: {e}")
            return WorkerStatus(online=False, error=str(e))

    async def get_gpu_metrics(self) -> Dict[str, Any]:
        """Get GPU metrics from worker."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/metrics/gpu",
                    headers=self._get_headers()
                )
                if response.status_code == 200:
                    return response.json()
                return {"available": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"available": False, "error": str(e)}

    async def start_training(
        self,
        session_id: str,
        prompts: List[Dict[str, Any]],
        base_model: str = "unsloth/llama-3.2-3b-instruct-bnb-4bit",
        output_model_name: str = "mcparr-finetuned",
        ollama_url: str = "http://localhost:11434",
        num_epochs: int = 3,
        batch_size: int = 2,
        learning_rate: float = 2e-4,
        max_seq_length: int = 2048,
        lora_r: int = 16,
        lora_alpha: int = 16,
        quantization_method: str = "q4_k_m",
        overwrite_existing: bool = False,
        base_adapter_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Start a training job on the worker.

        Args:
            session_id: MCParr session ID
            prompts: List of training prompts
            base_model: Unsloth base model ID
            output_model_name: Output model name
            ollama_url: URL to Ollama for importing finished model
            num_epochs: Number of training epochs
            batch_size: Training batch size
            learning_rate: Learning rate
            max_seq_length: Maximum sequence length
            lora_r: LoRA rank
            lora_alpha: LoRA alpha
            quantization_method: GGUF quantization method
            overwrite_existing: Overwrite existing Ollama model
            base_adapter_path: Path to existing LoRA adapter for incremental training

        Returns:
            Dict with job_id and status
        """
        # New worker API structure
        request_data = {
            "session_id": session_id,
            "base_model": base_model,
            "output_model_name": output_model_name,
            "prompts": [
                {
                    "system_prompt": p.get("system_prompt"),
                    "user_input": p["user_input"],
                    "expected_output": p["expected_output"]
                }
                for p in prompts
            ],
            "hyperparameters": {
                "num_epochs": num_epochs,
                "batch_size": batch_size,
                "learning_rate": learning_rate,
                "max_seq_length": max_seq_length,
                "warmup_steps": 5,
                "weight_decay": 0.01,
                "lora_r": lora_r,
                "lora_alpha": lora_alpha,
                "quantization_method": quantization_method
            },
            "ollama_target": {
                "url": ollama_url,
                "model_name": output_model_name,
                "overwrite": overwrite_existing
            }
        }

        # Add base_adapter_path for incremental training
        if base_adapter_path:
            request_data["base_adapter_path"] = base_adapter_path

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
                response = await client.post(
                    f"{self.base_url}/api/training/start",
                    json=request_data,
                    headers=self._get_headers()
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Training job started: {data.get('job_id')}")
                    return {
                        "success": True,
                        "job_id": data.get("job_id"),
                        "message": data.get("message"),
                        "status": data.get("status")
                    }
                elif response.status_code == 409:
                    return {
                        "success": False,
                        "error": "Worker is already training another job"
                    }
                elif response.status_code == 503:
                    return {
                        "success": False,
                        "error": "No GPU available on worker"
                    }
                else:
                    error_detail = response.json().get("detail", response.text)
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {error_detail}"
                    }

        except httpx.ConnectError:
            return {"success": False, "error": "Cannot connect to training worker"}
        except httpx.TimeoutException:
            return {"success": False, "error": "Training worker timeout"}
        except Exception as e:
            logger.error(f"Error starting training: {e}")
            return {"success": False, "error": str(e)}

    async def get_training_status(self) -> Optional[TrainingJobStatus]:
        """Get current training job status."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/training/status",
                    headers=self._get_headers()
                )

                if response.status_code == 200:
                    data = response.json()
                    if data is None:
                        return None
                    progress = data.get("progress", {})
                    return TrainingJobStatus(
                        job_id=data.get("job_id", ""),
                        session_id=data.get("session_id", ""),
                        status=data.get("status", "unknown"),
                        progress_percent=progress.get("progress_percent", data.get("progress_percent", 0)),
                        current_step=progress.get("current_step", data.get("current_step", 0)),
                        total_steps=progress.get("total_steps", data.get("total_steps", 0)),
                        current_epoch=progress.get("current_epoch", data.get("current_epoch", 0)),
                        total_epochs=progress.get("total_epochs", data.get("total_epochs", 0)),
                        loss=progress.get("loss", data.get("loss")),
                        learning_rate=progress.get("learning_rate", data.get("learning_rate")),
                        message=data.get("message", ""),
                        started_at=data.get("started_at"),
                        eta_seconds=progress.get("eta_seconds", data.get("eta_seconds")),
                        error=data.get("error"),
                        output_path=data.get("output_path"),
                        samples_per_second=progress.get("samples_per_second", 0.0),
                        gradient_norm=progress.get("gradient_norm"),
                    )
                return None

        except Exception as e:
            logger.warning(f"Failed to get training status: {e}")
            return None

    async def get_job_status(self, job_id: str) -> Optional[TrainingJobStatus]:
        """Get status for a specific job."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/training/job/{job_id}",
                    headers=self._get_headers()
                )

                if response.status_code == 200:
                    data = response.json()
                    # Progress fields can be nested under 'progress' or at top level
                    progress = data.get("progress", {})

                    # Get loss_history from worker
                    loss_history = progress.get("loss_history", [])

                    # Get loss - fallback to last element of loss_history if null
                    loss = progress.get("loss", data.get("loss"))
                    if loss is None and loss_history:
                        loss = loss_history[-1]

                    return TrainingJobStatus(
                        job_id=data.get("job_id", ""),
                        session_id=data.get("session_id", ""),
                        status=data.get("status", "unknown"),
                        progress_percent=progress.get("progress_percent", data.get("progress_percent", 0)),
                        current_step=progress.get("current_step", data.get("current_step", 0)),
                        total_steps=progress.get("total_steps", data.get("total_steps", 0)),
                        current_epoch=progress.get("current_epoch", data.get("current_epoch", 0)),
                        total_epochs=progress.get("total_epochs", data.get("total_epochs", 0)),
                        loss=loss,
                        learning_rate=progress.get("learning_rate", data.get("learning_rate")),
                        message=data.get("message", ""),
                        started_at=data.get("started_at"),
                        eta_seconds=progress.get("eta_seconds", data.get("eta_seconds")),
                        error=data.get("error"),
                        output_path=data.get("output_model", data.get("output_path")),
                        samples_per_second=progress.get("samples_per_second", 0.0),
                        gradient_norm=progress.get("gradient_norm"),
                        loss_history=loss_history if loss_history else None,
                    )
                return None

        except Exception as e:
            logger.warning(f"Failed to get job status: {e}")
            return None

    async def cancel_training(self) -> Dict[str, Any]:
        """Cancel the current training job."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/training/cancel",
                    headers=self._get_headers()
                )

                if response.status_code == 200:
                    return {"success": True, **response.json()}
                elif response.status_code == 404:
                    return {"success": False, "error": "No training job in progress"}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_available_models(self) -> Dict[str, Any]:
        """Get available base models for training."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self._get_headers()
                )

                if response.status_code == 200:
                    return response.json()
                return {"recommended": [], "quantization_methods": []}

        except Exception as e:
            logger.warning(f"Failed to get available models: {e}")
            return {"recommended": [], "quantization_methods": []}

    # ============= Logs Methods =============

    async def get_system_logs(self, tail: int = 100, level: Optional[str] = None) -> Dict[str, Any]:
        """Get system logs from worker."""
        try:
            params = {"tail": tail}
            if level:
                params["level"] = level

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/logs/system",
                    params=params,
                    headers=self._get_headers()
                )

                if response.status_code == 200:
                    return response.json()
                return {"logs": [], "count": 0, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            logger.warning(f"Failed to get system logs: {e}")
            return {"logs": [], "count": 0, "error": str(e)}

    async def get_job_logs(
        self,
        job_id: str,
        tail: int = 100,
        level: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get logs for a specific training job."""
        try:
            params = {"tail": tail}
            if level:
                params["level"] = level

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/logs/job/{job_id}",
                    params=params,
                    headers=self._get_headers()
                )

                if response.status_code == 200:
                    return response.json()
                return {"job_id": job_id, "logs": [], "count": 0, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            logger.warning(f"Failed to get job logs: {e}")
            return {"job_id": job_id, "logs": [], "count": 0, "error": str(e)}

    async def get_available_job_logs(self) -> Dict[str, Any]:
        """Get list of job IDs that have available logs."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/logs/jobs",
                    headers=self._get_headers()
                )

                if response.status_code == 200:
                    return response.json()
                return {"job_ids": [], "count": 0, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            logger.warning(f"Failed to get available job logs: {e}")
            return {"job_ids": [], "count": 0, "error": str(e)}

    async def delete_job_logs(self, job_id: str) -> Dict[str, Any]:
        """Delete logs for a specific job."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    f"{self.base_url}/logs/job/{job_id}",
                    headers=self._get_headers()
                )

                if response.status_code == 200:
                    return {"success": True, **response.json()}
                return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_job_logs_stream_url(self, job_id: str) -> str:
        """Get the SSE stream URL for job logs."""
        return f"{self.base_url}/logs/job/{job_id}/stream"

    def get_system_logs_stream_url(self) -> str:
        """Get the SSE stream URL for system logs."""
        return f"{self.base_url}/logs/system/stream"


# Singleton instance
_worker_client: Optional[WorkerClient] = None


def get_worker_client() -> WorkerClient:
    """Get or create worker client instance."""
    global _worker_client
    if _worker_client is None:
        _worker_client = WorkerClient()
    return _worker_client
