"""Training and Ollama management endpoints."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.database.connection import async_session_maker, get_db_session
from src.models import (
    PromptCategory,
    PromptDifficulty,
    PromptFormat,
    PromptSource,
    ServiceConfig,
    ServiceType,
    TrainingPrompt,
    TrainingSession,
    TrainingStatus,
    TrainingType,
    session_prompt_association,
)
from src.services.ollama_service import (
    OllamaConnectionError,
    OllamaError,
    get_ollama_service,
)
from src.services.training_service import (
    OllamaModelfileConfig,
    TrainingConfig,
    TrainingService,
)
from src.services.training_ws import connection_manager
from src.services.worker_client import WorkerClient, get_worker_client

# Global training service instance
_training_service: Optional[TrainingService] = None

# Active worker polling tasks
_worker_polling_tasks: dict = {}

router = APIRouter(prefix="/api/training", tags=["training"])


# ============= Pydantic Schemas =============


class OllamaModelResponse(BaseModel):
    name: str
    model: str
    size: int
    size_gb: float
    family: str
    parameter_size: str
    quantization_level: str
    modified_at: Optional[str] = None


class OllamaStatusResponse(BaseModel):
    status: str
    version: Optional[str] = None
    url: str
    error: Optional[str] = None
    models: List[OllamaModelResponse] = []
    model_count: int = 0
    total_size_gb: float = 0.0
    running_models: List[dict] = []
    running_count: int = 0


class TrainingSessionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    base_model: str = Field(..., min_length=1, max_length=100)
    training_type: TrainingType = TrainingType.FINE_TUNE
    training_backend: str = Field(
        default="ollama_modelfile", description="Training backend: ollama_modelfile or unsloth"
    )
    worker_id: Optional[str] = Field(default=None, description="Training worker ID")
    total_epochs: int = Field(default=1, ge=1, le=100)
    hyperparameters: dict = Field(default_factory=dict)
    ollama_service_id: Optional[str] = None
    # For incremental training: path to existing LoRA adapter on the worker
    base_adapter_path: Optional[str] = Field(
        default=None, description="Path to existing LoRA adapter for incremental training"
    )


class TrainingSessionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    total_epochs: Optional[int] = Field(None, ge=1, le=100)
    hyperparameters: Optional[dict] = None


class TrainingSessionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    base_model: str
    output_model: Optional[str]
    training_type: str
    training_backend: str
    worker_id: Optional[str]
    status: str
    error_message: Optional[str]
    current_epoch: int
    total_epochs: int
    current_step: int
    total_steps: int
    progress_percent: float
    loss: Optional[float]
    learning_rate: Optional[float]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_completion: Optional[datetime]
    gpu_memory_used: Optional[float]
    cpu_usage: Optional[float]
    dataset_size: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TrainingPromptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: PromptCategory = PromptCategory.GENERAL
    difficulty: PromptDifficulty = PromptDifficulty.BASIC
    format: PromptFormat = PromptFormat.CHAT
    system_prompt: Optional[str] = None
    user_input: str
    # Tool calling support
    tool_call: Optional[dict] = Field(
        default=None, description="Expected tool call: {'name': 'tool_name', 'arguments': {...}}"
    )
    tool_response: Optional[dict] = Field(default=None, description="Example tool response (realistic mock data)")
    assistant_response: Optional[str] = Field(
        default=None, description="Final assistant response after processing tool results"
    )
    # DEPRECATED - use assistant_response instead
    expected_output: str = Field(default="", description="DEPRECATED: use assistant_response instead")
    tags: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None


class TrainingPromptUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[PromptCategory] = None
    difficulty: Optional[PromptDifficulty] = None
    system_prompt: Optional[str] = None
    user_input: Optional[str] = None
    # Tool calling support
    tool_call: Optional[dict] = Field(default=None, description="Expected tool call")
    tool_response: Optional[dict] = Field(default=None, description="Example tool response")
    assistant_response: Optional[str] = Field(default=None, description="Final assistant response")
    expected_output: Optional[str] = None
    tags: Optional[List[str]] = None
    enabled: Optional[bool] = None


class TrainingPromptResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    category: str
    difficulty: str
    source: str
    format: str
    system_prompt: Optional[str]
    user_input: str
    # Tool calling fields
    tool_call: Optional[dict] = None
    tool_response: Optional[dict] = None
    assistant_response: Optional[str] = None
    expected_output: str
    tags: List[str]
    is_validated: bool
    validation_score: Optional[float]
    times_used: int
    enabled: bool
    session_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TrainingStatsResponse(BaseModel):
    total_sessions: int
    active_sessions: int
    completed_sessions: int
    failed_sessions: int
    total_prompts: int
    validated_prompts: int
    prompts_by_category: dict
    recent_sessions: List[TrainingSessionResponse]


# ============= Ollama Endpoints =============


@router.get("/ollama/status", response_model=OllamaStatusResponse)
async def get_ollama_status(service_id: Optional[str] = None, session: AsyncSession = Depends(get_db_session)):
    """Get Ollama server status and available models."""
    ollama = await get_ollama_service(session, service_id)
    if not ollama:
        return OllamaStatusResponse(
            status="not_configured", url="", error="No Ollama service configured. Add an Ollama service in Settings."
        )

    health = await ollama.health_check()
    response = OllamaStatusResponse(
        status=health.get("status", "unknown"),
        version=health.get("version"),
        url=health.get("url", ""),
        error=health.get("error"),
    )

    if health.get("status") == "healthy":
        try:
            models = await ollama.list_models()
            response.models = [
                OllamaModelResponse(
                    name=m.name,
                    model=m.model,
                    size=m.size,
                    size_gb=m.size_gb,
                    family=m.family,
                    parameter_size=m.parameter_size,
                    quantization_level=m.quantization_level,
                    modified_at=m.modified_at,
                )
                for m in models
            ]
            response.model_count = len(models)
            response.total_size_gb = sum(m.size_gb for m in models)

            running = await ollama.get_running_models()
            response.running_models = running
            response.running_count = len(running)
        except Exception as e:
            response.error = str(e)

    return response


@router.get("/ollama/models")
async def list_ollama_models(service_id: Optional[str] = None, session: AsyncSession = Depends(get_db_session)):
    """List all available Ollama models."""
    ollama = await get_ollama_service(session, service_id)
    if not ollama:
        raise HTTPException(status_code=404, detail="No Ollama service configured")

    try:
        models = await ollama.list_models()
        return {"models": [m.to_dict() for m in models], "total": len(models)}
    except OllamaConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except OllamaError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/ollama/models/{model_name}")
async def get_ollama_model_info(
    model_name: str, service_id: Optional[str] = None, session: AsyncSession = Depends(get_db_session)
):
    """Get detailed information about a specific model."""
    ollama = await get_ollama_service(session, service_id)
    if not ollama:
        raise HTTPException(status_code=404, detail="No Ollama service configured")

    try:
        info = await ollama.get_model_info(model_name)
        return info
    except OllamaError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/ollama/models/{model_name}")
async def delete_ollama_model(
    model_name: str, service_id: Optional[str] = None, session: AsyncSession = Depends(get_db_session)
):
    """Delete an Ollama model."""
    ollama = await get_ollama_service(session, service_id)
    if not ollama:
        raise HTTPException(status_code=404, detail="No Ollama service configured")

    try:
        success = await ollama.delete_model(model_name)
        if success:
            return {"message": f"Model {model_name} deleted successfully"}
        raise HTTPException(status_code=400, detail="Failed to delete model")
    except OllamaError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/ollama/models/{model_name}/load")
async def load_ollama_model(
    model_name: str, service_id: Optional[str] = None, session: AsyncSession = Depends(get_db_session)
):
    """Load an Ollama model into memory (warm it up)."""
    ollama = await get_ollama_service(session, service_id)
    if not ollama:
        raise HTTPException(status_code=404, detail="No Ollama service configured")

    try:
        success = await ollama.load_model(model_name)
        if success:
            return {"message": f"Model {model_name} loaded successfully", "loaded": True}
        raise HTTPException(status_code=400, detail="Failed to load model")
    except OllamaError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/ollama/models/{model_name}/unload")
async def unload_ollama_model(
    model_name: str, service_id: Optional[str] = None, session: AsyncSession = Depends(get_db_session)
):
    """Unload an Ollama model from memory."""
    ollama = await get_ollama_service(session, service_id)
    if not ollama:
        raise HTTPException(status_code=404, detail="No Ollama service configured")

    try:
        success = await ollama.unload_model(model_name)
        if success:
            return {"message": f"Model {model_name} unloaded successfully", "loaded": False}
        raise HTTPException(status_code=400, detail="Failed to unload model")
    except OllamaError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============= Training Session Endpoints =============


@router.get("/sessions", response_model=List[TrainingSessionResponse])
async def list_training_sessions(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
):
    """List all training sessions."""
    query = select(TrainingSession)

    if status:
        query = query.where(TrainingSession.status == status)

    query = query.order_by(TrainingSession.created_at.desc()).offset(skip).limit(limit)

    result = await session.execute(query)
    sessions = list(result.scalars().all())
    return sessions


@router.post("/sessions", response_model=TrainingSessionResponse)
async def create_training_session(data: TrainingSessionCreate, session: AsyncSession = Depends(get_db_session)):
    """Create a new training session."""
    # Session starts with 0 prompts - user must add them
    # Store base_adapter_path in hyperparameters for incremental training
    hyperparams = data.hyperparameters.copy() if data.hyperparameters else {}
    if data.base_adapter_path:
        hyperparams["base_adapter_path"] = data.base_adapter_path

    training_session = TrainingSession(
        id=str(uuid4()),
        name=data.name,
        description=data.description,
        base_model=data.base_model,
        training_type=data.training_type,
        training_backend=data.training_backend,
        worker_id=data.worker_id,
        total_epochs=data.total_epochs,
        hyperparameters=hyperparams,
        ollama_service_id=data.ollama_service_id,
        dataset_size=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    session.add(training_session)
    await session.commit()
    await session.refresh(training_session)

    return training_session


@router.get("/sessions/{session_id}", response_model=TrainingSessionResponse)
async def get_training_session(session_id: str, session: AsyncSession = Depends(get_db_session)):
    """Get a specific training session."""
    result = await session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
    training_session = result.scalar_one_or_none()

    if not training_session:
        raise HTTPException(status_code=404, detail="Training session not found")

    return training_session


@router.get("/sessions/{session_id}/summary")
async def get_session_summary(session_id: str, session: AsyncSession = Depends(get_db_session)):
    """Get comprehensive summary and metrics for a training session.

    Returns detailed information including:
    - Basic session info (name, status, models)
    - Timing (duration, start/end times)
    - Progress (epochs, steps, completion %)
    - Final metrics (loss, learning rate)
    - Metrics analysis (initial vs final loss, trend, improvement %)
    - Overall assessment with health indicator and icon
    """
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(TrainingSession).options(selectinload(TrainingSession.prompts)).where(TrainingSession.id == session_id)
    )
    training_session = result.scalar_one_or_none()

    if not training_session:
        raise HTTPException(status_code=404, detail="Training session not found")

    # Generate summary
    summary = training_session.generate_summary()

    # Add prompts info
    summary["prompts_count"] = len(training_session.prompts)
    summary["prompts"] = [
        {
            "id": p.id,
            "name": p.name,
            "category": p.category.value if hasattr(p.category, "value") else p.category,
        }
        for p in training_session.prompts[:10]  # Limit to first 10
    ]

    # Add hyperparameters
    summary["hyperparameters"] = training_session.hyperparameters

    # Add loss history for charting (only loss values with steps)
    if training_session.metrics_history:
        summary["loss_history"] = [
            {"step": m.get("step"), "loss": m.get("loss")}
            for m in training_session.metrics_history
            if m.get("loss") is not None and m.get("step") is not None
        ]
    else:
        summary["loss_history"] = []

    return summary


@router.get("/sessions/{session_id}/logs")
async def get_session_logs(session_id: str, session: AsyncSession = Depends(get_db_session)):
    """Get training logs for a session.

    For active sessions, fetches logs from the worker.
    For completed sessions, returns stored logs from the database.
    """
    result = await session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
    training_session = result.scalar_one_or_none()

    if not training_session:
        raise HTTPException(status_code=404, detail="Training session not found")

    # If session is completed and has stored logs, return them
    if training_session.training_logs and training_session.status in [
        TrainingStatus.COMPLETED,
        TrainingStatus.FAILED,
        TrainingStatus.CANCELLED,
    ]:
        return {"session_id": session_id, "logs": training_session.training_logs, "source": "stored"}

    # Try to fetch logs from worker for active sessions
    if training_session.worker_id:
        from src.models import TrainingWorker

        worker_result = await session.execute(
            select(TrainingWorker).where(TrainingWorker.id == training_session.worker_id)
        )
        worker = worker_result.scalar_one_or_none()

        if worker and worker.url:
            import httpx

            try:
                # Get the job_id from hyperparameters if stored there
                job_id = training_session.hyperparameters.get("job_id")
                if job_id:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.get(f"{worker.url}/api/logs/job/{job_id}")
                        if response.status_code == 200:
                            data = response.json()
                            logs = "\n".join(data.get("logs", []))
                            return {"session_id": session_id, "logs": logs, "source": "worker"}

                # Fallback to recent logs
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(f"{worker.url}/api/logs/recent?count=500")
                    if response.status_code == 200:
                        data = response.json()
                        logs = "\n".join(
                            [
                                f"[{log.get('timestamp', '')}] [{log.get('level', '')}] {log.get('message', '')}"
                                for log in data
                            ]
                        )
                        return {"session_id": session_id, "logs": logs, "source": "worker_recent"}
            except Exception as e:
                logger.warning(f"Failed to fetch logs from worker: {e}")

    return {
        "session_id": session_id,
        "logs": training_session.training_logs or "Aucun log disponible",
        "source": "none",
    }


@router.patch("/sessions/{session_id}", response_model=TrainingSessionResponse)
async def update_training_session(
    session_id: str, data: TrainingSessionUpdate, session: AsyncSession = Depends(get_db_session)
):
    """Update a training session."""
    result = await session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
    training_session = result.scalar_one_or_none()

    if not training_session:
        raise HTTPException(status_code=404, detail="Training session not found")

    if training_session.status in [TrainingStatus.RUNNING, TrainingStatus.PREPARING]:
        raise HTTPException(status_code=400, detail="Cannot update a running training session")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(training_session, key, value)

    training_session.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(training_session)

    return training_session


@router.delete("/sessions/{session_id}")
async def delete_training_session(session_id: str, session: AsyncSession = Depends(get_db_session)):
    """Delete a training session."""
    result = await session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
    training_session = result.scalar_one_or_none()

    if not training_session:
        raise HTTPException(status_code=404, detail="Training session not found")

    if training_session.status in [TrainingStatus.RUNNING, TrainingStatus.PREPARING]:
        raise HTTPException(status_code=400, detail="Cannot delete a running training session. Cancel it first.")

    await session.delete(training_session)
    await session.commit()

    return {"message": "Training session deleted"}


async def run_ollama_training_background(
    session_id: str, prompts_data: List[dict], config: OllamaModelfileConfig, ollama_url: str
):
    """Background task to create Ollama model via Modelfile."""
    global _training_service
    from loguru import logger

    if not _training_service:
        _training_service = TrainingService(ollama_url=ollama_url)
    else:
        _training_service.ollama_url = ollama_url

    async def update_progress(progress: dict):
        """Update session progress in database."""
        async with async_session_maker() as db_session:
            result = await db_session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
            training_session = result.scalar_one_or_none()
            if training_session:
                training_session.current_step = progress.get("step", 0)
                training_session.total_steps = progress.get("total_steps", 3)
                training_session.progress_percent = progress.get("progress_percent", 0)
                training_session.error_message = progress.get("message")  # Use for status updates
                training_session.updated_at = datetime.utcnow()
                await db_session.commit()

    try:
        # Update status to running
        async with async_session_maker() as db_session:
            result = await db_session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
            training_session = result.scalar_one_or_none()
            if training_session:
                training_session.status = TrainingStatus.RUNNING
                training_session.updated_at = datetime.utcnow()
                await db_session.commit()

        # Create Ollama model
        result = await _training_service.create_ollama_model(
            prompts=prompts_data, config=config, progress_callback=update_progress
        )

        # Update final status
        async with async_session_maker() as db_session:
            result_db = await db_session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
            training_session = result_db.scalar_one_or_none()
            if training_session:
                if result.get("success"):
                    training_session.status = TrainingStatus.COMPLETED
                    training_session.progress_percent = 100.0
                    training_session.output_model = config.output_model_name
                    training_session.error_message = None  # Clear any status messages
                else:
                    training_session.status = TrainingStatus.FAILED
                    training_session.error_message = result.get("error", "Unknown error")
                training_session.completed_at = datetime.utcnow()
                training_session.updated_at = datetime.utcnow()
                await db_session.commit()

        logger.info(f"Ollama training completed for session {session_id}: {result}")

    except Exception as e:
        logger.error(f"Ollama training failed for session {session_id}: {e}")
        async with async_session_maker() as db_session:
            result = await db_session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
            training_session = result.scalar_one_or_none()
            if training_session:
                training_session.status = TrainingStatus.FAILED
                training_session.error_message = str(e)
                training_session.completed_at = datetime.utcnow()
                training_session.updated_at = datetime.utcnow()
                await db_session.commit()


async def run_training_background(session_id: str, prompts_data: List[dict], config: TrainingConfig):
    """Background task to run the actual Unsloth fine-tuning (requires GPU)."""
    global _training_service
    from loguru import logger

    if not _training_service:
        _training_service = TrainingService()

    async def update_progress(progress: dict):
        """Update session progress in database."""
        async with async_session_maker() as db_session:
            result = await db_session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
            training_session = result.scalar_one_or_none()
            if training_session:
                training_session.current_step = progress.get("step", 0)
                training_session.total_steps = progress.get("total_steps", 0)
                training_session.progress_percent = progress.get("progress_percent", 0)
                if "loss" in progress:
                    training_session.loss = progress["loss"]
                training_session.updated_at = datetime.utcnow()
                await db_session.commit()

    try:
        # Update status to running
        async with async_session_maker() as db_session:
            result = await db_session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
            training_session = result.scalar_one_or_none()
            if training_session:
                training_session.status = TrainingStatus.RUNNING
                training_session.updated_at = datetime.utcnow()
                await db_session.commit()

        # Run training
        result = await _training_service.start_training(
            prompts=prompts_data, config=config, progress_callback=lambda p: asyncio.create_task(update_progress(p))
        )

        # Update final status
        async with async_session_maker() as db_session:
            result_db = await db_session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
            training_session = result_db.scalar_one_or_none()
            if training_session:
                if result.get("success"):
                    training_session.status = TrainingStatus.COMPLETED
                    training_session.progress_percent = 100.0
                    training_session.output_model = config.output_model_name
                    if "training_loss" in result:
                        training_session.loss = result["training_loss"]
                else:
                    training_session.status = TrainingStatus.FAILED
                    training_session.error_message = result.get("error", "Unknown error")
                training_session.completed_at = datetime.utcnow()
                training_session.updated_at = datetime.utcnow()
                await db_session.commit()

        logger.info(f"Training completed for session {session_id}: {result}")

    except Exception as e:
        logger.error(f"Training failed for session {session_id}: {e}")
        async with async_session_maker() as db_session:
            result = await db_session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
            training_session = result.scalar_one_or_none()
            if training_session:
                training_session.status = TrainingStatus.FAILED
                training_session.error_message = str(e)
                training_session.completed_at = datetime.utcnow()
                training_session.updated_at = datetime.utcnow()
                await db_session.commit()


async def fetch_and_save_logs(session_id: str, job_id: str, worker_client: WorkerClient) -> None:
    """Fetch logs from worker and save them to the database."""
    from loguru import logger

    try:
        # Fetch logs from worker - get all logs (tail=10000 for maximum)
        logs_data = await worker_client.get_job_logs(job_id, tail=10000)

        if logs_data and logs_data.get("logs"):
            # Format logs as a single string
            logs_list = logs_data.get("logs", [])
            if isinstance(logs_list, list):
                # Format each log entry with timestamp and level
                formatted_logs = []
                for log in logs_list:
                    if isinstance(log, dict):
                        timestamp = log.get("timestamp", "")
                        level = log.get("level", "INFO")
                        message = log.get("message", str(log))
                        formatted_logs.append(f"[{timestamp}] [{level}] {message}")
                    else:
                        formatted_logs.append(str(log))
                logs_text = "\n".join(formatted_logs)
            else:
                logs_text = str(logs_list)

            # Save logs to database
            async with async_session_maker() as db_session:
                result = await db_session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
                training_session = result.scalar_one_or_none()
                if training_session:
                    training_session.training_logs = logs_text
                    training_session.updated_at = datetime.utcnow()
                    await db_session.commit()
                    log_count = len(formatted_logs) if isinstance(logs_list, list) else 1
                    logger.info(f"Saved {log_count} log entries to session {session_id}")
        else:
            logger.warning(f"No logs found for job {job_id}")
    except Exception as e:
        logger.error(f"Failed to fetch and save logs for session {session_id}: {e}")


async def poll_worker_status(session_id: str, job_id: str, worker_client: WorkerClient):
    """Background task to poll training worker status and update database."""
    from loguru import logger

    logger.info(f"Starting worker polling for session {session_id}, job {job_id}")

    try:
        while True:
            await asyncio.sleep(2)  # Poll every 2 seconds for more responsive updates

            # Get status from worker
            job_status = await worker_client.get_job_status(job_id)

            if not job_status:
                logger.warning(f"Could not get status for job {job_id}")
                continue

            # Update database
            async with async_session_maker() as db_session:
                result = await db_session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
                training_session = result.scalar_one_or_none()

                if not training_session:
                    logger.error(f"Session {session_id} not found in database")
                    break

                # Map worker status to our status
                worker_status = job_status.status.lower()
                update_type = "progress"

                if worker_status in ["preparing", "downloading"]:
                    training_session.status = TrainingStatus.PREPARING
                elif worker_status == "training":
                    training_session.status = TrainingStatus.RUNNING
                elif worker_status == "exporting":
                    training_session.status = TrainingStatus.RUNNING
                elif worker_status == "importing":
                    training_session.status = TrainingStatus.RUNNING
                elif worker_status == "completed":
                    training_session.status = TrainingStatus.COMPLETED
                    training_session.completed_at = datetime.utcnow()
                    training_session.progress_percent = 100.0
                    update_type = "completed"
                    if job_status.output_path:
                        training_session.output_model = job_status.output_path
                elif worker_status in ["failed", "error"]:
                    training_session.status = TrainingStatus.FAILED
                    training_session.error_message = job_status.error or "Training failed on worker"
                    training_session.completed_at = datetime.utcnow()
                    update_type = "failed"
                elif worker_status == "cancelled":
                    training_session.status = TrainingStatus.CANCELLED
                    training_session.completed_at = datetime.utcnow()
                    update_type = "cancelled"

                # Update progress metrics
                training_session.current_step = job_status.current_step
                training_session.total_steps = job_status.total_steps
                training_session.current_epoch = job_status.current_epoch
                training_session.progress_percent = job_status.progress_percent
                if job_status.loss is not None:
                    training_session.loss = job_status.loss
                if job_status.learning_rate is not None:
                    training_session.learning_rate = job_status.learning_rate

                # Add to metrics history for summary analysis
                if training_session.metrics_history is None:
                    training_session.metrics_history = []

                # If worker has more loss_history data than our metrics_history, sync from worker
                if job_status.loss_history and len(job_status.loss_history) > len(training_session.metrics_history):
                    worker_points = len(job_status.loss_history)
                    session_points = len(training_session.metrics_history)
                    logger.info(
                        f"Syncing metrics_history from worker loss_history "
                        f"({worker_points} points, was {session_points})"
                    )
                    training_session.metrics_history = []
                    for i, loss_val in enumerate(job_status.loss_history):
                        training_session.metrics_history.append(
                            {
                                "timestamp": datetime.utcnow().isoformat(),
                                "step": i + 1,
                                "epoch": (i * job_status.total_epochs) // len(job_status.loss_history) + 1
                                if job_status.loss_history
                                else 0,
                                "loss": loss_val,
                                "learning_rate": job_status.learning_rate,
                            }
                        )
                elif job_status.loss is not None:
                    # Only add if we have a new step (avoid duplicates)
                    last_step = (
                        training_session.metrics_history[-1].get("step") if training_session.metrics_history else -1
                    )
                    if job_status.current_step > last_step:
                        training_session.metrics_history.append(
                            {
                                "timestamp": datetime.utcnow().isoformat(),
                                "step": job_status.current_step,
                                "epoch": job_status.current_epoch,
                                "loss": job_status.loss,
                                "learning_rate": job_status.learning_rate,
                            }
                        )
                        # Keep last 1000 entries
                        if len(training_session.metrics_history) > 1000:
                            training_session.metrics_history = training_session.metrics_history[-1000:]

                training_session.updated_at = datetime.utcnow()
                await db_session.commit()

                # Calculate metrics from history for WebSocket broadcast
                loss_history = []
                best_loss = job_status.loss
                best_loss_step = job_status.current_step
                best_loss_epoch = job_status.current_epoch
                loss_trend = "stable"
                loss_improvement_rate = 0.0

                if training_session.metrics_history:
                    loss_history = [
                        m.get("loss") for m in training_session.metrics_history if m.get("loss") is not None
                    ]

                    if loss_history:
                        # Find best (minimum) loss
                        best_loss = min(loss_history)
                        for m in training_session.metrics_history:
                            if m.get("loss") == best_loss:
                                best_loss_step = m.get("step", 0)
                                best_loss_epoch = m.get("epoch", 0)
                                break

                        # Calculate loss trend (use more values and lower threshold for fine-tuning)
                        if len(loss_history) >= 3:
                            # Use up to last 10 values for better trend detection
                            recent = loss_history[-10:] if len(loss_history) >= 10 else loss_history
                            first_half = recent[: len(recent) // 2]
                            second_half = recent[len(recent) // 2 :]

                            if first_half and second_half:
                                avg_first = sum(first_half) / len(first_half)
                                avg_second = sum(second_half) / len(second_half)

                                # Use 2% threshold for fine-tuning (more sensitive)
                                if avg_second < avg_first * 0.98:
                                    loss_trend = "decreasing"
                                elif avg_second > avg_first * 1.02:
                                    loss_trend = "increasing"
                                else:
                                    loss_trend = "stable"

                        # Calculate improvement rate
                        if len(loss_history) >= 2 and loss_history[0] > 0:
                            loss_improvement_rate = (loss_history[0] - loss_history[-1]) / loss_history[0] * 100

                # Determine training health based on trend
                training_health = "good"
                health_message = f"Phase: {worker_status}"
                if loss_trend == "decreasing":
                    training_health = "excellent"
                    health_message = "Loss decreasing - training well"
                elif loss_trend == "increasing":
                    training_health = "warning"
                    health_message = "Loss increasing - may need adjustment"

                # Fetch GPU metrics from worker
                gpu_data = None
                try:
                    gpu_metrics = await worker_client.get_gpu_metrics()
                    if gpu_metrics and gpu_metrics.get("gpu_id") is not None:
                        gpu_data = {
                            "gpu_id": gpu_metrics.get("gpu_id", 0),
                            "gpu_name": gpu_metrics.get("gpu_name", ""),
                            "memory_used_mb": gpu_metrics.get("memory_used_mb", 0),
                            "memory_total_mb": gpu_metrics.get("memory_total_mb", 0),
                            "memory_percent": gpu_metrics.get("memory_percent", 0),
                            "utilization_percent": gpu_metrics.get("utilization_percent", 0),
                            "temperature_celsius": gpu_metrics.get("temperature_celsius"),
                            "power_watts": gpu_metrics.get("power_watts"),
                        }
                except Exception as e:
                    logger.debug(f"Failed to fetch GPU metrics: {e}")

                # Broadcast to WebSocket clients
                ws_data = {
                    "progress": {
                        "current_epoch": job_status.current_epoch,
                        "total_epochs": job_status.total_epochs,
                        "current_step": job_status.current_step,
                        "total_steps": job_status.total_steps,
                        "progress_percent": job_status.progress_percent,
                        "samples_processed": job_status.current_step,
                        "tokens_processed": 0,
                    },
                    "performance": {
                        "loss": job_status.loss,
                        "loss_history": loss_history[-100:],  # Last 100 values for chart
                        "perplexity": None,
                        "gradient_norm": job_status.gradient_norm,
                        "learning_rate": job_status.learning_rate,
                        "accuracy": None,
                        "entropy": None,
                    },
                    "gpu": gpu_data,
                    "time": {
                        "elapsed_seconds": (datetime.utcnow() - training_session.started_at).total_seconds()
                        if training_session.started_at
                        else 0,
                        "eta_seconds": job_status.eta_seconds,
                        "samples_per_second": job_status.samples_per_second,
                        "tokens_per_second": job_status.samples_per_second
                        * 512,  # Estimate: ~512 tokens per sample average
                        "step_duration_ms": (1000 / job_status.samples_per_second)
                        if job_status.samples_per_second > 0
                        else 0,
                    },
                    "quality": {
                        "loss_trend": loss_trend,
                        "loss_improvement_rate": loss_improvement_rate,
                        "training_health": training_health,
                        "health_message": health_message,
                        "overfitting_risk": "low",
                    },
                    "convergence": {
                        "best_loss": best_loss,
                        "best_loss_epoch": best_loss_epoch,
                        "best_loss_step": best_loss_step,
                        "epochs_without_improvement": 0,
                        "should_early_stop": False,
                        "early_stop_reason": None,
                    },
                    # Add current phase for UI display
                    "phase": worker_status,
                }

                await connection_manager.broadcast_to_frontend(
                    {
                        "type": "session_update",
                        "session_id": session_id,
                        "update_type": update_type,
                        "data": ws_data,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

                logger.debug(
                    f"Session {session_id}: {worker_status} - "
                    f"Step {job_status.current_step}/{job_status.total_steps} - "
                    f"{job_status.progress_percent:.1f}%"
                )

                # Stop polling if job is done
                if worker_status in ["completed", "failed", "error", "cancelled"]:
                    logger.info(f"Training job {job_id} finished with status: {worker_status}")
                    # Save logs to database before exiting
                    await fetch_and_save_logs(session_id, job_id, worker_client)
                    break

    except asyncio.CancelledError:
        logger.info(f"Polling cancelled for session {session_id}")
        # Try to save logs even when cancelled
        try:
            await fetch_and_save_logs(session_id, job_id, worker_client)
        except Exception as e:
            logger.warning(f"Failed to save logs on cancel: {e}")
    except Exception as e:
        logger.error(f"Error polling worker for session {session_id}: {e}")
        # Try to save logs before marking as failed
        try:
            await fetch_and_save_logs(session_id, job_id, worker_client)
        except Exception as log_err:
            logger.warning(f"Failed to save logs on error: {log_err}")
        # Mark session as failed on polling error
        async with async_session_maker() as db_session:
            result = await db_session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
            training_session = result.scalar_one_or_none()
            if training_session and training_session.status in [TrainingStatus.RUNNING, TrainingStatus.PREPARING]:
                training_session.status = TrainingStatus.FAILED
                training_session.error_message = f"Lost connection to training worker: {e}"
                training_session.completed_at = datetime.utcnow()
                training_session.updated_at = datetime.utcnow()
                await db_session.commit()
    finally:
        # Remove from active polling tasks
        if session_id in _worker_polling_tasks:
            del _worker_polling_tasks[session_id]


async def start_worker_training(
    session_id: str,
    prompts_data: List[dict],
    base_model: str,
    output_model_name: str,
    ollama_url: str,
    hyperparams: dict,
    total_epochs: int,
):
    """Start training on remote GPU worker and begin polling."""
    from loguru import logger

    worker_client = get_worker_client()

    # Update session to preparing
    async with async_session_maker() as db_session:
        result = await db_session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
        training_session = result.scalar_one_or_none()
        if training_session:
            training_session.status = TrainingStatus.PREPARING
            training_session.error_message = "Connecting to training worker..."
            training_session.updated_at = datetime.utcnow()
            await db_session.commit()

    # Start training on worker
    result = await worker_client.start_training(
        session_id=session_id,
        prompts=prompts_data,
        base_model=base_model,
        output_model_name=output_model_name,
        ollama_url=ollama_url,
        num_epochs=total_epochs,
        batch_size=hyperparams.get("batch_size", 2),
        learning_rate=hyperparams.get("learning_rate", 2e-4),
        max_seq_length=hyperparams.get("max_seq_length", 2048),
        lora_r=hyperparams.get("lora_r", 16),
        lora_alpha=hyperparams.get("lora_alpha", 16),
        quantization_method=hyperparams.get("quantization_method", "q4_k_m"),
        overwrite_existing=hyperparams.get("overwrite_existing", False),
        base_adapter_path=hyperparams.get("base_adapter_path"),  # For incremental training
    )

    if not result.get("success"):
        # Mark as failed
        async with async_session_maker() as db_session:
            result_db = await db_session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
            training_session = result_db.scalar_one_or_none()
            if training_session:
                training_session.status = TrainingStatus.FAILED
                training_session.error_message = result.get("error", "Failed to start training on worker")
                training_session.completed_at = datetime.utcnow()
                training_session.updated_at = datetime.utcnow()
                await db_session.commit()
        logger.error(f"Failed to start training on worker: {result.get('error')}")
        return

    job_id = result.get("job_id")
    logger.info(f"Training job started on worker: {job_id}")

    # Update session with job info
    async with async_session_maker() as db_session:
        result_db = await db_session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
        training_session = result_db.scalar_one_or_none()
        if training_session:
            training_session.status = TrainingStatus.RUNNING
            training_session.error_message = None
            training_session.updated_at = datetime.utcnow()
            await db_session.commit()

    # Start polling task
    polling_task = asyncio.create_task(poll_worker_status(session_id, job_id, worker_client))
    _worker_polling_tasks[session_id] = polling_task


@router.post("/sessions/{session_id}/start")
async def start_training_session(
    session_id: str, background_tasks: BackgroundTasks = None, session: AsyncSession = Depends(get_db_session)
):
    """Start a training session.

    The backend is determined by the session's training_backend field:
    - ollama_modelfile: Creates an Ollama model with embedded examples (no GPU needed)
    - unsloth / gpu_worker: Real fine-tuning with Unsloth (GPU required on worker)
    """
    result = await session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
    training_session = result.scalar_one_or_none()

    if not training_session:
        raise HTTPException(status_code=404, detail="Training session not found")

    if training_session.status != TrainingStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Cannot start session with status {training_session.status}")

    # Get prompts for this session (many-to-many via association table)
    from sqlalchemy.orm import selectinload

    # Reload session with prompts
    result_with_prompts = await session.execute(
        select(TrainingSession).options(selectinload(TrainingSession.prompts)).where(TrainingSession.id == session_id)
    )
    training_session = result_with_prompts.scalar_one_or_none()
    prompts = training_session.prompts if training_session else []

    if not prompts:
        raise HTTPException(status_code=400, detail="No prompts associated with this session")

    # Prepare prompts data
    prompts_data = [
        {"system_prompt": p.system_prompt, "user_input": p.user_input, "expected_output": p.expected_output}
        for p in prompts
    ]

    # Mark prompts as used (increment usage counter)
    for prompt in prompts:
        prompt.mark_used()
    await session.commit()

    # Get Ollama URL from configured service
    ollama_url = "http://localhost:11434"
    if training_session.ollama_service_id:
        service_result = await session.execute(
            select(ServiceConfig).where(ServiceConfig.id == training_session.ollama_service_id)
        )
        service = service_result.scalar_one_or_none()
        if service and service.full_url:
            ollama_url = service.full_url.rstrip("/")
    else:
        # Try to find any Ollama service
        service_result = await session.execute(
            select(ServiceConfig)
            .where(ServiceConfig.service_type == ServiceType.OLLAMA, ServiceConfig.enabled == True)
            .limit(1)
        )
        service = service_result.scalar_one_or_none()
        if service and service.full_url:
            ollama_url = service.full_url.rstrip("/")

    hyperparams = training_session.hyperparameters or {}

    # Use backend from session, not query parameter
    backend = training_session.training_backend or "ollama_modelfile"

    # Auto-detect: if base_model is a HuggingFace model (contains '/'),
    # force gpu_worker backend because ollama_modelfile can't use HF models
    base_model = training_session.base_model
    if "/" in base_model and backend == "ollama_modelfile":
        logger.info(f"Auto-switching to gpu_worker backend for HuggingFace model: {base_model}")
        backend = "gpu_worker"

    if backend == "ollama_modelfile":
        # Ollama Modelfile approach - no GPU needed
        config = OllamaModelfileConfig(
            base_model=training_session.base_model,
            output_model_name=f"mcparr-{training_session.name.lower().replace(' ', '-')}",
            temperature=hyperparams.get("temperature", 0.7),
            top_p=hyperparams.get("top_p", 0.9),
            top_k=hyperparams.get("top_k", 40),
            num_ctx=hyperparams.get("num_ctx", 4096),
        )

        # Update session to preparing
        training_session.status = TrainingStatus.PREPARING
        training_session.started_at = datetime.utcnow()
        training_session.updated_at = datetime.utcnow()
        training_session.total_steps = 3  # Modelfile creation has 3 steps

        await session.commit()

        # Start Ollama training in background
        background_tasks.add_task(run_ollama_training_background, session_id, prompts_data, config, ollama_url)

        return {
            "message": "Creating Ollama model with embedded examples",
            "session_id": session_id,
            "backend": "ollama_modelfile",
            "prompts_count": len(prompts),
            "config": {
                "base_model": config.base_model,
                "output_model": config.output_model_name,
                "ollama_url": ollama_url,
            },
        }

    elif backend in ("unsloth", "gpu_worker"):
        # Unsloth fine-tuning on remote GPU worker
        settings = get_settings()

        # Check worker connectivity first
        worker_client = get_worker_client()
        worker_status = await worker_client.health_check()

        if not worker_status.online:
            raise HTTPException(
                status_code=503,
                detail=f"Training worker not available: {worker_status.error or 'Connection failed'}. "
                f"Check that the worker is running at {settings.training_worker_url}",
            )

        # Prepare model name for Unsloth (convert ollama format to unsloth)
        # e.g., "llama3.2:3b" -> "unsloth/llama-3.2-3b-instruct-bnb-4bit"
        base_model_raw = training_session.base_model.lower()

        # If already a HuggingFace model path (contains /), use as-is
        if "/" in base_model_raw:
            base_model = base_model_raw
        else:
            # Map common ollama models to unsloth models
            unsloth_model_map = {
                "llama3.2:3b": "unsloth/llama-3.2-3b-instruct-bnb-4bit",
                "llama3.2:1b": "unsloth/llama-3.2-1b-instruct-bnb-4bit",
                "llama3.1:8b": "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit",
                "mistral:7b": "unsloth/mistral-7b-instruct-v0.3-bnb-4bit",
                "qwen2.5:3b": "unsloth/Qwen2.5-3B-Instruct-bnb-4bit",
                "qwen2.5:7b": "unsloth/Qwen2.5-7B-Instruct-bnb-4bit",
            }
            base_model = unsloth_model_map.get(
                base_model_raw, hyperparams.get("unsloth_model", f"unsloth/{base_model_raw.replace(':', '-')}-bnb-4bit")
            )
        output_model_name = f"mcparr-{training_session.name.lower().replace(' ', '-')}"

        # Update session to preparing
        training_session.status = TrainingStatus.PREPARING
        training_session.started_at = datetime.utcnow()
        training_session.updated_at = datetime.utcnow()
        training_session.error_message = "Dispatching to GPU worker..."

        await session.commit()

        # Start training on remote worker (async task)
        background_tasks.add_task(
            start_worker_training,
            session_id,
            prompts_data,
            base_model,
            output_model_name,
            ollama_url,
            hyperparams,
            training_session.total_epochs,
        )

        return {
            "message": "Starting Unsloth fine-tuning on GPU worker",
            "session_id": session_id,
            "backend": "unsloth",
            "worker_url": settings.training_worker_url,
            "prompts_count": len(prompts),
            "config": {
                "base_model": base_model,
                "epochs": training_session.total_epochs,
                "output_model": output_model_name,
                "ollama_url": ollama_url,
            },
        }

    else:
        raise HTTPException(
            status_code=400, detail=f"Unknown backend: {backend}. Use 'ollama_modelfile', 'unsloth' or 'gpu_worker'"
        )


@router.post("/sessions/{session_id}/cancel")
async def cancel_training_session(session_id: str, session: AsyncSession = Depends(get_db_session)):
    """Cancel a running training session."""
    result = await session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
    training_session = result.scalar_one_or_none()

    if not training_session:
        raise HTTPException(status_code=404, detail="Training session not found")

    if training_session.status not in [TrainingStatus.RUNNING, TrainingStatus.PREPARING, TrainingStatus.PENDING]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel session with status {training_session.status}")

    training_session.cancel_training()
    training_session.updated_at = datetime.utcnow()

    await session.commit()

    # Cancel polling task if exists
    if session_id in _worker_polling_tasks:
        _worker_polling_tasks[session_id].cancel()
        del _worker_polling_tasks[session_id]

    # Also cancel on remote worker
    try:
        worker_client = get_worker_client()
        await worker_client.cancel_training()
    except Exception:
        pass  # Ignore errors cancelling on worker

    # Also cancel in local training service
    global _training_service
    if _training_service:
        _training_service.cancel_training()

    return {"message": "Training session cancelled", "session_id": session_id}


@router.post("/sessions/{session_id}/duplicate")
async def duplicate_training_session(session_id: str, session: AsyncSession = Depends(get_db_session)):
    """Duplicate a training session with all its prompts."""
    from sqlalchemy.orm import selectinload

    # Get original session with prompts
    result = await session.execute(
        select(TrainingSession).options(selectinload(TrainingSession.prompts)).where(TrainingSession.id == session_id)
    )
    original_session = result.scalar_one_or_none()

    if not original_session:
        raise HTTPException(status_code=404, detail="Training session not found")

    # Find the next version number for naming
    base_name = original_session.name
    # Remove version suffix if present (e.g., "Test v1" -> "Test")
    import re

    match = re.match(r"(.+?)\s*v(\d+)$", base_name)
    if match:
        base_name = match.group(1).strip()

    # Find existing sessions with similar names to get next version
    similar_result = await session.execute(select(TrainingSession).where(TrainingSession.name.like(f"{base_name}%")))
    similar_sessions = similar_result.scalars().all()

    max_version = 0
    for s in similar_sessions:
        m = re.search(r"v(\d+)$", s.name)
        if m:
            max_version = max(max_version, int(m.group(1)))

    new_name = f"{base_name} v{max_version + 1}"

    # Create new session
    new_session = TrainingSession(
        name=new_name,
        description=original_session.description,
        base_model=original_session.base_model,
        training_type=original_session.training_type,
        total_epochs=original_session.total_epochs,
        hyperparameters=original_session.hyperparameters.copy() if original_session.hyperparameters else {},
        ollama_service_id=original_session.ollama_service_id,
        status=TrainingStatus.PENDING,
    )

    session.add(new_session)
    await session.flush()  # Get the new ID

    # Copy prompt associations
    for prompt in original_session.prompts:
        await session.execute(
            session_prompt_association.insert().values(
                session_id=new_session.id, prompt_id=prompt.id, added_at=datetime.utcnow()
            )
        )

    await session.commit()

    return {
        "message": "Session duplicated successfully",
        "original_session_id": session_id,
        "new_session_id": new_session.id,
        "new_name": new_name,
        "prompts_copied": len(original_session.prompts),
    }


@router.get("/requirements")
async def check_training_requirements():
    """Check if training requirements are met (GPU, libraries, etc.)."""
    global _training_service
    if not _training_service:
        _training_service = TrainingService()

    requirements = await _training_service.check_requirements()
    return requirements


@router.get("/worker/status")
async def get_worker_status():
    """Get training worker status and GPU information."""
    settings = get_settings()
    worker_client = get_worker_client()

    # Get basic health
    health = await worker_client.health_check()

    if not health.online:
        return {
            "online": False,
            "worker_url": settings.training_worker_url,
            "error": health.error,
            "gpu_available": False,
        }

    # Get detailed info
    info = await worker_client.get_worker_info()
    gpu_metrics = await worker_client.get_gpu_metrics()

    return {
        "online": True,
        "worker_url": settings.training_worker_url,
        "worker_id": info.worker_id,
        "worker_name": info.worker_name,
        "status": info.status,
        "gpu_available": info.gpu_available,
        "gpu_count": info.gpu_count,
        "gpu_names": info.gpu_names,
        "current_job_id": info.current_job_id,
        "gpu_metrics": gpu_metrics,
    }


@router.get("/worker/models")
async def get_worker_models():
    """Get available base models from training worker."""
    worker_client = get_worker_client()

    # Check worker is online first
    health = await worker_client.health_check()
    if not health.online:
        raise HTTPException(status_code=503, detail=f"Training worker not available: {health.error}")

    models = await worker_client.get_available_models()
    return models


# ============= Worker Logs Endpoints =============


@router.get("/worker/logs/system")
async def get_worker_system_logs(
    tail: int = Query(default=100, le=1000, description="Number of lines to return"),
    level: Optional[str] = Query(default=None, description="Filter by log level (debug, info, warning, error)"),
):
    """Get system logs from training worker."""
    worker_client = get_worker_client()

    # Check worker is online first
    health = await worker_client.health_check()
    if not health.online:
        raise HTTPException(status_code=503, detail=f"Training worker not available: {health.error}")

    return await worker_client.get_system_logs(tail=tail, level=level)


@router.get("/worker/logs/job/{job_id}")
async def get_worker_job_logs(
    job_id: str,
    tail: int = Query(default=100, le=5000, description="Number of lines to return"),
    level: Optional[str] = Query(default=None, description="Filter by log level"),
):
    """Get logs for a specific training job from worker."""
    worker_client = get_worker_client()

    # Check worker is online first
    health = await worker_client.health_check()
    if not health.online:
        raise HTTPException(status_code=503, detail=f"Training worker not available: {health.error}")

    return await worker_client.get_job_logs(job_id=job_id, tail=tail, level=level)


@router.get("/worker/logs/jobs")
async def list_worker_job_logs():
    """List job IDs that have available logs on worker."""
    worker_client = get_worker_client()

    # Check worker is online first
    health = await worker_client.health_check()
    if not health.online:
        raise HTTPException(status_code=503, detail=f"Training worker not available: {health.error}")

    return await worker_client.get_available_job_logs()


@router.delete("/worker/logs/job/{job_id}")
async def delete_worker_job_logs(job_id: str):
    """Delete logs for a specific job on worker."""
    worker_client = get_worker_client()

    # Check worker is online first
    health = await worker_client.health_check()
    if not health.online:
        raise HTTPException(status_code=503, detail=f"Training worker not available: {health.error}")

    return await worker_client.delete_job_logs(job_id)


@router.get("/worker/logs/job/{job_id}/stream-url")
async def get_job_logs_stream_url(job_id: str):
    """Get the SSE stream URL for job logs (to be consumed directly by frontend)."""
    worker_client = get_worker_client()
    settings = get_settings()

    return {
        "stream_url": worker_client.get_job_logs_stream_url(job_id),
        "worker_url": settings.training_worker_url,
        "job_id": job_id,
    }


@router.get("/worker/logs/system/stream-url")
async def get_system_logs_stream_url():
    """Get the SSE stream URL for system logs (to be consumed directly by frontend)."""
    worker_client = get_worker_client()
    settings = get_settings()

    return {"stream_url": worker_client.get_system_logs_stream_url(), "worker_url": settings.training_worker_url}


@router.post("/sessions/{session_id}/import-ollama")
async def import_model_to_ollama(session_id: str, session: AsyncSession = Depends(get_db_session)):
    """Import a completed training session's model into Ollama."""
    result = await session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
    training_session = result.scalar_one_or_none()

    if not training_session:
        raise HTTPException(status_code=404, detail="Training session not found")

    if training_session.status != TrainingStatus.COMPLETED:
        raise HTTPException(
            status_code=400, detail=f"Cannot import model from session with status {training_session.status}"
        )

    global _training_service
    if not _training_service:
        _training_service = TrainingService()

    model_name = training_session.output_model or f"mcparr-{training_session.name.lower().replace(' ', '-')}"
    result = await _training_service.import_to_ollama(model_name)

    if result.get("success"):
        training_session.output_model = model_name
        training_session.updated_at = datetime.utcnow()
        await session.commit()

    return result


# ============= Session Prompts Management =============


class SessionPromptsUpdate(BaseModel):
    """Update prompts for a session."""

    prompt_ids: List[str] = Field(..., description="List of prompt IDs to associate with session")


@router.get("/sessions/{session_id}/prompts", response_model=List[TrainingPromptResponse])
async def get_session_prompts(session_id: str, session: AsyncSession = Depends(get_db_session)):
    """Get all prompts associated with a session."""
    # Verify session exists
    result = await session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Training session not found")

    # Get prompts for this session
    prompts_result = await session.execute(
        select(TrainingPrompt).where(TrainingPrompt.session_id == session_id).order_by(TrainingPrompt.name)
    )
    return list(prompts_result.scalars().all())


@router.put("/sessions/{session_id}/prompts")
async def update_session_prompts(
    session_id: str, data: SessionPromptsUpdate, session: AsyncSession = Depends(get_db_session)
):
    """Set prompts for a session (replaces existing associations). Many-to-many: prompts can be in multiple sessions."""
    from sqlalchemy.orm import selectinload

    # Get session with prompts loaded
    result = await session.execute(
        select(TrainingSession).options(selectinload(TrainingSession.prompts)).where(TrainingSession.id == session_id)
    )
    training_session = result.scalar_one_or_none()

    if not training_session:
        raise HTTPException(status_code=404, detail="Training session not found")

    if training_session.status != TrainingStatus.PENDING:
        raise HTTPException(status_code=400, detail="Cannot modify prompts for a session that is not pending")

    # Clear existing associations (many-to-many)
    training_session.prompts.clear()

    # Add new associations
    if data.prompt_ids:
        prompts_result = await session.execute(select(TrainingPrompt).where(TrainingPrompt.id.in_(data.prompt_ids)))
        prompts = list(prompts_result.scalars().all())

        for prompt in prompts:
            training_session.prompts.append(prompt)

        # Update session dataset_size
        training_session.dataset_size = len(prompts)
    else:
        training_session.dataset_size = 0

    training_session.updated_at = datetime.utcnow()
    await session.commit()

    return {
        "message": f"Updated session with {training_session.dataset_size} prompts",
        "session_id": session_id,
        "prompt_count": training_session.dataset_size,
    }


@router.post("/sessions/{session_id}/prompts/add")
async def add_prompts_to_session(
    session_id: str, data: SessionPromptsUpdate, session: AsyncSession = Depends(get_db_session)
):
    """Add prompts to a session (keeps existing associations). Many-to-many: prompts can be in multiple sessions."""
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(TrainingSession).options(selectinload(TrainingSession.prompts)).where(TrainingSession.id == session_id)
    )
    training_session = result.scalar_one_or_none()

    if not training_session:
        raise HTTPException(status_code=404, detail="Training session not found")

    if training_session.status != TrainingStatus.PENDING:
        raise HTTPException(status_code=400, detail="Cannot modify prompts for a session that is not pending")

    # Add new associations (many-to-many, no restriction on already assigned)
    added = 0
    if data.prompt_ids:
        # Get current prompt IDs to avoid duplicates
        current_prompt_ids = {p.id for p in training_session.prompts}

        prompts_result = await session.execute(select(TrainingPrompt).where(TrainingPrompt.id.in_(data.prompt_ids)))
        for prompt in prompts_result.scalars():
            if prompt.id not in current_prompt_ids:
                training_session.prompts.append(prompt)
                added += 1

    # Update dataset_size
    training_session.dataset_size = len(training_session.prompts)
    training_session.updated_at = datetime.utcnow()

    await session.commit()

    return {
        "message": f"Added {added} prompts to session",
        "session_id": session_id,
        "added": added,
        "total": training_session.dataset_size,
    }


@router.post("/sessions/{session_id}/prompts/remove")
async def remove_prompts_from_session(
    session_id: str, data: SessionPromptsUpdate, session: AsyncSession = Depends(get_db_session)
):
    """Remove prompts from a session (many-to-many: only removes from this session, prompt still exists)."""
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(TrainingSession).options(selectinload(TrainingSession.prompts)).where(TrainingSession.id == session_id)
    )
    training_session = result.scalar_one_or_none()

    if not training_session:
        raise HTTPException(status_code=404, detail="Training session not found")

    if training_session.status != TrainingStatus.PENDING:
        raise HTTPException(status_code=400, detail="Cannot modify prompts for a session that is not pending")

    # Remove associations from many-to-many
    removed = 0
    if data.prompt_ids:
        prompt_ids_to_remove = set(data.prompt_ids)
        prompts_to_remove = [p for p in training_session.prompts if p.id in prompt_ids_to_remove]
        for prompt in prompts_to_remove:
            training_session.prompts.remove(prompt)
            removed += 1

    # Update dataset_size
    training_session.dataset_size = len(training_session.prompts)
    training_session.updated_at = datetime.utcnow()

    await session.commit()

    return {
        "message": f"Removed {removed} prompts from session",
        "session_id": session_id,
        "removed": removed,
        "total": training_session.dataset_size,
    }


# ============= Training Prompts Endpoints =============


@router.get("/prompts", response_model=List[TrainingPromptResponse])
async def list_training_prompts(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    validated: Optional[bool] = None,
    enabled: Optional[bool] = None,
    session_id: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: Optional[int] = Query(None, ge=1),
    session: AsyncSession = Depends(get_db_session),
):
    """List training prompts with filtering. No limit by default (returns all)."""
    query = select(TrainingPrompt)
    conditions = []

    if category:
        conditions.append(TrainingPrompt.category == category)
    if difficulty:
        conditions.append(TrainingPrompt.difficulty == difficulty)
    if validated is not None:
        conditions.append(TrainingPrompt.is_validated == validated)
    if enabled is not None:
        conditions.append(TrainingPrompt.enabled == enabled)
    if session_id:
        conditions.append(TrainingPrompt.session_id == session_id)
    if search:
        conditions.append(TrainingPrompt.name.ilike(f"%{search}%") | TrainingPrompt.user_input.ilike(f"%{search}%"))

    if conditions:
        query = query.where(and_(*conditions))

    query = query.order_by(TrainingPrompt.created_at.desc()).offset(skip)
    if limit:
        query = query.limit(limit)

    result = await session.execute(query)
    prompts = list(result.scalars().all())
    return prompts


@router.post("/prompts", response_model=TrainingPromptResponse)
async def create_training_prompt(data: TrainingPromptCreate, session: AsyncSession = Depends(get_db_session)):
    """Create a new training prompt.

    For tool calling prompts:
    - tool_call: {"name": "tool_name", "arguments": {...}}
    - tool_response: Example response from the tool (realistic mock data)
    - assistant_response: Final response that synthesizes the tool result

    For regular prompts:
    - Just use user_input and assistant_response (or expected_output for backward compat)
    """
    # Build content based on format
    content = {
        "system_prompt": data.system_prompt,
        "user_input": data.user_input,
        "tool_call": data.tool_call,
        "tool_response": data.tool_response,
        "assistant_response": data.assistant_response,
        "expected_output": data.expected_output,
    }

    # Use assistant_response if provided, otherwise fall back to expected_output
    final_expected_output = data.expected_output or ""

    prompt = TrainingPrompt(
        id=str(uuid4()),
        name=data.name,
        description=data.description,
        category=data.category,
        difficulty=data.difficulty,
        source=PromptSource.MANUAL,
        format=data.format,
        content=content,
        system_prompt=data.system_prompt,
        user_input=data.user_input,
        tool_call=data.tool_call,
        tool_response=data.tool_response,
        assistant_response=data.assistant_response,
        expected_output=final_expected_output,
        tags=data.tags,
        session_id=data.session_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    session.add(prompt)
    await session.commit()
    await session.refresh(prompt)

    return prompt


@router.get("/prompts/export")
async def export_training_prompts(
    category: Optional[str] = None,
    session_id: Optional[str] = None,
    format: str = Query("json", regex="^(json|jsonl)$"),
    session: AsyncSession = Depends(get_db_session),
):
    """Export training prompts for download."""
    query = select(TrainingPrompt).where(TrainingPrompt.enabled == True)

    if category:
        query = query.where(TrainingPrompt.category == category)
    if session_id:
        query = query.where(TrainingPrompt.session_id == session_id)

    result = await session.execute(query)
    prompts = list(result.scalars().all())

    export_data = []
    for prompt in prompts:
        export_data.append(prompt.to_training_format())

    return {"format": format, "count": len(export_data), "data": export_data}


@router.get("/prompts/{prompt_id}", response_model=TrainingPromptResponse)
async def get_training_prompt(prompt_id: str, session: AsyncSession = Depends(get_db_session)):
    """Get a specific training prompt."""
    result = await session.execute(select(TrainingPrompt).where(TrainingPrompt.id == prompt_id))
    prompt = result.scalar_one_or_none()

    if not prompt:
        raise HTTPException(status_code=404, detail="Training prompt not found")

    return prompt


@router.patch("/prompts/{prompt_id}", response_model=TrainingPromptResponse)
async def update_training_prompt(
    prompt_id: str, data: TrainingPromptUpdate, session: AsyncSession = Depends(get_db_session)
):
    """Update a training prompt."""
    result = await session.execute(select(TrainingPrompt).where(TrainingPrompt.id == prompt_id))
    prompt = result.scalar_one_or_none()

    if not prompt:
        raise HTTPException(status_code=404, detail="Training prompt not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(prompt, key, value)

    # Update content if any relevant field changed
    content_fields = [
        "user_input",
        "expected_output",
        "system_prompt",
        "tool_call",
        "tool_response",
        "assistant_response",
    ]
    if any(field in update_data for field in content_fields):
        prompt.content = {
            "system_prompt": prompt.system_prompt,
            "user_input": prompt.user_input,
            "tool_call": prompt.tool_call,
            "tool_response": prompt.tool_response,
            "assistant_response": prompt.assistant_response,
            "expected_output": prompt.expected_output,
        }

    prompt.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(prompt)

    return prompt


@router.delete("/prompts/{prompt_id}")
async def delete_training_prompt(prompt_id: str, session: AsyncSession = Depends(get_db_session)):
    """Delete a training prompt."""
    result = await session.execute(select(TrainingPrompt).where(TrainingPrompt.id == prompt_id))
    prompt = result.scalar_one_or_none()

    if not prompt:
        raise HTTPException(status_code=404, detail="Training prompt not found")

    await session.delete(prompt)
    await session.commit()

    return {"message": "Training prompt deleted"}


@router.post("/prompts/{prompt_id}/validate")
async def validate_training_prompt(
    prompt_id: str,
    score: Optional[float] = Query(None, ge=0, le=1),
    validated_by: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session),
):
    """Mark a prompt as validated."""
    result = await session.execute(select(TrainingPrompt).where(TrainingPrompt.id == prompt_id))
    prompt = result.scalar_one_or_none()

    if not prompt:
        raise HTTPException(status_code=404, detail="Training prompt not found")

    prompt.validate(score=score, validated_by=validated_by)
    prompt.updated_at = datetime.utcnow()

    await session.commit()

    return {"message": "Prompt validated", "prompt_id": prompt_id}


# ============= Stats Endpoint =============


@router.get("/stats", response_model=TrainingStatsResponse)
async def get_training_stats(session: AsyncSession = Depends(get_db_session)):
    """Get training statistics."""
    # Session counts
    total_sessions = await session.execute(select(func.count(TrainingSession.id)))
    total_sessions = total_sessions.scalar() or 0

    active_sessions = await session.execute(
        select(func.count(TrainingSession.id)).where(
            TrainingSession.status.in_([TrainingStatus.RUNNING, TrainingStatus.PREPARING])
        )
    )
    active_sessions = active_sessions.scalar() or 0

    completed_sessions = await session.execute(
        select(func.count(TrainingSession.id)).where(TrainingSession.status == TrainingStatus.COMPLETED)
    )
    completed_sessions = completed_sessions.scalar() or 0

    failed_sessions = await session.execute(
        select(func.count(TrainingSession.id)).where(TrainingSession.status == TrainingStatus.FAILED)
    )
    failed_sessions = failed_sessions.scalar() or 0

    # Prompt counts
    total_prompts = await session.execute(select(func.count(TrainingPrompt.id)))
    total_prompts = total_prompts.scalar() or 0

    validated_prompts = await session.execute(
        select(func.count(TrainingPrompt.id)).where(TrainingPrompt.is_validated == True)
    )
    validated_prompts = validated_prompts.scalar() or 0

    # Prompts by category
    category_result = await session.execute(
        select(TrainingPrompt.category, func.count(TrainingPrompt.id)).group_by(TrainingPrompt.category)
    )
    prompts_by_category = {row[0]: row[1] for row in category_result.fetchall()}

    # Recent sessions
    recent_result = await session.execute(select(TrainingSession).order_by(TrainingSession.created_at.desc()).limit(5))
    recent_sessions = list(recent_result.scalars().all())

    return TrainingStatsResponse(
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        completed_sessions=completed_sessions,
        failed_sessions=failed_sessions,
        total_prompts=total_prompts,
        validated_prompts=validated_prompts,
        prompts_by_category=prompts_by_category,
        recent_sessions=recent_sessions,
    )


# ============= Import/Export Endpoints =============


@router.post("/prompts/import")
async def import_training_prompts(prompts: List[TrainingPromptCreate], session: AsyncSession = Depends(get_db_session)):
    """Import multiple training prompts."""
    created = []
    for data in prompts:
        content = {
            "system_prompt": data.system_prompt,
            "user_input": data.user_input,
            "tool_call": data.tool_call,
            "tool_response": data.tool_response,
            "assistant_response": data.assistant_response,
            "expected_output": data.expected_output,
        }

        prompt = TrainingPrompt(
            id=str(uuid4()),
            name=data.name,
            description=data.description,
            category=data.category,
            difficulty=data.difficulty,
            source=PromptSource.IMPORTED,
            format=data.format,
            content=content,
            system_prompt=data.system_prompt,
            user_input=data.user_input,
            tool_call=data.tool_call,
            tool_response=data.tool_response,
            assistant_response=data.assistant_response,
            expected_output=data.expected_output,
            tags=data.tags,
            session_id=data.session_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(prompt)
        created.append(prompt)

    await session.commit()

    return {"message": f"Imported {len(created)} prompts", "count": len(created)}


class OllamaMetricsResponse(BaseModel):
    """Ollama and system metrics response."""

    # Ollama metrics
    ollama_status: str
    ollama_version: Optional[str] = None
    ollama_url: str = ""
    models_count: int = 0
    models_total_size_gb: float = 0.0
    running_models_count: int = 0
    running_models: List[dict] = []
    models: List[dict] = []

    # System metrics (Ollama host)
    system_cpu_percent: Optional[float] = None
    system_memory_used_gb: Optional[float] = None
    system_memory_total_gb: Optional[float] = None
    system_memory_percent: Optional[float] = None
    system_gpu_used_gb: Optional[float] = None
    system_gpu_total_gb: Optional[float] = None
    system_gpu_percent: Optional[float] = None
    system_gpu_name: Optional[str] = None

    # Training metrics
    training_total_sessions: int = 0
    training_active_sessions: int = 0
    training_completed_sessions: int = 0
    training_total_prompts: int = 0
    training_prompts_by_category: dict = {}

    # Error info
    error: Optional[str] = None


@router.get("/ollama/metrics", response_model=OllamaMetricsResponse)
async def get_ollama_metrics(service_id: Optional[str] = None, session: AsyncSession = Depends(get_db_session)):
    """Get comprehensive Ollama and system metrics for training stats."""
    import psutil

    response = OllamaMetricsResponse(ollama_status="not_configured", ollama_url="")

    # Get Ollama service and status
    ollama = await get_ollama_service(session, service_id)
    if ollama:
        health = await ollama.health_check()
        response.ollama_status = health.get("status", "unknown")
        response.ollama_version = health.get("version")
        response.ollama_url = health.get("url", "")
        response.error = health.get("error")

        if health.get("status") == "healthy":
            try:
                # Get models info
                models = await ollama.list_models()
                response.models_count = len(models)
                response.models_total_size_gb = round(sum(m.size_gb for m in models), 2)
                response.models = [
                    {
                        "name": m.name,
                        "size_gb": m.size_gb,
                        "family": m.family,
                        "parameter_size": m.parameter_size,
                        "quantization_level": m.quantization_level,
                    }
                    for m in models
                ]

                # Get running models
                running = await ollama.get_running_models()
                response.running_models_count = len(running)
                response.running_models = running
            except Exception as e:
                response.error = str(e)

    # Get system metrics (local system - could be adapted for remote Ollama host)
    try:
        # CPU
        response.system_cpu_percent = psutil.cpu_percent(interval=0.1)

        # Memory
        memory = psutil.virtual_memory()
        response.system_memory_used_gb = round(memory.used / (1024**3), 2)
        response.system_memory_total_gb = round(memory.total / (1024**3), 2)
        response.system_memory_percent = memory.percent

        # GPU (try nvidia-smi via subprocess)
        try:
            import subprocess

            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.used,memory.total,utilization.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(",")
                if len(parts) >= 4:
                    response.system_gpu_name = parts[0].strip()
                    response.system_gpu_used_gb = round(float(parts[1].strip()) / 1024, 2)
                    response.system_gpu_total_gb = round(float(parts[2].strip()) / 1024, 2)
                    response.system_gpu_percent = float(parts[3].strip())
        except Exception:
            pass  # GPU info not available
    except Exception:
        pass  # System metrics not available

    # Get training stats from database
    try:
        # Session counts
        total_sessions = await session.execute(select(func.count(TrainingSession.id)))
        response.training_total_sessions = total_sessions.scalar() or 0

        active_sessions = await session.execute(
            select(func.count(TrainingSession.id)).where(
                TrainingSession.status.in_([TrainingStatus.RUNNING, TrainingStatus.PREPARING])
            )
        )
        response.training_active_sessions = active_sessions.scalar() or 0

        completed_sessions = await session.execute(
            select(func.count(TrainingSession.id)).where(TrainingSession.status == TrainingStatus.COMPLETED)
        )
        response.training_completed_sessions = completed_sessions.scalar() or 0

        # Prompt counts
        total_prompts = await session.execute(select(func.count(TrainingPrompt.id)))
        response.training_total_prompts = total_prompts.scalar() or 0

        # Prompts by category
        category_result = await session.execute(
            select(TrainingPrompt.category, func.count(TrainingPrompt.id)).group_by(TrainingPrompt.category)
        )
        response.training_prompts_by_category = {row[0]: row[1] for row in category_result.fetchall()}
    except Exception:
        pass

    return response


@router.delete("/prompts/all")
async def delete_all_prompts(session: AsyncSession = Depends(get_db_session)):
    """Delete all training prompts."""
    result = await session.execute(select(func.count(TrainingPrompt.id)))
    count = result.scalar() or 0

    await session.execute(delete(TrainingPrompt))
    await session.commit()

    return {"message": f"Deleted {count} prompts", "deleted_count": count}


@router.post("/prompts/seed")
async def seed_training_prompts(reset: bool = False, session: AsyncSession = Depends(get_db_session)):
    """Load pre-defined homelab training prompts from seed files.

    Args:
        reset: If True, delete all existing prompts before seeding
    """
    # Si reset, supprimer tous les prompts existants
    if reset:
        result = await session.execute(select(func.count(TrainingPrompt.id)))
        count = result.scalar() or 0
        await session.execute(delete(TrainingPrompt))
        await session.commit()
        return {"message": f"Deleted {count} prompts", "deleted_count": count, "created_count": 0}

    data_dir = Path(__file__).parent.parent / "data"

    # Load only tool-calling prompts (main training data)
    seed_file = data_dir / "seed_prompts_tools.json"

    if not seed_file.exists():
        return {"message": "No seed file found. Use import to add prompts.", "created_count": 0, "skipped_count": 0}

    with open(seed_file, "r", encoding="utf-8") as f:
        seed_prompts = json.load(f)

    created = []
    skipped = []

    for prompt_data in seed_prompts:
        # Check if prompt with same name already exists (only if not reset)
        if not reset:
            existing = await session.execute(select(TrainingPrompt).where(TrainingPrompt.name == prompt_data["name"]))
            if existing.scalar_one_or_none():
                skipped.append(prompt_data["name"])
                continue

        # Create new prompt
        prompt = TrainingPrompt(
            id=str(uuid4()),
            name=prompt_data["name"],
            description=prompt_data.get("description"),
            category=prompt_data.get("category", "homelab"),
            difficulty=prompt_data.get("difficulty", "basic"),
            source=PromptSource.SYSTEM,
            format=PromptFormat.CHAT,
            system_prompt=prompt_data.get("system_prompt"),
            user_input=prompt_data["user_input"],
            expected_output=prompt_data["expected_output"],
            tags=prompt_data.get("tags", []),
            content={
                "system_prompt": prompt_data.get("system_prompt"),
                "user_input": prompt_data["user_input"],
                "expected_output": prompt_data["expected_output"],
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(prompt)
        created.append(prompt_data["name"])

    await session.commit()

    return {
        "message": f"Seeded {len(created)} prompts"
        + (f", skipped {len(skipped)} existing" if skipped else "")
        + (" (reset mode)" if reset else ""),
        "created": created,
        "skipped": skipped,
        "reset": reset,
    }


# ============= WebSocket Endpoints =============


@router.websocket("/ws")
async def websocket_frontend(websocket: WebSocket):
    """
    WebSocket endpoint for frontend clients to receive real-time training updates.

    Messages received from client:
    - {"type": "subscribe", "session_id": "xxx"} - Subscribe to session updates
    - {"type": "unsubscribe", "session_id": "xxx"} - Unsubscribe from session
    - {"type": "ping"} - Keepalive ping

    Messages sent to client:
    - {"type": "session_update", "session_id": "xxx",
       "update_type": "progress|metrics|started|completed|failed", "data": {...}}
    - {"type": "log_line", "session_id": "xxx", "data": {...}}
    - {"type": "pong"} - Response to ping
    """
    await connection_manager.connect_frontend(websocket)

    try:
        while True:
            try:
                data = await websocket.receive_json()
                msg_type = data.get("type")

                if msg_type == "subscribe":
                    session_id = data.get("session_id")
                    if session_id:
                        connection_manager.subscribe_to_session(websocket, session_id)
                        await websocket.send_json({"type": "subscribed", "session_id": session_id})

                elif msg_type == "unsubscribe":
                    session_id = data.get("session_id")
                    if session_id:
                        connection_manager.unsubscribe_from_session(websocket, session_id)
                        await websocket.send_json({"type": "unsubscribed", "session_id": session_id})

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

            except json.JSONDecodeError:
                logger.warning("Invalid JSON received from frontend WebSocket")

    except WebSocketDisconnect:
        connection_manager.disconnect_frontend(websocket)
    except Exception as e:
        logger.error(f"Frontend WebSocket error: {e}")
        connection_manager.disconnect_frontend(websocket)


@router.websocket("/ws/worker/{job_id}")
async def websocket_worker(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for training workers to send real-time updates.

    Workers connect with their job_id and send updates about training progress.

    Messages received from worker:
    - {"type": "connected", "data": {"session_id": "xxx", "worker_id": "xxx"}}
    - {"type": "progress_update", "data": {"session_id": "xxx", "metrics": {...}}}
    - {"type": "metrics_update", "data": {"session_id": "xxx", "metrics": {...}}}
    - {"type": "log_line", "data": {"session_id": "xxx", "log": {...}}}
    - {"type": "job_started", "data": {"session_id": "xxx", ...}}
    - {"type": "job_completed", "data": {"session_id": "xxx", ...}}
    - {"type": "job_failed", "data": {"session_id": "xxx", "error": "..."}}
    - {"type": "job_cancelled", "data": {"session_id": "xxx"}}

    Messages sent to worker:
    - {"type": "cancel_job", "job_id": "xxx"} - Request to cancel the job
    - {"type": "ping"} - Keepalive ping
    """
    await connection_manager.connect_worker(websocket, job_id)

    try:
        while True:
            try:
                data = await websocket.receive_json()
                await connection_manager.handle_worker_message(job_id, data)

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from worker {job_id}")

    except WebSocketDisconnect:
        connection_manager.disconnect_worker(job_id)
    except Exception as e:
        logger.error(f"Worker WebSocket error for job {job_id}: {e}")
        connection_manager.disconnect_worker(job_id)


@router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    return connection_manager.get_stats()


# ============= Session Update Callback =============


async def _handle_session_update(session_id: str, update_type: str, data: dict):
    """
    Callback to update session in database when receiving worker updates.
    This is called by the connection_manager when it receives updates from workers.
    """
    try:
        async with async_session_maker() as db_session:
            result = await db_session.execute(select(TrainingSession).where(TrainingSession.id == session_id))
            session = result.scalar_one_or_none()

            if not session:
                logger.warning(f"Session {session_id} not found for update")
                return

            if update_type == "progress":
                metrics = data
                progress = metrics.get("progress", {})
                performance = metrics.get("performance", {})
                metrics.get("time", {})
                quality = metrics.get("quality", {})

                session.current_epoch = progress.get("current_epoch", session.current_epoch)
                session.total_epochs = progress.get("total_epochs", session.total_epochs)
                session.current_step = progress.get("current_step", session.current_step)
                session.total_steps = progress.get("total_steps", session.total_steps)
                session.progress_percent = progress.get("progress_percent", session.progress_percent)

                if performance.get("loss") is not None:
                    session.loss = performance.get("loss")
                if performance.get("learning_rate") is not None:
                    session.learning_rate = performance.get("learning_rate")

                # Store metrics history
                if session.metrics_history is None:
                    session.metrics_history = []

                session.metrics_history.append(
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "step": progress.get("current_step"),
                        "epoch": progress.get("current_epoch"),
                        "loss": performance.get("loss"),
                        "learning_rate": performance.get("learning_rate"),
                        "quality": quality,
                    }
                )

                # Keep last 1000 metrics
                if len(session.metrics_history) > 1000:
                    session.metrics_history = session.metrics_history[-1000:]

            elif update_type == "started":
                session.status = TrainingStatus.RUNNING
                session.started_at = datetime.utcnow()
                session.total_epochs = data.get("total_epochs", session.total_epochs)
                session.total_steps = data.get("total_steps", session.total_steps)

            elif update_type == "completed":
                session.status = TrainingStatus.COMPLETED
                session.completed_at = datetime.utcnow()
                session.progress_percent = 100.0
                session.output_model = data.get("output_model")

            elif update_type == "failed":
                session.status = TrainingStatus.FAILED
                session.completed_at = datetime.utcnow()
                session.error_message = data.get("error")

            elif update_type == "cancelled":
                session.status = TrainingStatus.CANCELLED
                session.completed_at = datetime.utcnow()

            session.updated_at = datetime.utcnow()
            await db_session.commit()

    except Exception as e:
        logger.error(f"Failed to update session {session_id}: {e}")


# Register the callback
connection_manager.on_session_update(_handle_session_update)
