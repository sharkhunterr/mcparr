"""MCP request history and analytics router."""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db_session
from src.models.service_config import ServiceConfig
from src.models.user_mapping import UserMapping
from src.services.mcp_audit import mcp_audit_service

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


async def get_user_display_names(session: AsyncSession, user_ids: list[str]) -> dict[str, str]:
    """
    Get display names for user IDs by looking up Open WebUI user mappings.

    The user_id in MCP requests is typically the email from Open WebUI,
    so we match against service_email in the user mappings.

    If the Open WebUI mapping has a generic central_username (like email prefix),
    we look for a better display name from other mappings of the same user.

    Args:
        session: Database session
        user_ids: List of user IDs (emails) to look up

    Returns:
        Dict mapping user_id (email) to display name
    """
    if not user_ids:
        return {}

    # Filter out None values
    valid_user_ids = [uid for uid in user_ids if uid]
    if not valid_user_ids:
        return {}

    # Find Open WebUI service
    openwebui_result = await session.execute(
        select(ServiceConfig).where(ServiceConfig.service_type == "openwebui", ServiceConfig.enabled == True)
    )
    openwebui_service = openwebui_result.scalar_one_or_none()

    if not openwebui_service:
        return {}

    # Look up Open WebUI mappings where service_email matches any of the user_ids (emails)
    mapping_result = await session.execute(
        select(UserMapping).where(
            UserMapping.service_config_id == str(openwebui_service.id),
            UserMapping.service_email.in_(valid_user_ids),
            UserMapping.enabled == True,
        )
    )
    openwebui_mappings = mapping_result.scalars().all()

    if not openwebui_mappings:
        return {}

    # Collect central_user_ids to find better display names from other mappings
    central_user_ids = [m.central_user_id for m in openwebui_mappings]

    # Get all mappings for these users to find the best display name
    all_mappings_result = await session.execute(
        select(UserMapping).where(UserMapping.central_user_id.in_(central_user_ids), UserMapping.enabled == True)
    )
    all_mappings = all_mappings_result.scalars().all()

    # Build lookup: central_user_id -> best display name
    # Prefer central_username that is not just the email prefix
    best_names: dict[str, str] = {}
    for mapping in all_mappings:
        current_name = best_names.get(mapping.central_user_id)
        candidate = mapping.central_username or mapping.service_username

        if not current_name:
            best_names[mapping.central_user_id] = candidate
        elif current_name and candidate:
            # Prefer names that don't look like email prefixes (contain dots or match email pattern)
            current_looks_like_email = "." in current_name and "@" not in current_name
            candidate_looks_like_email = "." in candidate and "@" not in candidate
            if current_looks_like_email and not candidate_looks_like_email:
                best_names[mapping.central_user_id] = candidate

    # Build final lookup: email -> display name
    display_names = {}
    for mapping in openwebui_mappings:
        if mapping.service_email:
            display_names[mapping.service_email] = best_names.get(
                mapping.central_user_id, mapping.central_username or mapping.service_username
            )

    return display_names


# Server status response
class McpServerStatusResponse(BaseModel):
    active: bool
    protocol_version: str
    server_name: str
    server_version: str
    tools_count: int
    enabled_services: list[str]
    openapi_url: str
    docs_url: str


@router.get("/status", response_model=McpServerStatusResponse)
async def get_mcp_server_status(
    session: AsyncSession = Depends(get_db_session),
):
    """Get MCP server status and configuration info."""
    from src.mcp.tools.audiobookshelf_tools import AudiobookshelfTools
    from src.mcp.tools.authentik_tools import AuthentikTools
    from src.mcp.tools.base import ToolRegistry
    from src.mcp.tools.deluge_tools import DelugeTools
    from src.mcp.tools.jackett_tools import JackettTools
    from src.mcp.tools.komga_tools import KomgaTools
    from src.mcp.tools.openwebui_tools import OpenWebUITools
    from src.mcp.tools.overseerr_tools import OverseerrTools
    from src.mcp.tools.plex_tools import PlexTools
    from src.mcp.tools.prowlarr_tools import ProwlarrTools
    from src.mcp.tools.radarr_tools import RadarrTools
    from src.mcp.tools.romm_tools import RommTools
    from src.mcp.tools.sonarr_tools import SonarrTools
    from src.mcp.tools.system_tools import SystemTools
    from src.mcp.tools.tautulli_tools import TautulliTools
    from src.mcp.tools.wikijs_tools import WikiJSTools
    from src.mcp.tools.zammad_tools import ZammadTools
    from src.models import ServiceConfig

    # Get enabled services from database
    result = await session.execute(select(ServiceConfig).where(ServiceConfig.enabled == True))
    enabled_services = result.scalars().all()
    enabled_service_types = [s.service_type.lower() for s in enabled_services]

    registry = ToolRegistry()
    registry.register(SystemTools)

    # Service type to tools class mapping
    service_tools_map = {
        "plex": PlexTools,
        "overseerr": OverseerrTools,
        "zammad": ZammadTools,
        "tautulli": TautulliTools,
        "openwebui": OpenWebUITools,
        "radarr": RadarrTools,
        "sonarr": SonarrTools,
        "prowlarr": ProwlarrTools,
        "jackett": JackettTools,
        "deluge": DelugeTools,
        "komga": KomgaTools,
        "romm": RommTools,
        "authentik": AuthentikTools,
        "audiobookshelf": AudiobookshelfTools,
        "wikijs": WikiJSTools,
    }

    for service_type in enabled_service_types:
        if service_type in service_tools_map:
            registry.register(service_tools_map[service_type])

    return McpServerStatusResponse(
        active=True,
        protocol_version="2024-11-05",
        server_name="mcparr-ai-gateway",
        server_version="1.0.0",
        tools_count=len(registry.tools),
        enabled_services=enabled_service_types,
        openapi_url="/openapi.json",
        docs_url="/docs",
    )


# Response models
class McpRequestResponse(BaseModel):
    id: str
    tool_name: str
    tool_category: Optional[str]
    status: str
    input_params: Optional[dict]
    output_result: Optional[dict]
    error_message: Optional[str]
    duration_ms: Optional[int]
    user_id: Optional[str]
    user_display_name: Optional[str] = None  # Mapped user name if available
    service_id: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class McpRequestListResponse(BaseModel):
    items: list[McpRequestResponse]
    total: int
    skip: int
    limit: int


class McpStatsResponse(BaseModel):
    total: int
    by_status: dict
    by_category: dict
    top_tools: dict
    average_duration_ms: float
    success_rate: float
    period_hours: int


class McpStatsComparisonResponse(BaseModel):
    total: int
    total_change: Optional[float]  # % change from previous period
    average_duration_ms: float
    duration_change: Optional[float]  # % change from previous period
    success_rate: float
    success_rate_change: Optional[float]  # absolute change (not %)
    completed: int
    completed_change: Optional[float]
    failed: int
    failed_change: Optional[float]


class McpStatsWithComparisonResponse(BaseModel):
    total: int
    by_status: dict
    by_category: dict
    top_tools: dict
    average_duration_ms: float
    success_rate: float
    period_hours: int
    comparison: McpStatsComparisonResponse


class McpToolUsageResponse(BaseModel):
    tool_name: str
    category: Optional[str]
    usage_count: int
    avg_duration_ms: float
    success_rate: float


class McpHourlyUsageResponse(BaseModel):
    hour: str
    count: int
    success_count: int = 0
    failed_count: int = 0


class McpUserStatsResponse(BaseModel):
    user_id: str
    user_display_name: Optional[str] = None
    request_count: int
    avg_duration_ms: float
    success_count: int
    failed_count: int
    success_rate: float


class McpUserServiceStatsResponse(BaseModel):
    user_id: str
    user_display_name: Optional[str] = None
    service: str
    request_count: int
    success_count: int
    success_rate: float


class McpHourlyUserUsageResponse(BaseModel):
    hour: str
    user_id: str
    user_display_name: Optional[str] = None
    count: int


# Endpoints
@router.get("/requests", response_model=McpRequestListResponse)
async def get_mcp_requests(
    tool_name: Optional[str] = Query(None, description="Filter by tool name"),
    category: Optional[str] = Query(None, description="Filter by tool category"),
    service: Optional[str] = Query(None, description="Filter by service (tool name prefix)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    start_time: Optional[datetime] = Query(None, description="Filter by start time"),
    end_time: Optional[datetime] = Query(None, description="Filter by end time"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return"),
    session: AsyncSession = Depends(get_db_session),
):
    """Get MCP request history with filtering and pagination."""
    requests, total = await mcp_audit_service.get_requests(
        session=session,
        tool_name=tool_name,
        category=category,
        service=service,
        status=status,
        start_time=start_time,
        end_time=end_time,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )

    # Get user display names for all user_ids in results
    user_ids = [req.user_id for req in requests if req.user_id]
    display_names = await get_user_display_names(session, user_ids)

    return McpRequestListResponse(
        items=[
            McpRequestResponse(
                id=str(req.id),
                tool_name=req.tool_name,
                tool_category=req.tool_category,
                status=req.status.value if hasattr(req.status, "value") else req.status,
                input_params=req.input_params,
                output_result=req.output_result,
                error_message=req.error_message,
                duration_ms=req.duration_ms,
                user_id=req.user_id,
                user_display_name=display_names.get(req.user_id) if req.user_id else None,
                service_id=str(req.service_id) if req.service_id else None,
                created_at=req.created_at,
                completed_at=req.completed_at,
            )
            for req in requests
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/requests/{request_id}", response_model=McpRequestResponse)
async def get_mcp_request(
    request_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get a specific MCP request by ID."""
    request = await mcp_audit_service.get_request_by_id(session, request_id)

    if not request:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="MCP request not found")

    # Get user display name if user_id exists
    user_display_name = None
    if request.user_id:
        display_names = await get_user_display_names(session, [request.user_id])
        user_display_name = display_names.get(request.user_id)

    return McpRequestResponse(
        id=str(request.id),
        tool_name=request.tool_name,
        tool_category=request.tool_category,
        status=request.status.value if hasattr(request.status, "value") else request.status,
        input_params=request.input_params,
        output_result=request.output_result,
        error_message=request.error_message,
        duration_ms=request.duration_ms,
        user_id=request.user_id,
        user_display_name=user_display_name,
        service_id=str(request.service_id) if request.service_id else None,
        created_at=request.created_at,
        completed_at=request.completed_at,
    )


@router.get("/stats", response_model=McpStatsResponse)
async def get_mcp_stats(
    hours: int = Query(24, ge=1, le=720, description="Time period in hours"),
    session: AsyncSession = Depends(get_db_session),
):
    """Get MCP request statistics for the specified time period."""
    stats = await mcp_audit_service.get_stats(session, hours=hours)
    return McpStatsResponse(**stats)


@router.get("/stats/comparison", response_model=McpStatsWithComparisonResponse)
async def get_mcp_stats_with_comparison(
    hours: int = Query(24, ge=1, le=720, description="Time period in hours"),
    session: AsyncSession = Depends(get_db_session),
):
    """Get MCP request statistics with comparison to previous period."""
    stats = await mcp_audit_service.get_stats_with_comparison(session, hours=hours)
    return McpStatsWithComparisonResponse(**stats)


@router.get("/tools/usage", response_model=list[McpToolUsageResponse])
async def get_tool_usage(
    hours: int = Query(24, ge=1, le=720, description="Time period in hours"),
    session: AsyncSession = Depends(get_db_session),
):
    """Get tool usage statistics."""
    usage = await mcp_audit_service.get_tool_usage(session, hours=hours)
    return [McpToolUsageResponse(**item) for item in usage]


@router.get("/hourly-usage", response_model=list[McpHourlyUsageResponse])
async def get_hourly_usage(
    hours: int = Query(24, ge=1, le=168, description="Time period in hours"),
    session: AsyncSession = Depends(get_db_session),
):
    """Get hourly usage statistics."""
    usage = await mcp_audit_service.get_hourly_usage(session, hours=hours)
    return [McpHourlyUsageResponse(**item) for item in usage]


@router.get("/user-stats", response_model=list[McpUserStatsResponse])
async def get_user_stats(
    hours: int = Query(24, ge=1, le=720, description="Time period in hours"),
    session: AsyncSession = Depends(get_db_session),
):
    """Get usage statistics per user."""
    stats = await mcp_audit_service.get_user_stats(session, hours=hours)

    # Get display names for all user_ids
    user_ids = [s["user_id"] for s in stats if s["user_id"]]
    display_names = await get_user_display_names(session, user_ids)

    return [
        McpUserStatsResponse(**s, user_display_name=display_names.get(s["user_id"]) if s["user_id"] else None)
        for s in stats
    ]


@router.get("/user-service-stats", response_model=list[McpUserServiceStatsResponse])
async def get_user_service_stats(
    hours: int = Query(24, ge=1, le=720, description="Time period in hours"),
    session: AsyncSession = Depends(get_db_session),
):
    """Get usage statistics per user and service."""
    stats = await mcp_audit_service.get_user_service_stats(session, hours=hours)

    # Get display names for all user_ids
    user_ids = list({s["user_id"] for s in stats if s["user_id"]})
    display_names = await get_user_display_names(session, user_ids)

    return [
        McpUserServiceStatsResponse(**s, user_display_name=display_names.get(s["user_id"]) if s["user_id"] else None)
        for s in stats
    ]


@router.get("/hourly-usage-by-user", response_model=list[McpHourlyUserUsageResponse])
async def get_hourly_usage_by_user(
    hours: int = Query(24, ge=1, le=168, description="Time period in hours"),
    session: AsyncSession = Depends(get_db_session),
):
    """Get hourly usage statistics broken down by user."""
    usage = await mcp_audit_service.get_hourly_usage_by_user(session, hours=hours)

    # Get display names for all user_ids
    user_ids = list({u["user_id"] for u in usage if u["user_id"]})
    display_names = await get_user_display_names(session, user_ids)

    return [
        McpHourlyUserUsageResponse(**u, user_display_name=display_names.get(u["user_id"]) if u["user_id"] else None)
        for u in usage
    ]


@router.delete("/cleanup")
async def cleanup_old_requests(
    retention_days: int = Query(30, ge=1, le=365, description="Retention period in days"),
    session: AsyncSession = Depends(get_db_session),
):
    """Delete MCP requests older than retention period."""
    deleted = await mcp_audit_service.cleanup_old_requests(session, retention_days=retention_days)
    return {"deleted": deleted, "retention_days": retention_days}


@router.get("/tools")
async def get_available_tools(
    session: AsyncSession = Depends(get_db_session),
):
    """Get list of available MCP tools based on enabled services."""
    from sqlalchemy import select

    from src.mcp.tools.audiobookshelf_tools import AudiobookshelfTools
    from src.mcp.tools.authentik_tools import AuthentikTools
    from src.mcp.tools.base import ToolRegistry
    from src.mcp.tools.deluge_tools import DelugeTools
    from src.mcp.tools.jackett_tools import JackettTools
    from src.mcp.tools.komga_tools import KomgaTools
    from src.mcp.tools.openwebui_tools import OpenWebUITools
    from src.mcp.tools.overseerr_tools import OverseerrTools
    from src.mcp.tools.plex_tools import PlexTools
    from src.mcp.tools.prowlarr_tools import ProwlarrTools
    from src.mcp.tools.radarr_tools import RadarrTools
    from src.mcp.tools.romm_tools import RommTools
    from src.mcp.tools.sonarr_tools import SonarrTools
    from src.mcp.tools.system_tools import SystemTools
    from src.mcp.tools.tautulli_tools import TautulliTools
    from src.mcp.tools.wikijs_tools import WikiJSTools
    from src.mcp.tools.zammad_tools import ZammadTools
    from src.models import ServiceConfig

    # Get enabled services from database
    result = await session.execute(select(ServiceConfig).where(ServiceConfig.enabled == True))
    enabled_services = result.scalars().all()
    enabled_service_types = {s.service_type.lower() for s in enabled_services}

    registry = ToolRegistry()

    # System tools are always available (no service required)
    registry.register(SystemTools)

    # Service type to tools class mapping
    service_tools_map = {
        "plex": PlexTools,
        "overseerr": OverseerrTools,
        "zammad": ZammadTools,
        "tautulli": TautulliTools,
        "openwebui": OpenWebUITools,
        "radarr": RadarrTools,
        "sonarr": SonarrTools,
        "prowlarr": ProwlarrTools,
        "jackett": JackettTools,
        "deluge": DelugeTools,
        "komga": KomgaTools,
        "romm": RommTools,
        "authentik": AuthentikTools,
        "audiobookshelf": AudiobookshelfTools,
        "wikijs": WikiJSTools,
    }

    # Register tools for enabled services
    for service_type in enabled_service_types:
        if service_type in service_tools_map:
            registry.register(service_tools_map[service_type])

    tools = []
    for name, tool_def in registry.tools.items():
        tools.append(
            {
                "name": name,
                "description": tool_def.description,
                "category": tool_def.category,
                "is_mutation": tool_def.is_mutation,
                "requires_service": tool_def.requires_service,
                "parameters": [
                    {
                        "name": p.name,
                        "description": p.description,
                        "type": p.type,
                        "required": p.required,
                        "enum": p.enum,
                        "default": p.default,
                    }
                    for p in tool_def.parameters
                ],
            }
        )

    # Group by category
    categories = {}
    for tool in tools:
        cat = tool["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(tool)

    return {
        "total": len(tools),
        "enabled_services": list(enabled_service_types),
        "categories": categories,
        "tools": tools,
    }


class ToolTestRequest(BaseModel):
    tool_name: str
    arguments: dict = {}


class ToolTestResponse(BaseModel):
    success: bool
    tool_name: str
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: int
    chain_context: Optional[dict[str, Any]] = None
    next_tools_to_call: Optional[list[dict[str, Any]]] = None
    chain_messages: Optional[list[dict[str, Any]]] = None
    message_to_display: Optional[str] = None
    ai_instruction: Optional[str] = None

    model_config = {"exclude_none": True}


@router.post("/tools/test", response_model=ToolTestResponse)
async def test_tool(
    request: ToolTestRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Test a specific MCP tool with given arguments."""
    import time

    from sqlalchemy import select

    from src.mcp.tools.audiobookshelf_tools import AudiobookshelfTools
    from src.mcp.tools.authentik_tools import AuthentikTools
    from src.mcp.tools.deluge_tools import DelugeTools
    from src.mcp.tools.jackett_tools import JackettTools
    from src.mcp.tools.komga_tools import KomgaTools
    from src.mcp.tools.openwebui_tools import OpenWebUITools
    from src.mcp.tools.overseerr_tools import OverseerrTools
    from src.mcp.tools.plex_tools import PlexTools
    from src.mcp.tools.prowlarr_tools import ProwlarrTools
    from src.mcp.tools.radarr_tools import RadarrTools
    from src.mcp.tools.romm_tools import RommTools
    from src.mcp.tools.sonarr_tools import SonarrTools
    from src.mcp.tools.system_tools import SystemTools
    from src.mcp.tools.tautulli_tools import TautulliTools
    from src.mcp.tools.wikijs_tools import WikiJSTools
    from src.mcp.tools.zammad_tools import ZammadTools
    from src.models import ServiceConfig

    start_time = time.time()

    # Get enabled services from database
    result = await session.execute(select(ServiceConfig).where(ServiceConfig.enabled == True))
    enabled_services = result.scalars().all()

    # Build service configs dict
    service_configs = {}
    for svc in enabled_services:
        service_configs[svc.service_type.lower()] = {
            "url": svc.base_url,
            "base_url": svc.base_url,
            "external_url": getattr(svc, "external_url", None),
            "port": svc.port,
            "api_key": svc.api_key,
            "username": getattr(svc, "username", None),
            "password": getattr(svc, "password", None),
            "extra_config": getattr(svc, "extra_config", None) or {},
        }

    # Tool class mapping
    tool_classes = {
        "system": SystemTools,
        "plex": PlexTools,
        "overseerr": OverseerrTools,
        "zammad": ZammadTools,
        "tautulli": TautulliTools,
        "openwebui": OpenWebUITools,
        "radarr": RadarrTools,
        "sonarr": SonarrTools,
        "prowlarr": ProwlarrTools,
        "jackett": JackettTools,
        "deluge": DelugeTools,
        "komga": KomgaTools,
        "romm": RommTools,
        "authentik": AuthentikTools,
        "audiobookshelf": AudiobookshelfTools,
        "wikijs": WikiJSTools,
    }

    # Determine which service this tool belongs to
    tool_service = None
    for service_name in tool_classes.keys():
        if request.tool_name.startswith(f"{service_name}_"):
            tool_service = service_name
            break

    if not tool_service:
        return ToolTestResponse(
            success=False,
            tool_name=request.tool_name,
            error=f"Unknown tool: {request.tool_name}",
            duration_ms=int((time.time() - start_time) * 1000),
        )

    # Check if service is enabled (system tools are always available)
    if tool_service != "system" and tool_service not in service_configs:
        return ToolTestResponse(
            success=False,
            tool_name=request.tool_name,
            error=f"Service '{tool_service}' is not enabled",
            duration_ms=int((time.time() - start_time) * 1000),
        )

    try:
        # Get the service config
        config = service_configs.get(tool_service, {})

        # Instantiate the tool class
        tool_class = tool_classes[tool_service]
        tool_instance = tool_class(config)

        # Execute the tool
        tool_result = await tool_instance.execute(request.tool_name, request.arguments)

        duration_ms = int((time.time() - start_time) * 1000)

        # Enrich with tool chain suggestions
        from src.services.tool_chain_service import enrich_tool_result_with_chains

        # tool_result is already a dict with {success, result, error} structure
        # If it's not, wrap it
        if isinstance(tool_result, dict) and "success" in tool_result:
            full_result = tool_result
        else:
            full_result = {
                "success": True,
                "result": tool_result,
                "error": None,
            }

        enriched = await enrich_tool_result_with_chains(session, request.tool_name, full_result, request.arguments)

        return ToolTestResponse(
            success=full_result.get("success", True),
            tool_name=request.tool_name,
            result=full_result.get("result"),
            error=full_result.get("error"),
            duration_ms=duration_ms,
            chain_context=enriched.get("chain_context"),
            next_tools_to_call=enriched.get("next_tools_to_call"),
            chain_messages=enriched.get("chain_messages"),
            message_to_display=enriched.get("message_to_display"),
            ai_instruction=enriched.get("ai_instruction"),
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolTestResponse(
            success=False,
            tool_name=request.tool_name,
            error=str(e),
            duration_ms=duration_ms,
        )
