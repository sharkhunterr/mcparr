"""Training Workers router - manages GPU training workers."""

from datetime import datetime, timedelta
from typing import List, Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import async_session_maker, get_db_session
from src.models import (
    ServiceConfig,
    TrainingWorker,
    WorkerMetricsSnapshot,
    WorkerStatus,
)

router = APIRouter(prefix="/api/workers", tags=["workers"])


# ============= Pydantic Schemas =============


class WorkerCreate(BaseModel):
    """Create a new worker."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    url: str = Field(..., description="Worker URL (e.g., http://192.168.1.100:8080)")
    api_key: Optional[str] = Field(None, description="Optional API key for authentication")
    ollama_service_id: Optional[str] = Field(None, description="Ollama service to use for model import")


class WorkerUpdate(BaseModel):
    """Update a worker."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    url: Optional[str] = None
    api_key: Optional[str] = None
    enabled: Optional[bool] = None
    ollama_service_id: Optional[str] = None


class WorkerResponse(BaseModel):
    """Worker response."""

    id: str
    name: str
    description: Optional[str]
    url: str
    status: str
    enabled: bool
    last_seen_at: Optional[str]
    last_error: Optional[str]
    gpu_available: bool
    gpu_count: int
    gpu_names: List[str]
    gpu_memory_total_mb: float
    worker_version: Optional[str]
    platform: Optional[str]
    ollama_service_id: Optional[str]
    current_job_id: Optional[str]
    current_session_id: Optional[str]
    total_jobs_completed: int
    total_training_time_seconds: float
    created_at: str
    updated_at: str


class WorkerMetricsResponse(BaseModel):
    """Worker metrics response."""

    worker_id: str
    recorded_at: str
    cpu_percent: Optional[float]
    memory_percent: Optional[float]
    memory_used_mb: Optional[float]
    gpu_utilization_percent: Optional[float]
    gpu_memory_percent: Optional[float]
    gpu_temperature_c: Optional[float]
    gpu_power_draw_w: Optional[float]
    training_progress_percent: Optional[float]
    training_loss: Optional[float]


class WorkerTestResult(BaseModel):
    """Result of testing a worker connection."""

    success: bool
    message: str
    worker_info: Optional[dict] = None
    error: Optional[str] = None


class TrainingStartRequest(BaseModel):
    """Request to start training on a worker."""

    session_id: str = Field(..., description="Training session ID from MCParr")
    base_model: str = Field(default="unsloth/llama-3.2-3b-instruct-bnb-4bit")
    output_model_name: str = Field(..., description="Output model name in Ollama")
    overwrite_existing: bool = Field(default=False, description="Overwrite if model exists")

    # Training hyperparameters
    num_epochs: int = Field(default=3, ge=1, le=100)
    batch_size: int = Field(default=2, ge=1, le=32)
    learning_rate: float = Field(default=2e-4)
    max_seq_length: int = Field(default=2048)
    warmup_steps: int = Field(default=5)
    lora_r: int = Field(default=16)
    lora_alpha: int = Field(default=16)
    quantization_method: str = Field(default="q4_k_m")


# ============= Helper Functions =============


async def get_worker_or_404(worker_id: str, session: AsyncSession) -> TrainingWorker:
    """Get worker by ID or raise 404."""
    result = await session.execute(select(TrainingWorker).where(TrainingWorker.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


def worker_to_response(worker: TrainingWorker) -> WorkerResponse:
    """Convert worker model to response."""
    return WorkerResponse(
        id=worker.id,
        name=worker.name,
        description=worker.description,
        url=worker.url,
        status=worker.status.value,
        enabled=worker.enabled,
        last_seen_at=worker.last_seen_at.isoformat() if worker.last_seen_at else None,
        last_error=worker.last_error,
        gpu_available=worker.gpu_available,
        gpu_count=worker.gpu_count,
        gpu_names=worker.gpu_names or [],
        gpu_memory_total_mb=worker.gpu_memory_total_mb,
        worker_version=worker.worker_version,
        platform=worker.platform,
        ollama_service_id=worker.ollama_service_id,
        current_job_id=worker.current_job_id,
        current_session_id=worker.current_session_id,
        total_jobs_completed=worker.total_jobs_completed,
        total_training_time_seconds=worker.total_training_time_seconds,
        created_at=worker.created_at.isoformat(),
        updated_at=worker.updated_at.isoformat(),
    )


async def fetch_worker_info(url: str, api_key: Optional[str] = None) -> dict:
    """Fetch worker info from the worker API."""
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{url.rstrip('/')}/", headers=headers)
        response.raise_for_status()
        return response.json()


async def fetch_worker_metrics(url: str, api_key: Optional[str] = None) -> dict:
    """Fetch metrics from the worker API."""
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{url.rstrip('/')}/api/metrics", headers=headers)
        response.raise_for_status()
        return response.json()


async def update_worker_status(worker: TrainingWorker, session: AsyncSession):
    """Update worker status by polling the worker API."""
    try:
        info = await fetch_worker_info(worker.url, worker.api_key)

        # Use worker's reported status, not just presence of job_id
        worker_status = info.get("status", "idle").lower()
        if worker_status == "training":
            worker.status = WorkerStatus.TRAINING
        elif worker_status in ("idle", "completed"):
            worker.status = WorkerStatus.ONLINE
            # Clear job_id when worker is idle/completed
            worker.current_job_id = None
        else:
            worker.status = WorkerStatus.ONLINE

        worker.last_seen_at = datetime.utcnow()
        worker.last_error = None
        worker.gpu_available = info.get("gpu_available", False)
        worker.gpu_count = info.get("gpu_count", 0)
        worker.gpu_names = info.get("gpu_names", [])
        worker.worker_version = info.get("version")
        # Only update current_job_id if worker is actively training
        if worker_status == "training":
            worker.current_job_id = info.get("current_job_id")

        # Calculate total GPU memory
        if worker.gpu_names:
            metrics = await fetch_worker_metrics(worker.url, worker.api_key)
            total_mem = sum(g.get("memory", {}).get("total_mb", 0) for g in metrics.get("gpus", []))
            worker.gpu_memory_total_mb = total_mem

    except httpx.ConnectError:
        worker.status = WorkerStatus.OFFLINE
        worker.last_error = "Cannot connect to worker"
    except httpx.TimeoutException:
        worker.status = WorkerStatus.OFFLINE
        worker.last_error = "Connection timeout"
    except Exception as e:
        worker.status = WorkerStatus.ERROR
        worker.last_error = str(e)

    worker.updated_at = datetime.utcnow()
    await session.commit()


# ============= Endpoints =============


@router.get("", response_model=List[WorkerResponse])
async def list_workers(enabled_only: bool = Query(default=False), session: AsyncSession = Depends(get_db_session)):
    """List all training workers."""
    query = select(TrainingWorker).order_by(desc(TrainingWorker.created_at))

    if enabled_only:
        query = query.where(TrainingWorker.enabled is True)

    result = await session.execute(query)
    workers = result.scalars().all()

    return [worker_to_response(w) for w in workers]


@router.post("", response_model=WorkerResponse, status_code=201)
async def create_worker(data: WorkerCreate, session: AsyncSession = Depends(get_db_session)):
    """Create a new training worker."""
    # Check if URL already exists
    result = await session.execute(select(TrainingWorker).where(TrainingWorker.url == data.url))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Worker with this URL already exists")

    worker = TrainingWorker(
        name=data.name,
        description=data.description,
        url=data.url.rstrip("/"),
        api_key=data.api_key,
        ollama_service_id=data.ollama_service_id,
        status=WorkerStatus.UNKNOWN,
    )

    session.add(worker)
    await session.commit()
    await session.refresh(worker)

    # Try to fetch worker info
    await update_worker_status(worker, session)

    return worker_to_response(worker)


@router.get("/{worker_id}", response_model=WorkerResponse)
async def get_worker(worker_id: str, session: AsyncSession = Depends(get_db_session)):
    """Get a specific worker."""
    worker = await get_worker_or_404(worker_id, session)
    return worker_to_response(worker)


@router.patch("/{worker_id}", response_model=WorkerResponse)
async def update_worker(worker_id: str, data: WorkerUpdate, session: AsyncSession = Depends(get_db_session)):
    """Update a worker."""
    worker = await get_worker_or_404(worker_id, session)

    if data.name is not None:
        worker.name = data.name
    if data.description is not None:
        worker.description = data.description
    if data.url is not None:
        worker.url = data.url.rstrip("/")
    if data.api_key is not None:
        worker.api_key = data.api_key
    if data.enabled is not None:
        worker.enabled = data.enabled
    if data.ollama_service_id is not None:
        worker.ollama_service_id = data.ollama_service_id

    worker.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(worker)

    return worker_to_response(worker)


@router.delete("/{worker_id}")
async def delete_worker(worker_id: str, session: AsyncSession = Depends(get_db_session)):
    """Delete a worker."""
    worker = await get_worker_or_404(worker_id, session)

    # Check if worker has an active job
    if worker.current_job_id:
        raise HTTPException(status_code=400, detail="Cannot delete worker with active training job")

    await session.delete(worker)
    await session.commit()

    return {"message": "Worker deleted"}


@router.post("/{worker_id}/test", response_model=WorkerTestResult)
async def test_worker(worker_id: str, session: AsyncSession = Depends(get_db_session)):
    """Test connection to a worker."""
    worker = await get_worker_or_404(worker_id, session)

    try:
        info = await fetch_worker_info(worker.url, worker.api_key)

        # Update worker info
        await update_worker_status(worker, session)

        return WorkerTestResult(
            success=True, message=f"Connected to {info.get('worker_name', 'worker')}", worker_info=info
        )

    except httpx.ConnectError as e:
        return WorkerTestResult(success=False, message="Cannot connect to worker", error=str(e))
    except httpx.HTTPStatusError as e:
        return WorkerTestResult(success=False, message=f"HTTP error: {e.response.status_code}", error=str(e))
    except Exception as e:
        return WorkerTestResult(success=False, message="Connection failed", error=str(e))


@router.post("/{worker_id}/refresh")
async def refresh_worker_status(worker_id: str, session: AsyncSession = Depends(get_db_session)):
    """Refresh worker status."""
    worker = await get_worker_or_404(worker_id, session)
    await update_worker_status(worker, session)
    return worker_to_response(worker)


@router.get("/{worker_id}/metrics", response_model=WorkerMetricsResponse)
async def get_worker_metrics(worker_id: str, session: AsyncSession = Depends(get_db_session)):
    """Get current metrics from a worker."""
    worker = await get_worker_or_404(worker_id, session)

    if worker.status == WorkerStatus.OFFLINE:
        raise HTTPException(status_code=503, detail="Worker is offline")

    try:
        metrics = await fetch_worker_metrics(worker.url, worker.api_key)

        # Get first GPU metrics if available
        gpu_metrics = metrics.get("gpus", [{}])[0] if metrics.get("gpus") else {}

        return WorkerMetricsResponse(
            worker_id=worker.id,
            recorded_at=metrics.get("timestamp", datetime.utcnow().isoformat()),
            cpu_percent=metrics.get("cpu", {}).get("percent_total"),
            memory_percent=metrics.get("memory", {}).get("percent"),
            memory_used_mb=metrics.get("memory", {}).get("used_mb"),
            gpu_utilization_percent=gpu_metrics.get("gpu_utilization_percent"),
            gpu_memory_percent=gpu_metrics.get("memory_percent"),
            gpu_temperature_c=gpu_metrics.get("temperature_c"),
            gpu_power_draw_w=gpu_metrics.get("power_draw_w"),
            training_progress_percent=None,  # Will be set if training
            training_loss=None,
        )

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to get metrics: {e}") from e


@router.get("/{worker_id}/metrics/history")
async def get_worker_metrics_history(
    worker_id: str,
    limit: int = Query(default=100, le=1000),
    minutes: int = Query(default=60, le=1440),
    session: AsyncSession = Depends(get_db_session),
):
    """Get historical metrics for a worker."""
    await get_worker_or_404(worker_id, session)

    since = datetime.utcnow() - timedelta(minutes=minutes)

    result = await session.execute(
        select(WorkerMetricsSnapshot)
        .where(WorkerMetricsSnapshot.worker_id == worker_id)
        .where(WorkerMetricsSnapshot.recorded_at >= since)
        .order_by(desc(WorkerMetricsSnapshot.recorded_at))
        .limit(limit)
    )
    snapshots = result.scalars().all()

    return {
        "worker_id": worker_id,
        "count": len(snapshots),
        "metrics": [
            {
                "recorded_at": s.recorded_at.isoformat(),
                "cpu_percent": s.cpu_percent,
                "memory_percent": s.memory_percent,
                "gpu_utilization_percent": s.gpu_utilization_percent,
                "gpu_memory_percent": s.gpu_memory_percent,
                "gpu_temperature_c": s.gpu_temperature_c,
                "training_progress_percent": s.training_progress_percent,
                "training_loss": s.training_loss,
            }
            for s in snapshots
        ],
    }


@router.post("/{worker_id}/training/start")
async def start_training_on_worker(
    worker_id: str,
    request: TrainingStartRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
):
    """Start training on a worker."""
    from src.models import TrainingPrompt, TrainingSession, TrainingStatus

    worker = await get_worker_or_404(worker_id, session)

    # Check worker status
    if worker.status == WorkerStatus.OFFLINE:
        raise HTTPException(status_code=503, detail="Worker is offline")
    if worker.status == WorkerStatus.TRAINING:
        raise HTTPException(status_code=409, detail="Worker is already training")
    if not worker.gpu_available:
        raise HTTPException(status_code=503, detail="Worker has no GPU available")

    # Get training session and prompts
    result = await session.execute(select(TrainingSession).where(TrainingSession.id == request.session_id))
    training_session = result.scalar_one_or_none()
    if not training_session:
        raise HTTPException(status_code=404, detail="Training session not found")

    # Get prompts
    prompt_result = await session.execute(
        select(TrainingPrompt).where(
            TrainingPrompt.id.in_(
                select(TrainingPrompt.id).join(TrainingSession.prompts).where(TrainingSession.id == request.session_id)
            )
        )
    )
    prompts = prompt_result.scalars().all()

    if not prompts:
        raise HTTPException(status_code=400, detail="No prompts in training session")

    # Get Ollama URL
    ollama_url = "http://localhost:11434"
    if worker.ollama_service_id:
        service_result = await session.execute(
            select(ServiceConfig).where(ServiceConfig.id == worker.ollama_service_id)
        )
        service = service_result.scalar_one_or_none()
        if service and service.url:
            ollama_url = service.url.rstrip("/")

    # Prepare prompts data for new worker API
    prompts_data = [
        {
            "id": str(p.id),
            "system_prompt": p.system_prompt,
            "user_input": p.user_input,
            "expected_output": p.expected_output,
        }
        for p in prompts
    ]

    # Build request body for new worker API v2.0
    training_request = {
        "session_id": request.session_id,
        "session_name": training_session.name,
        "base_model": request.base_model,
        "output_model_name": request.output_model_name,
        "prompts": prompts_data,
        "hyperparameters": {
            "num_epochs": request.num_epochs,
            "batch_size": request.batch_size,
            "learning_rate": request.learning_rate,
            "max_seq_length": request.max_seq_length,
            "warmup_ratio": 0.1,
            "lora_r": request.lora_r,
            "lora_alpha": request.lora_alpha,
            "lora_dropout": 0.05,
            "gradient_accumulation_steps": 4,
            "weight_decay": 0.01,
            "quantization_method": request.quantization_method or "q4_k_m",
        },
        "ollama_target": {
            "url": ollama_url,
            "model_name": request.output_model_name,
            "overwrite": request.overwrite_existing,
        },
        "backend_ws_url": None,  # Will be set up later for real-time updates
    }

    # Start training on worker
    try:
        headers = {}
        if worker.api_key:
            headers["X-API-Key"] = worker.api_key

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{worker.url}/api/training/start", headers=headers, json=training_request)
            response.raise_for_status()
            result_data = response.json()

        # Update worker status
        worker.status = WorkerStatus.TRAINING
        worker.current_job_id = result_data.get("job_id")
        worker.current_session_id = request.session_id
        worker.updated_at = datetime.utcnow()

        # Update training session
        training_session.status = TrainingStatus.RUNNING
        training_session.started_at = datetime.utcnow()
        training_session.updated_at = datetime.utcnow()

        await session.commit()

        return {
            "message": "Training started on worker",
            "worker_id": worker_id,
            "job_id": result_data.get("job_id"),
            "session_id": request.session_id,
        }

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Worker error: {e.response.text}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start training: {e}") from e


@router.get("/{worker_id}/training/status")
async def get_worker_training_status(worker_id: str, session: AsyncSession = Depends(get_db_session)):
    """Get current training status from a worker."""
    worker = await get_worker_or_404(worker_id, session)

    if not worker.current_job_id:
        return {"status": "idle", "job_id": None}

    try:
        headers = {}
        if worker.api_key:
            headers["X-API-Key"] = worker.api_key

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{worker.url}/training/status", headers=headers)
            response.raise_for_status()
            return response.json()

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to get training status: {e}") from e


@router.post("/{worker_id}/training/cancel")
async def cancel_worker_training(worker_id: str, session: AsyncSession = Depends(get_db_session)):
    """Cancel training on a worker."""
    worker = await get_worker_or_404(worker_id, session)

    if not worker.current_job_id:
        raise HTTPException(status_code=400, detail="No active training job")

    try:
        headers = {}
        if worker.api_key:
            headers["X-API-Key"] = worker.api_key

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{worker.url}/training/cancel", headers=headers)
            response.raise_for_status()

        # Update worker status
        worker.status = WorkerStatus.ONLINE
        worker.current_job_id = None
        worker.current_session_id = None
        worker.updated_at = datetime.utcnow()
        await session.commit()

        return {"message": "Training cancelled"}

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to cancel training: {e}") from e


@router.get("/{worker_id}/models")
async def get_available_models(worker_id: str, session: AsyncSession = Depends(get_db_session)):
    """Get available base models for training."""
    worker = await get_worker_or_404(worker_id, session)

    try:
        headers = {}
        if worker.api_key:
            headers["X-API-Key"] = worker.api_key

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{worker.url}/models", headers=headers)
            response.raise_for_status()
            return response.json()

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to get models: {e}") from e


@router.post("/refresh-all")
async def refresh_all_workers(background_tasks: BackgroundTasks, session: AsyncSession = Depends(get_db_session)):
    """Refresh status of all enabled workers."""
    result = await session.execute(select(TrainingWorker).where(TrainingWorker.enabled is True))
    workers = result.scalars().all()

    async def refresh_worker(worker_id: str):
        async with async_session_maker() as db_session:
            result = await db_session.execute(select(TrainingWorker).where(TrainingWorker.id == worker_id))
            worker = result.scalar_one_or_none()
            if worker:
                await update_worker_status(worker, db_session)

    for worker in workers:
        background_tasks.add_task(refresh_worker, worker.id)

    return {"message": f"Refreshing {len(workers)} workers", "count": len(workers)}
