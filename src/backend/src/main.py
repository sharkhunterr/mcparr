"""MCParr AI Gateway - Main FastAPI application."""

import traceback
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from src.config.settings import get_settings
from src.database.connection import get_db_manager, init_database
from src.middleware.correlation_id import CorrelationIdMiddleware
from src.middleware.logging import LoggingMiddleware
from src.routers import health
from src.services.log_service import log_service
from src.utils.logging import setup_logging


async def log_error_to_db(request: Request, exc: Exception, status_code: int = 500) -> None:
    """Log error to database for visibility in web UI."""
    try:
        db_manager = get_db_manager()
        async with db_manager.session_factory() as session:
            correlation_id = getattr(request.state, "correlation_id", None)
            await log_service.create_log(
                session,
                level="error",
                message=f"{request.method} {request.url.path} - {status_code}: {str(exc)}",
                source="backend",
                component="exception_handler",
                correlation_id=correlation_id,
                exception_type=type(exc).__name__,
                exception_message=str(exc),
                stack_trace=traceback.format_exc(),
                extra_data={
                    "method": request.method,
                    "path": str(request.url.path),
                    "query": str(request.url.query) if request.url.query else None,
                    "status_code": status_code,
                },
            )
    except Exception as log_err:
        # Don't let logging errors break the response
        print(f"Failed to log error to DB: {log_err}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    settings = get_settings()

    # Setup logging
    setup_logging(settings.log_level)

    # Initialize database
    db_manager = init_database()
    await db_manager.create_tables()

    print(f"🚀 MCParr AI Gateway started on port {settings.api_port}")
    print("📊 Web UI: http://localhost:3000")
    print(f"🔗 API Docs: http://localhost:{settings.api_port}/docs")
    print(f"🤖 MCP Server: http://localhost:{settings.mcp_port}")

    yield

    # Shutdown
    await db_manager.close()
    print("👋 MCParr AI Gateway shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="MCParr AI Gateway",
        description="MCP server with web administration interface for homelab services",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Middleware setup
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])  # Local network trust model

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(LoggingMiddleware)

    # Exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        # Log HTTP errors (4xx and 5xx) to database
        if exc.status_code >= 400:
            await log_error_to_db(request, exc, exc.status_code)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "correlation_id": getattr(request.state, "correlation_id", "unknown"),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        # Log unhandled exceptions to database
        await log_error_to_db(request, exc, 500)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(exc) if settings.debug else "An error occurred",
                "correlation_id": getattr(request.state, "correlation_id", "unknown"),
            },
        )

    # Include routers
    app.include_router(health.router, tags=["Health"])

    # Import and include other routers
    from src.routers import config, dashboard, services, system

    app.include_router(dashboard.router, tags=["Dashboard"])
    app.include_router(system.router, tags=["System"])
    app.include_router(config.router, tags=["Configuration"])
    app.include_router(services.router, tags=["Services"])

    # Users router
    from src.routers import users

    app.include_router(users.router, tags=["Users"])

    # Groups router
    from src.routers import groups

    app.include_router(groups.router, tags=["Groups"])

    # Service Groups router
    from src.routers import service_groups

    app.include_router(service_groups.router, tags=["Service Groups"])

    # Tool Chains router
    from src.routers import tool_chains

    app.include_router(tool_chains.router, tags=["Tool Chains"])

    # Observability routers
    from src.routers import alerts, logs

    app.include_router(logs.router, tags=["Logs"])
    app.include_router(alerts.router, tags=["Alerts"])

    # MCP router
    from src.routers import mcp

    app.include_router(mcp.router, tags=["MCP"])

    # Training router
    from src.routers import training

    app.include_router(training.router, tags=["Training"])

    # Workers router (GPU training workers)
    from src.routers import workers

    app.include_router(workers.router, tags=["Workers"])

    # OpenAPI Tools router for Open WebUI integration
    from src.routers import openapi_tools

    app.include_router(openapi_tools.router)

    # Backup/Restore router
    from src.routers import backup

    app.include_router(backup.router, tags=["Backup"])

    # WebSocket endpoints
    from src.websocket.logs import websocket_logs_endpoint
    from src.websocket.system import handle_system_websocket
    from src.websocket.training import handle_training_websocket

    @app.websocket("/ws/system")
    async def websocket_system_endpoint(websocket):
        await handle_system_websocket(websocket)

    @app.websocket("/ws")
    async def websocket_main_endpoint(websocket):
        """Main WebSocket endpoint for general connections."""
        await handle_system_websocket(websocket)

    @app.websocket("/ws/logs")
    async def websocket_logs(websocket):
        """WebSocket endpoint for real-time log streaming."""
        await websocket_logs_endpoint(websocket)

    @app.websocket("/ws/training")
    async def websocket_training(websocket):
        """WebSocket endpoint for real-time training progress."""
        await handle_training_websocket(websocket)

    return app


# Create application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
