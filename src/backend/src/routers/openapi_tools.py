"""OpenAPI Tools router for Open WebUI integration.

This router exposes MCP tools as standard REST endpoints that Open WebUI
can discover via /openapi.json and invoke as external tools.
"""

import logging
import os
from typing import Any, Dict, Optional

import httpx
import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db_session
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
from src.models.mcp_request import McpRequest, McpToolCategory

logger = logging.getLogger(__name__)

# Open WebUI base URL for user resolution
OPEN_WEBUI_BASE_URL = os.getenv("OPEN_WEBUI_BASE_URL", "http://192.168.1.60:8080")

router = APIRouter(prefix="/tools", tags=["AI Tools"])


# ============================================================================
# Open WebUI User Resolution (Session Auth)
# ============================================================================


def decode_jwt_user_id(token: str) -> Optional[str]:
    """
    Decode a JWT token without verifying the signature to extract user ID.
    This is safe in a trusted network environment where the token comes from Open WebUI.
    """
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload.get("id")
    except jwt.exceptions.DecodeError:
        return None
    except Exception:
        return None


async def resolve_openwebui_user(request: Request) -> Optional[dict]:
    """
    Resolve Open WebUI user from the session JWT token.

    When Open WebUI is configured with Auth: Session, it forwards the user's
    JWT token in both the Authorization header and Cookie.

    Returns dict with id, email, name, role or None if resolution fails.
    """
    token = None

    # Try Authorization header first (Bearer token)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]

    # Fallback to cookie
    if not token:
        token = request.cookies.get("token")

    if not token:
        return None

    # Decode JWT to get user ID
    user_id = decode_jwt_user_id(token)
    if not user_id:
        return None

    # Call Open WebUI API to get full user info (email, name, role)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{OPEN_WEBUI_BASE_URL}/api/v1/auths/", headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 200:
                data = response.json()
                user_info = {
                    "id": data.get("id"),
                    "email": data.get("email"),
                    "name": data.get("name"),
                    "role": data.get("role"),
                }
                logger.info(f"[OpenWebUI] Resolved user: {user_info.get('email')} (id: {user_info.get('id')})")
                return user_info
            else:
                # API call failed, return just the ID from JWT
                logger.warning(f"[OpenWebUI] API call failed ({response.status_code}), using JWT id only")
                return {"id": user_id, "email": None, "name": None, "role": None}
    except Exception as e:
        logger.warning(f"[OpenWebUI] Error calling API: {e}, using JWT id only")
        return {"id": user_id, "email": None, "name": None, "role": None}


# ============================================================================
# Open WebUI compatible OpenAPI spec endpoint
# ============================================================================


def _build_tool_path(tool_def) -> dict:
    """Build OpenAPI path definition from a ToolDefinition."""
    path_def = {
        "post": {
            "operationId": tool_def.name,
            "summary": tool_def.description[:100] if len(tool_def.description) > 100 else tool_def.description,
            "description": tool_def.description,
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                }
            },
        }
    }

    # Add request body if tool has parameters
    if tool_def.parameters:
        properties = {}
        required = []
        for param in tool_def.parameters:
            prop: dict = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
            properties[param.name] = prop
            if param.required:
                required.append(param.name)

        schema: dict = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required

        path_def["post"]["requestBody"] = {
            "required": bool(required),
            "content": {"application/json": {"schema": schema}},
        }

    return path_def


def generate_openwebui_openapi_spec() -> dict:
    """Generate OpenAPI 3.0.3 spec dynamically from all tool definitions."""
    # Collect all tool definitions from all tool classes
    all_tool_classes = [
        SystemTools,
        PlexTools,
        TautulliTools,
        OverseerrTools,
        RadarrTools,
        SonarrTools,
        ProwlarrTools,
        JackettTools,
        DelugeTools,
        KomgaTools,
        RommTools,
        AudiobookshelfTools,
        OpenWebUITools,
        ZammadTools,
        WikiJSTools,
        AuthentikTools,
    ]

    paths = {}
    for tool_class in all_tool_classes:
        try:
            # Instantiate without config to get definitions
            tool_instance = tool_class(None)
            for tool_def in tool_instance.definitions:
                path = f"/tools/{tool_def.name}"
                paths[path] = _build_tool_path(tool_def)
        except Exception as e:
            logger.warning(f"Failed to get definitions from {tool_class.__name__}: {e}")

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "MCParr AI Tools",
            "description": "AI tools for homelab services management",
            "version": "1.0.0",
        },
        "paths": paths,
        "components": {
            "schemas": {
                "ToolResponse": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "description": "Whether the tool executed successfully"},
                        "result": {"type": "object", "description": "The result data from the tool"},
                        "error": {"type": "string", "description": "Error message if the tool failed"},
                    },
                    "required": ["success"],
                }
            }
        },
    }


def filter_spec_by_services(spec: dict, services: list[str], title: str, description: str) -> dict:
    """Filter OpenAPI spec to include only paths for specified services."""
    filtered_paths = {}
    for path, path_def in spec.get("paths", {}).items():
        # Extract service name from path like /tools/plex_search_media -> plex
        path_service = path.split("/")[-1].split("_")[0]
        if path_service in services:
            filtered_paths[path] = path_def

    return {
        "openapi": spec["openapi"],
        "info": {"title": title, "description": description, "version": spec["info"]["version"]},
        "paths": filtered_paths,
        "components": spec.get("components", {}),
    }


@router.get("/openapi.json", include_in_schema=False, response_class=JSONResponse)
async def get_openwebui_openapi():
    """Get OpenAPI spec optimized for Open WebUI compatibility."""
    return JSONResponse(content=generate_openwebui_openapi_spec())


@router.get("/media/openapi.json", include_in_schema=False, response_class=JSONResponse)
async def get_media_openapi():
    """Get OpenAPI spec for media tools (Plex, Tautulli, Overseerr, Komga, RomM)."""
    full_spec = generate_openwebui_openapi_spec()
    return JSONResponse(
        content=filter_spec_by_services(
            full_spec,
            ["plex", "tautulli", "overseerr", "komga", "romm"],
            "MCParr Media Tools",
            "AI tools for media playback and libraries (Plex, Tautulli, Overseerr, Komga, RomM)",
        )
    )


@router.get("/processing/openapi.json", include_in_schema=False, response_class=JSONResponse)
async def get_processing_openapi():
    """Get OpenAPI spec for media processing tools (Radarr, Sonarr, Prowlarr, Jackett, Deluge)."""
    full_spec = generate_openwebui_openapi_spec()
    return JSONResponse(
        content=filter_spec_by_services(
            full_spec,
            ["radarr", "sonarr", "prowlarr", "jackett", "deluge"],
            "MCParr Processing Tools",
            "AI tools for media acquisition and processing (Radarr, Sonarr, Prowlarr, Jackett, Deluge)",
        )
    )


@router.get("/system/openapi.json", include_in_schema=False, response_class=JSONResponse)
async def get_system_openapi():
    """Get OpenAPI spec for system tools (System, OpenWebUI, Zammad)."""
    full_spec = generate_openwebui_openapi_spec()
    return JSONResponse(
        content=filter_spec_by_services(
            full_spec,
            ["system", "openwebui", "zammad"],
            "MCParr System Tools",
            "AI tools for system management (health, support)",
        )
    )


# ============================================================================
# Pydantic models for tool requests/responses
# ============================================================================


class ToolResponse(BaseModel):
    """Standard response for all tools."""

    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# --- Plex Tools ---


class PlexSearchRequest(BaseModel):
    """Search for media in Plex library."""

    query: str = Field(..., description="Search query (title, actor, director, etc.)")
    media_type: Optional[str] = Field(None, description="Type of media: movie, show, episode, artist, album, track")
    limit: int = Field(10, description="Maximum number of results to return")


class PlexRecentlyAddedRequest(BaseModel):
    """Get recently added media."""

    library_name: Optional[str] = Field(None, description="Name of the library (e.g., 'Movies', 'TV Shows')")
    limit: int = Field(10, description="Maximum number of items to return")


class PlexOnDeckRequest(BaseModel):
    """Get on deck items."""

    limit: int = Field(10, description="Maximum number of items to return")


class PlexMediaDetailsRequest(BaseModel):
    """Get details for a specific media item."""

    title: str = Field(..., description="Title of the movie or TV show")
    year: Optional[int] = Field(None, description="Release year (helps with disambiguation)")


# --- Overseerr Tools ---


class OverseerrSearchRequest(BaseModel):
    """Search for media in Overseerr."""

    query: str = Field(..., description="Search query for movies or TV shows")
    media_type: Optional[str] = Field(None, description="Filter by type: movie or tv")


class OverseerrRequestMediaRequest(BaseModel):
    """Request media through Overseerr."""

    title: str = Field(..., description="Title of the media to request")
    media_type: str = Field(..., description="Type of media: movie or tv")
    year: Optional[int] = Field(None, description="Release year for disambiguation")


# --- Tautulli Tools ---


class TautulliHistoryRequest(BaseModel):
    """Get play history from Tautulli."""

    length: int = Field(25, description="Number of history items to return")
    user: Optional[str] = Field(None, description="Filter history by username")


class TautulliRecentlyAddedRequest(BaseModel):
    """Get recently added items."""

    count: int = Field(25, description="Number of recently added items to return")


# --- Zammad Tools ---


class ZammadSearchTicketsRequest(BaseModel):
    """Search Zammad tickets."""

    query: str = Field(..., description="Search query for tickets")
    limit: int = Field(10, description="Maximum number of results")


class ZammadCreateTicketRequest(BaseModel):
    """Create a new Zammad ticket."""

    title: str = Field(..., description="Ticket title/subject")
    body: str = Field(..., description="Ticket body/description")
    customer_email: Optional[str] = Field(None, description="Customer email address")
    priority: Optional[str] = Field("normal", description="Priority: low, normal, high")


# ============================================================================
# Tool category mapping
# ============================================================================

TOOL_CATEGORY_MAP = {
    "system_get_health": McpToolCategory.SYSTEM,
    "system_get_metrics": McpToolCategory.SYSTEM,
    "plex_get_libraries": McpToolCategory.MEDIA,
    "plex_search_media": McpToolCategory.MEDIA,
    "plex_get_recently_added": McpToolCategory.MEDIA,
    "plex_get_on_deck": McpToolCategory.MEDIA,
    "plex_get_media_details": McpToolCategory.MEDIA,
    "plex_get_active_sessions": McpToolCategory.MEDIA,
    "overseerr_search": McpToolCategory.REQUESTS,
    "overseerr_get_requests": McpToolCategory.REQUESTS,
    "overseerr_request_media": McpToolCategory.REQUESTS,
    "overseerr_get_trending": McpToolCategory.REQUESTS,
    "tautulli_get_activity": McpToolCategory.MEDIA,
    "tautulli_get_history": McpToolCategory.MEDIA,
    "tautulli_get_users": McpToolCategory.USERS,
    "tautulli_get_libraries": McpToolCategory.MEDIA,
    "tautulli_get_statistics": McpToolCategory.MEDIA,
    "tautulli_get_recently_added": McpToolCategory.MEDIA,
    "tautulli_get_server_info": McpToolCategory.SYSTEM,
    "tautulli_get_top_users": McpToolCategory.MEDIA,
    "tautulli_get_top_movies": McpToolCategory.MEDIA,
    "tautulli_get_top_tv_shows": McpToolCategory.MEDIA,
    "tautulli_get_top_music": McpToolCategory.MEDIA,
    "tautulli_get_top_platforms": McpToolCategory.MEDIA,
    "tautulli_get_user_stats": McpToolCategory.MEDIA,
    "tautulli_get_watch_stats_summary": McpToolCategory.MEDIA,
    "zammad_get_tickets": McpToolCategory.SUPPORT,
    "zammad_search_tickets": McpToolCategory.SUPPORT,
    "zammad_create_ticket": McpToolCategory.SUPPORT,
    "zammad_get_organizations": McpToolCategory.SUPPORT,
    "zammad_get_users": McpToolCategory.USERS,
    "zammad_get_ticket_details": McpToolCategory.SUPPORT,
    "zammad_add_comment": McpToolCategory.SUPPORT,
    "zammad_update_ticket_status": McpToolCategory.SUPPORT,
    "zammad_get_ticket_stats": McpToolCategory.SUPPORT,
    "openwebui_get_status": McpToolCategory.SYSTEM,
    "openwebui_get_users": McpToolCategory.USERS,
    "openwebui_get_models": McpToolCategory.SYSTEM,
    "openwebui_get_chats": McpToolCategory.SYSTEM,
    "openwebui_get_statistics": McpToolCategory.SYSTEM,
    "openwebui_search_users": McpToolCategory.USERS,
}

MUTATION_TOOLS = {
    "overseerr_request_media",
    "zammad_create_ticket",
}


# ============================================================================
# Helper to get tool registry with enabled services
# ============================================================================


async def get_tool_registry(session: AsyncSession) -> ToolRegistry:
    """Get tool registry with enabled services."""
    result = await session.execute(select(ServiceConfig).where(ServiceConfig.enabled == True))
    enabled_services = result.scalars().all()

    configs_by_type = {}
    for svc in enabled_services:
        svc_type = svc.service_type.lower()
        # Construct full URL with port if specified
        base_url = svc.base_url
        if svc.port:
            # Remove trailing slash if present
            base_url = base_url.rstrip("/")
            base_url = f"{base_url}:{svc.port}"
        configs_by_type[svc_type] = {
            "base_url": base_url,
            "external_url": svc.external_url,  # Public URL for user-facing links
            "api_key": svc.api_key,
            "username": svc.username,
            "password": svc.password,
            "config": svc.config or {},
        }

    registry = ToolRegistry()
    registry.register(SystemTools)

    if "plex" in configs_by_type:
        registry.register(PlexTools, configs_by_type["plex"])
    if "overseerr" in configs_by_type:
        registry.register(OverseerrTools, configs_by_type["overseerr"])
    if "zammad" in configs_by_type:
        registry.register(ZammadTools, configs_by_type["zammad"])
    if "tautulli" in configs_by_type:
        registry.register(TautulliTools, configs_by_type["tautulli"])
    if "openwebui" in configs_by_type:
        registry.register(OpenWebUITools, configs_by_type["openwebui"])
    if "romm" in configs_by_type:
        registry.register(RommTools, configs_by_type["romm"])
    if "komga" in configs_by_type:
        registry.register(KomgaTools, configs_by_type["komga"])
    if "radarr" in configs_by_type:
        registry.register(RadarrTools, configs_by_type["radarr"])
    if "sonarr" in configs_by_type:
        registry.register(SonarrTools, configs_by_type["sonarr"])
    if "prowlarr" in configs_by_type:
        registry.register(ProwlarrTools, configs_by_type["prowlarr"])
    if "jackett" in configs_by_type:
        registry.register(JackettTools, configs_by_type["jackett"])
    if "deluge" in configs_by_type:
        registry.register(DelugeTools, configs_by_type["deluge"])
    if "authentik" in configs_by_type:
        registry.register(AuthentikTools, configs_by_type["authentik"])
    if "audiobookshelf" in configs_by_type:
        registry.register(AudiobookshelfTools, configs_by_type["audiobookshelf"])
    if "wikijs" in configs_by_type:
        registry.register(WikiJSTools, configs_by_type["wikijs"])

    return registry


async def execute_tool_with_logging(
    session: AsyncSession,
    tool_name: str,
    arguments: dict,
    request: Optional[Request] = None,
) -> dict:
    """Execute a tool and log the request to the database."""
    from src.models.user_mapping import UserMapping
    from src.services.permission_service import check_tool_permission

    # Create MCP request record
    mcp_request = McpRequest(
        tool_name=tool_name,
        tool_category=TOOL_CATEGORY_MAP.get(tool_name, McpToolCategory.SYSTEM),
        input_params=arguments,
        is_mutation=tool_name in MUTATION_TOOLS,
    )

    central_user_id = None

    # Extract user info from Open WebUI session token
    if request:
        # Try to resolve user from Open WebUI session JWT
        openwebui_user = await resolve_openwebui_user(request)
        if openwebui_user:
            # Use email as user_id if available, otherwise use the UUID
            mcp_request.user_id = openwebui_user.get("email") or openwebui_user.get("id")
            # Store full user info in input_params for reference
            if mcp_request.input_params is None:
                mcp_request.input_params = {}
            mcp_request.input_params["_openwebui_user"] = openwebui_user
            logger.info(f"[MCP] Tool '{tool_name}' called by user: {mcp_request.user_id}")

            # Try to find central_user_id from user mappings
            # First try by email
            if openwebui_user.get("email"):
                user_mapping_result = await session.execute(
                    select(UserMapping.central_user_id)
                    .where(UserMapping.central_email == openwebui_user.get("email"))
                    .limit(1)
                )
                row = user_mapping_result.first()
                if row:
                    central_user_id = row[0]

            # If no mapping found by email, try by Open WebUI user ID
            if not central_user_id and openwebui_user.get("id"):
                user_mapping_result = await session.execute(
                    select(UserMapping.central_user_id)
                    .where(UserMapping.service_user_id == openwebui_user.get("id"))
                    .limit(1)
                )
                row = user_mapping_result.first()
                if row:
                    central_user_id = row[0]

            # Check group permissions if we have a central_user_id
            if central_user_id:
                # Get service type from tool name
                service_type = None
                if tool_name.startswith("plex_"):
                    service_type = "plex"
                elif tool_name.startswith("overseerr_"):
                    service_type = "overseerr"
                elif tool_name.startswith("zammad_"):
                    service_type = "zammad"
                elif tool_name.startswith("tautulli_"):
                    service_type = "tautulli"
                elif tool_name.startswith("openwebui_"):
                    service_type = "openwebui"
                elif tool_name.startswith("system_"):
                    service_type = "system"

                permission_result = await check_tool_permission(session, central_user_id, tool_name, service_type)

                if not permission_result.has_access:
                    logger.warning(
                        f"[MCP] Access denied for user {central_user_id} to tool {tool_name}: "
                        f"{permission_result.denial_reason}"
                    )
                    # Log the denied request
                    mcp_request.mark_failed(f"Access denied: {permission_result.denial_reason}", "PermissionDenied")
                    session.add(mcp_request)
                    await session.commit()
                    return {
                        "success": False,
                        "error": (
                            f"Access denied: You don't have permission to use this tool. "
                            f"{permission_result.denial_reason}"
                        ),
                        "error_type": "PermissionDenied",
                    }
                else:
                    logger.info(
                        f"[MCP] Access granted for user {central_user_id} to tool {tool_name} "
                        f"by group: {permission_result.granted_by_group}"
                    )

        # Also check for explicit headers as fallback
        mcp_request.session_id = request.headers.get("X-Session-Id")
        mcp_request.correlation_id = request.headers.get("X-Correlation-Id")
        mcp_request.ai_model = request.headers.get("X-AI-Model")

    session.add(mcp_request)
    await session.flush()  # Get the ID

    # Mark as started
    mcp_request.mark_started()

    try:
        # Get registry and execute
        registry = await get_tool_registry(session)
        result = await registry.execute(tool_name, arguments)

        # Mark as completed
        if result.get("success"):
            mcp_request.mark_completed(result)
        else:
            mcp_request.mark_failed(result.get("error", "Unknown error"), result.get("error_type", "ToolError"))

        await session.commit()
        return result

    except Exception as e:
        mcp_request.mark_failed(str(e), type(e).__name__)
        await session.commit()
        raise


# ============================================================================
# System Tools
# ============================================================================


@router.post(
    "/system_list_tools",
    response_model=ToolResponse,
    summary="ALWAYS CALL FIRST - List available tools by category",
    description="CALL THIS TOOL FIRST before any other tool. Returns all available tools grouped by category to help you choose the right tool.",
)
async def system_list_tools(request: Request, session: AsyncSession = Depends(get_db_session)):
    """List all available tools grouped by category."""
    result = await execute_tool_with_logging(session, "system_list_tools", {}, request)
    return ToolResponse(**result)


@router.post(
    "/system_get_health",
    response_model=ToolResponse,
    summary="Get system health status",
    description="Get overall system health status including CPU, memory, disk usage and any issues detected.",
)
async def system_get_health(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get system health status."""
    result = await execute_tool_with_logging(session, "system_get_health", {}, request)
    return ToolResponse(**result)


@router.post(
    "/system_get_metrics",
    response_model=ToolResponse,
    summary="Get system metrics",
    description="Get current system resource metrics including CPU, memory, disk, network usage and uptime.",
)
async def system_get_metrics(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get system metrics."""
    result = await execute_tool_with_logging(session, "system_get_metrics", {}, request)
    return ToolResponse(**result)


# ============================================================================
# Plex Tools
# ============================================================================


@router.post(
    "/plex_get_libraries",
    response_model=ToolResponse,
    summary="Get Plex libraries",
    description="Get list of all Plex media libraries (Movies, TV Shows, Music, etc.)",
)
async def plex_get_libraries(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get all Plex libraries."""
    result = await execute_tool_with_logging(session, "plex_get_libraries", {}, request)
    return ToolResponse(**result)


@router.post(
    "/plex_search_media",
    response_model=ToolResponse,
    summary="Search Plex media",
    description="Search for movies, TV shows, or other media in Plex library by title, actor, director, etc.",
)
async def plex_search_media(request: Request, body: PlexSearchRequest, session: AsyncSession = Depends(get_db_session)):
    """Search for media in Plex."""
    result = await execute_tool_with_logging(session, "plex_search_media", body.model_dump(exclude_none=True), request)
    return ToolResponse(**result)


@router.post(
    "/plex_get_recently_added",
    response_model=ToolResponse,
    summary="Get recently added media",
    description="Get recently added media to Plex library. Can filter by library name.",
)
async def plex_get_recently_added(
    request: Request,
    body: PlexRecentlyAddedRequest = PlexRecentlyAddedRequest(),
    session: AsyncSession = Depends(get_db_session),
):
    """Get recently added media."""
    result = await execute_tool_with_logging(
        session, "plex_get_recently_added", body.model_dump(exclude_none=True), request
    )
    return ToolResponse(**result)


@router.post(
    "/plex_get_on_deck",
    response_model=ToolResponse,
    summary="Get On Deck items",
    description="Get 'On Deck' items (continue watching) for the Plex server.",
)
async def plex_get_on_deck(
    request: Request, body: PlexOnDeckRequest = PlexOnDeckRequest(), session: AsyncSession = Depends(get_db_session)
):
    """Get on deck items."""
    result = await execute_tool_with_logging(session, "plex_get_on_deck", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/plex_get_media_details",
    response_model=ToolResponse,
    summary="Get media details",
    description="Get detailed information about a specific movie or TV show including cast, genres, rating.",
)
async def plex_get_media_details(
    request: Request, body: PlexMediaDetailsRequest, session: AsyncSession = Depends(get_db_session)
):
    """Get media details."""
    result = await execute_tool_with_logging(
        session, "plex_get_media_details", body.model_dump(exclude_none=True), request
    )
    return ToolResponse(**result)


@router.post(
    "/plex_get_active_sessions",
    response_model=ToolResponse,
    summary="Get active streaming sessions",
    description="Get list of currently active streaming sessions on Plex (who is watching what).",
)
async def plex_get_active_sessions(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get active streaming sessions."""
    result = await execute_tool_with_logging(session, "plex_get_active_sessions", {}, request)
    return ToolResponse(**result)


# ============================================================================
# Overseerr Tools
# ============================================================================


@router.post(
    "/overseerr_search",
    response_model=ToolResponse,
    summary="Search Overseerr",
    description="Search for movies or TV shows in Overseerr to check availability or request.",
)
async def overseerr_search(
    request: Request, body: OverseerrSearchRequest, session: AsyncSession = Depends(get_db_session)
):
    """Search Overseerr."""
    result = await execute_tool_with_logging(session, "overseerr_search", body.model_dump(exclude_none=True), request)
    return ToolResponse(**result)


@router.post(
    "/overseerr_get_requests",
    response_model=ToolResponse,
    summary="Get Overseerr requests",
    description="Get list of pending and recent media requests from Overseerr.",
)
async def overseerr_get_requests(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Overseerr requests."""
    result = await execute_tool_with_logging(session, "overseerr_get_requests", {}, request)
    return ToolResponse(**result)


@router.post(
    "/overseerr_request_media",
    response_model=ToolResponse,
    summary="Request media on Overseerr",
    description="Request a movie or TV show to be added to the library via Overseerr.",
)
async def overseerr_request_media(
    request: Request, body: OverseerrRequestMediaRequest, session: AsyncSession = Depends(get_db_session)
):
    """Request media on Overseerr."""
    result = await execute_tool_with_logging(
        session, "overseerr_request_media", body.model_dump(exclude_none=True), request
    )
    return ToolResponse(**result)


@router.post(
    "/overseerr_get_trending",
    response_model=ToolResponse,
    summary="Get trending media",
    description="Get trending movies and TV shows from Overseerr.",
)
async def overseerr_get_trending(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get trending media."""
    result = await execute_tool_with_logging(session, "overseerr_get_trending", {}, request)
    return ToolResponse(**result)


# ============================================================================
# Tautulli Tools
# ============================================================================


@router.post(
    "/tautulli_get_activity",
    response_model=ToolResponse,
    summary="Get Plex activity",
    description="Get current Plex streaming activity including active sessions, bandwidth usage, and stream counts.",
)
async def tautulli_get_activity(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get current Plex activity."""
    result = await execute_tool_with_logging(session, "tautulli_get_activity", {}, request)
    return ToolResponse(**result)


@router.post(
    "/tautulli_get_history",
    response_model=ToolResponse,
    summary="Get play history",
    description="Get play history from Tautulli with optional user filtering.",
)
async def tautulli_get_history(
    request: Request,
    body: TautulliHistoryRequest = TautulliHistoryRequest(),
    session: AsyncSession = Depends(get_db_session),
):
    """Get play history."""
    result = await execute_tool_with_logging(
        session, "tautulli_get_history", body.model_dump(exclude_none=True), request
    )
    return ToolResponse(**result)


@router.post(
    "/tautulli_get_users",
    response_model=ToolResponse,
    summary="Get Plex users",
    description="Get list of all Plex users known to Tautulli with their details and permissions.",
)
async def tautulli_get_users(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Plex users."""
    result = await execute_tool_with_logging(session, "tautulli_get_users", {}, request)
    return ToolResponse(**result)


@router.post(
    "/tautulli_get_libraries",
    response_model=ToolResponse,
    summary="Get library statistics",
    description="Get library statistics from Tautulli including item counts and types.",
)
async def tautulli_get_libraries(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get library statistics."""
    result = await execute_tool_with_logging(session, "tautulli_get_libraries", {}, request)
    return ToolResponse(**result)


@router.post(
    "/tautulli_get_statistics",
    response_model=ToolResponse,
    summary="Get comprehensive statistics",
    description="Get comprehensive statistics including activity, history, users, and libraries overview.",
)
async def tautulli_get_statistics(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get comprehensive statistics."""
    result = await execute_tool_with_logging(session, "tautulli_get_statistics", {}, request)
    return ToolResponse(**result)


@router.post(
    "/tautulli_get_recently_added",
    response_model=ToolResponse,
    summary="Get recently added via Tautulli",
    description="Get recently added items to Plex libraries via Tautulli.",
)
async def tautulli_get_recently_added(
    request: Request,
    body: TautulliRecentlyAddedRequest = TautulliRecentlyAddedRequest(),
    session: AsyncSession = Depends(get_db_session),
):
    """Get recently added items."""
    result = await execute_tool_with_logging(session, "tautulli_get_recently_added", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/tautulli_get_server_info",
    response_model=ToolResponse,
    summary="Get server info",
    description="Get Tautulli and Plex server information including versions and status.",
)
async def tautulli_get_server_info(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get server information."""
    result = await execute_tool_with_logging(session, "tautulli_get_server_info", {}, request)
    return ToolResponse(**result)


class TautulliMyStatsRequest(BaseModel):
    """Request body for tautulli_get_my_stats."""

    length: int = Field(default=25, description="Number of history items to return")


async def get_user_tautulli_mapping(session: AsyncSession, openwebui_user: dict) -> Optional[str]:
    """
    Get the Tautulli username for an Open WebUI user.

    Args:
        session: Database session
        openwebui_user: User info from Open WebUI (id, email, name)

    Returns:
        Tautulli username if mapping exists, None otherwise
    """
    from src.models.user_mapping import UserMapping

    # First find the central_user_id from Open WebUI email
    central_user_id = None

    if openwebui_user.get("email"):
        result = await session.execute(
            select(UserMapping.central_user_id).where(UserMapping.central_email == openwebui_user.get("email")).limit(1)
        )
        row = result.first()
        if row:
            central_user_id = row[0]

    # If not found by email, try by Open WebUI user ID
    if not central_user_id and openwebui_user.get("id"):
        result = await session.execute(
            select(UserMapping.central_user_id).where(UserMapping.service_user_id == openwebui_user.get("id")).limit(1)
        )
        row = result.first()
        if row:
            central_user_id = row[0]

    if not central_user_id:
        return None

    # Now find the Tautulli service config
    tautulli_service = await session.execute(
        select(ServiceConfig).where(ServiceConfig.service_type == "tautulli", ServiceConfig.enabled == True)
    )
    tautulli_config = tautulli_service.scalar_one_or_none()

    if not tautulli_config:
        return None

    # Find the user's Tautulli mapping
    tautulli_mapping = await session.execute(
        select(UserMapping).where(
            UserMapping.central_user_id == central_user_id,
            UserMapping.service_config_id == str(tautulli_config.id),
            UserMapping.enabled == True,
        )
    )
    mapping = tautulli_mapping.scalar_one_or_none()

    if mapping:
        return mapping.service_username

    return None


@router.post(
    "/tautulli_get_my_stats",
    response_model=ToolResponse,
    summary="Get my personal viewing statistics",
    description=(
        "Get your personal viewing history and statistics from Tautulli. "
        "Requires a user mapping between Open WebUI and Tautulli."
    ),
)
async def tautulli_get_my_stats(
    request: Request,
    body: TautulliMyStatsRequest = TautulliMyStatsRequest(),
    session: AsyncSession = Depends(get_db_session),
):
    """Get personal viewing statistics for the current user."""
    from datetime import datetime

    # Resolve Open WebUI user
    openwebui_user = await resolve_openwebui_user(request)
    if not openwebui_user:
        return ToolResponse(
            success=False, error="Impossible d'identifier l'utilisateur. Veuillez vous connecter à Open WebUI."
        )

    # Get Tautulli username mapping
    tautulli_username = await get_user_tautulli_mapping(session, openwebui_user)

    if not tautulli_username:
        user_display = openwebui_user.get("name") or openwebui_user.get("email") or "Utilisateur"
        return ToolResponse(
            success=False,
            error=f"Aucun mapping Tautulli trouvé pour {user_display}. "
            f"Veuillez configurer le mapping utilisateur dans les paramètres "
            f"(Open WebUI → Tautulli) pour accéder à vos statistiques personnelles.",
        )

    # Log the request with user context
    mcp_request = McpRequest(
        tool_name="tautulli_get_my_stats",
        tool_category=McpToolCategory.MONITORING,
        input_params={"length": body.length, "resolved_user": tautulli_username},
        is_mutation=False,
        user_id=openwebui_user.get("email") or openwebui_user.get("id"),
    )
    mcp_request.input_params["_openwebui_user"] = openwebui_user
    session.add(mcp_request)
    await session.commit()
    await session.refresh(mcp_request)

    start_time = datetime.utcnow()

    try:
        # Get Tautulli service config
        tautulli_service = await session.execute(
            select(ServiceConfig).where(ServiceConfig.service_type == "tautulli", ServiceConfig.enabled == True)
        )
        tautulli_config = tautulli_service.scalar_one_or_none()

        if not tautulli_config:
            mcp_request.mark_failed("Tautulli service not configured", "ConfigError")
            await session.commit()
            return ToolResponse(success=False, error="Le service Tautulli n'est pas configuré.")

        # Create adapter and get history for the user
        from src.adapters.tautulli import TautulliAdapter

        class ServiceConfigProxy:
            def __init__(self, config):
                self.api_key = config.api_key
                self.base_url = f"{config.base_url}:{config.port}" if config.port else config.base_url
                self.port = None
                self.config = config.config or {}

            def get_config_value(self, key: str, default=None):
                return self.config.get(key, default)

        adapter = TautulliAdapter(ServiceConfigProxy(tautulli_config))

        # Get user's watch history
        history_data = await adapter.get_history(length=body.length, user=tautulli_username)

        # Calculate some personal stats
        total_plays = history_data.get("total_plays", 0)
        total_duration = history_data.get("total_duration", 0)
        if isinstance(total_duration, str):
            total_duration = int(total_duration) if total_duration.isdigit() else 0

        history_items = history_data.get("history", [])

        # Count by media type
        media_types = {}
        for item in history_items:
            media_type = item.get("media_type", "unknown")
            media_types[media_type] = media_types.get(media_type, 0) + 1

        result = {
            "user": tautulli_username,
            "total_plays": total_plays,
            "total_watch_time_hours": round(total_duration / 3600, 2),
            "media_breakdown": media_types,
            "recent_history": [
                {
                    "title": _format_media_title(item),
                    "media_type": item.get("media_type"),
                    "date": item.get("date"),
                    "duration_minutes": round(item.get("duration", 0) / 60, 1),
                    "percent_complete": item.get("percent_complete"),
                    "watched_status": item.get("watched_status"),
                    "player": item.get("player"),
                }
                for item in history_items
            ],
        }

        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        mcp_request.mark_completed(result)
        mcp_request.duration_ms = duration_ms
        await session.commit()

        return ToolResponse(success=True, result=result)

    except Exception as e:
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        mcp_request.mark_failed(str(e), type(e).__name__)
        mcp_request.duration_ms = duration_ms
        await session.commit()

        logger.error(f"[tautulli_get_my_stats] Error: {e}")
        return ToolResponse(success=False, error=str(e))


def _format_media_title(item: dict) -> str:
    """Format title including parent/grandparent for TV shows."""
    title = item.get("title", "")
    grandparent = item.get("grandparent_title")
    parent = item.get("parent_title")

    if grandparent:
        return f"{grandparent} - {parent} - {title}" if parent else f"{grandparent} - {title}"
    elif parent:
        return f"{parent} - {title}"
    return title


# New Tautulli statistics models
class TautulliTopRequest(BaseModel):
    """Request body for top statistics endpoints."""

    days: int = Field(default=30, description="Number of days to analyze")
    stats_type: str = Field(default="plays", description="Type of stats: 'plays' or 'duration'")
    limit: int = Field(default=10, description="Number of items to return")


class TautulliTopWithUserRequest(BaseModel):
    """Request body for top statistics with optional user filter."""

    days: int = Field(default=30, description="Number of days to analyze")
    stats_type: str = Field(default="plays", description="Type of stats: 'plays' or 'duration'")
    limit: int = Field(default=10, description="Number of items to return")
    username: Optional[str] = Field(default=None, description="Filter by username (optional)")


class TautulliUserStatsRequest(BaseModel):
    """Request body for user statistics."""

    username: str = Field(..., description="Username or friendly name of the user")
    days: int = Field(default=30, description="Number of days to analyze")


class TautulliWatchSummaryRequest(BaseModel):
    """Request body for watch statistics summary."""

    days: int = Field(default=30, description="Number of days to analyze")
    stats_type: str = Field(default="plays", description="Type of stats: 'plays' or 'duration'")
    limit: int = Field(default=5, description="Number of items per category")


@router.post(
    "/tautulli_get_top_users",
    response_model=ToolResponse,
    summary="Get top Plex users",
    description="Get top Plex users by play count or watch duration over a specified period.",
)
async def tautulli_get_top_users(
    request: Request, body: TautulliTopRequest = TautulliTopRequest(), session: AsyncSession = Depends(get_db_session)
):
    """Get top users by plays or duration."""
    result = await execute_tool_with_logging(session, "tautulli_get_top_users", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/tautulli_get_top_movies",
    response_model=ToolResponse,
    summary="Get top watched movies",
    description="Get top watched movies over a specified period, optionally filtered by user.",
)
async def tautulli_get_top_movies(
    request: Request,
    body: TautulliTopWithUserRequest = TautulliTopWithUserRequest(),
    session: AsyncSession = Depends(get_db_session),
):
    """Get top watched movies."""
    result = await execute_tool_with_logging(
        session, "tautulli_get_top_movies", body.model_dump(exclude_none=True), request
    )
    return ToolResponse(**result)


@router.post(
    "/tautulli_get_top_tv_shows",
    response_model=ToolResponse,
    summary="Get top watched TV shows",
    description="Get top watched TV shows over a specified period, optionally filtered by user.",
)
async def tautulli_get_top_tv_shows(
    request: Request,
    body: TautulliTopWithUserRequest = TautulliTopWithUserRequest(),
    session: AsyncSession = Depends(get_db_session),
):
    """Get top watched TV shows."""
    result = await execute_tool_with_logging(
        session, "tautulli_get_top_tv_shows", body.model_dump(exclude_none=True), request
    )
    return ToolResponse(**result)


@router.post(
    "/tautulli_get_top_music",
    response_model=ToolResponse,
    summary="Get top listened music",
    description="Get top listened music over a specified period, optionally filtered by user.",
)
async def tautulli_get_top_music(
    request: Request,
    body: TautulliTopWithUserRequest = TautulliTopWithUserRequest(),
    session: AsyncSession = Depends(get_db_session),
):
    """Get top listened music."""
    result = await execute_tool_with_logging(
        session, "tautulli_get_top_music", body.model_dump(exclude_none=True), request
    )
    return ToolResponse(**result)


@router.post(
    "/tautulli_get_top_platforms",
    response_model=ToolResponse,
    summary="Get top streaming platforms",
    description="Get most used platforms/devices for streaming over a specified period.",
)
async def tautulli_get_top_platforms(
    request: Request, body: TautulliTopRequest = TautulliTopRequest(), session: AsyncSession = Depends(get_db_session)
):
    """Get top platforms."""
    result = await execute_tool_with_logging(session, "tautulli_get_top_platforms", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/tautulli_get_user_stats",
    response_model=ToolResponse,
    summary="Get user statistics",
    description="Get detailed watch statistics for a specific user including watch time, top content, and devices.",
)
async def tautulli_get_user_stats(
    request: Request, body: TautulliUserStatsRequest, session: AsyncSession = Depends(get_db_session)
):
    """Get detailed statistics for a specific user."""
    result = await execute_tool_with_logging(session, "tautulli_get_user_stats", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/tautulli_get_watch_stats_summary",
    response_model=ToolResponse,
    summary="Get watch statistics summary",
    description="Get a comprehensive summary of watch statistics including top users, movies, TV shows, and platforms.",
)
async def tautulli_get_watch_stats_summary(
    request: Request,
    body: TautulliWatchSummaryRequest = TautulliWatchSummaryRequest(),
    session: AsyncSession = Depends(get_db_session),
):
    """Get comprehensive watch statistics summary."""
    result = await execute_tool_with_logging(session, "tautulli_get_watch_stats_summary", body.model_dump(), request)
    return ToolResponse(**result)


# ============================================================================
# Zammad Tools
# ============================================================================


@router.post(
    "/zammad_get_tickets",
    response_model=ToolResponse,
    summary="Get support tickets",
    description="Get list of support tickets from Zammad with their status.",
)
async def zammad_get_tickets(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get support tickets."""
    result = await execute_tool_with_logging(session, "zammad_get_tickets", {}, request)
    return ToolResponse(**result)


@router.post(
    "/zammad_search_tickets",
    response_model=ToolResponse,
    summary="Search tickets",
    description="Search Zammad tickets by keyword.",
)
async def zammad_search_tickets(
    request: Request, body: ZammadSearchTicketsRequest, session: AsyncSession = Depends(get_db_session)
):
    """Search tickets."""
    result = await execute_tool_with_logging(session, "zammad_search_tickets", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/zammad_create_ticket",
    response_model=ToolResponse,
    summary="Create support ticket",
    description="Create a new support ticket in Zammad.",
)
async def zammad_create_ticket(
    request: Request, body: ZammadCreateTicketRequest, session: AsyncSession = Depends(get_db_session)
):
    """Create a support ticket."""
    result = await execute_tool_with_logging(
        session, "zammad_create_ticket", body.model_dump(exclude_none=True), request
    )
    return ToolResponse(**result)


@router.post(
    "/zammad_get_organizations",
    response_model=ToolResponse,
    summary="Get organizations",
    description="Get list of organizations from Zammad.",
)
async def zammad_get_organizations(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get organizations."""
    result = await execute_tool_with_logging(session, "zammad_get_organizations", {}, request)
    return ToolResponse(**result)


@router.post(
    "/zammad_get_users",
    response_model=ToolResponse,
    summary="Get Zammad users",
    description="Get list of users from Zammad.",
)
async def zammad_get_users(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Zammad users."""
    result = await execute_tool_with_logging(session, "zammad_get_users", {}, request)
    return ToolResponse(**result)


class ZammadGetTicketDetailsRequest(BaseModel):
    """Get ticket details request."""

    ticket_id: int = Field(..., description="ID or number of the ticket to retrieve (e.g., 1 or 20001)")


class ZammadAddCommentRequest(BaseModel):
    """Add comment to ticket request."""

    ticket_id: int = Field(..., description="ID of the ticket")
    comment: str = Field(..., description="Comment content")
    internal: bool = Field(False, description="Whether the comment is internal (not visible to customer)")


class ZammadUpdateTicketStatusRequest(BaseModel):
    """Update ticket status request."""

    ticket_id: int = Field(..., description="ID of the ticket")
    status: str = Field(..., description="New status for the ticket (open, pending, closed)")


@router.post(
    "/zammad_get_ticket_details",
    response_model=ToolResponse,
    summary="Get ticket details",
    description="Get detailed information about a specific ticket including all articles/messages.",
)
async def zammad_get_ticket_details(
    request: Request, body: ZammadGetTicketDetailsRequest, session: AsyncSession = Depends(get_db_session)
):
    """Get ticket details."""
    result = await execute_tool_with_logging(session, "zammad_get_ticket_details", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/zammad_add_comment",
    response_model=ToolResponse,
    summary="Add comment to ticket",
    description="Add a comment/reply to an existing ticket.",
)
async def zammad_add_comment(
    request: Request, body: ZammadAddCommentRequest, session: AsyncSession = Depends(get_db_session)
):
    """Add comment to ticket."""
    result = await execute_tool_with_logging(session, "zammad_add_comment", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/zammad_update_ticket_status",
    response_model=ToolResponse,
    summary="Update ticket status",
    description="Update the status of a ticket (open, pending, closed).",
)
async def zammad_update_ticket_status(
    request: Request, body: ZammadUpdateTicketStatusRequest, session: AsyncSession = Depends(get_db_session)
):
    """Update ticket status."""
    result = await execute_tool_with_logging(session, "zammad_update_ticket_status", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/zammad_get_ticket_stats",
    response_model=ToolResponse,
    summary="Get ticket statistics",
    description="Get statistics about tickets (open count, pending, closed, etc.).",
)
async def zammad_get_ticket_stats(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get ticket statistics."""
    result = await execute_tool_with_logging(session, "zammad_get_ticket_stats", {}, request)
    return ToolResponse(**result)


# ============================================================================
# Open WebUI Tools
# ============================================================================


class OpenWebUIUsersRequest(BaseModel):
    """Get Open WebUI users request."""

    limit: int = Field(50, description="Maximum number of users to return")


class OpenWebUIChatsRequest(BaseModel):
    """Get Open WebUI chats request."""

    limit: int = Field(20, description="Maximum number of chats to return")


class OpenWebUISearchUsersRequest(BaseModel):
    """Search Open WebUI users request."""

    query: str = Field(..., description="Search query (email or name)")


@router.post(
    "/openwebui_get_status",
    response_model=ToolResponse,
    summary="Get Open WebUI status",
    description="Get Open WebUI service status including version and current user info.",
)
async def openwebui_get_status(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Open WebUI status."""
    result = await execute_tool_with_logging(session, "openwebui_get_status", {}, request)
    return ToolResponse(**result)


@router.post(
    "/openwebui_get_users",
    response_model=ToolResponse,
    summary="Get Open WebUI users",
    description="Get list of all users registered in Open WebUI (requires admin privileges).",
)
async def openwebui_get_users(
    request: Request,
    body: OpenWebUIUsersRequest = OpenWebUIUsersRequest(),
    session: AsyncSession = Depends(get_db_session),
):
    """Get Open WebUI users."""
    result = await execute_tool_with_logging(session, "openwebui_get_users", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/openwebui_get_models",
    response_model=ToolResponse,
    summary="Get available AI models",
    description="Get list of available AI models in Open WebUI.",
)
async def openwebui_get_models(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get available AI models."""
    result = await execute_tool_with_logging(session, "openwebui_get_models", {}, request)
    return ToolResponse(**result)


@router.post(
    "/openwebui_get_chats",
    response_model=ToolResponse,
    summary="Get chat history",
    description="Get chat history for the authenticated user.",
)
async def openwebui_get_chats(
    request: Request,
    body: OpenWebUIChatsRequest = OpenWebUIChatsRequest(),
    session: AsyncSession = Depends(get_db_session),
):
    """Get chat history."""
    result = await execute_tool_with_logging(session, "openwebui_get_chats", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/openwebui_get_statistics",
    response_model=ToolResponse,
    summary="Get Open WebUI statistics",
    description="Get Open WebUI statistics including user count, models, and chat activity.",
)
async def openwebui_get_statistics(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Open WebUI statistics."""
    result = await execute_tool_with_logging(session, "openwebui_get_statistics", {}, request)
    return ToolResponse(**result)


@router.post(
    "/openwebui_search_users",
    response_model=ToolResponse,
    summary="Search Open WebUI users",
    description="Search for users by email or name in Open WebUI (requires admin privileges).",
)
async def openwebui_search_users(
    request: Request, body: OpenWebUISearchUsersRequest, session: AsyncSession = Depends(get_db_session)
):
    """Search Open WebUI users."""
    result = await execute_tool_with_logging(session, "openwebui_search_users", body.model_dump(), request)
    return ToolResponse(**result)


# ============================================================================
# RomM Tools
# ============================================================================


class RommRomsRequest(BaseModel):
    """Get ROMs request."""

    platform_id: Optional[int] = Field(None, description="Filter by platform ID")
    limit: int = Field(50, description="Maximum number of ROMs to return")


class RommSearchRequest(BaseModel):
    """Search ROMs request."""

    query: str = Field(..., description="Search query (game title)")


@router.post(
    "/romm_get_platforms",
    response_model=ToolResponse,
    summary="Get ROM platforms",
    description="Get list of gaming platforms in RomM.",
)
async def romm_get_platforms(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get RomM platforms."""
    result = await execute_tool_with_logging(session, "romm_get_platforms", {}, request)
    return ToolResponse(**result)


@router.post(
    "/romm_get_roms",
    response_model=ToolResponse,
    summary="Get ROMs",
    description="Get list of ROMs, optionally filtered by platform.",
)
async def romm_get_roms(
    request: Request, body: RommRomsRequest = RommRomsRequest(), session: AsyncSession = Depends(get_db_session)
):
    """Get ROMs from RomM."""
    result = await execute_tool_with_logging(session, "romm_get_roms", body.model_dump(exclude_none=True), request)
    return ToolResponse(**result)


@router.post("/romm_search", response_model=ToolResponse, summary="Search ROMs", description="Search for ROMs by name.")
async def romm_search(request: Request, body: RommSearchRequest, session: AsyncSession = Depends(get_db_session)):
    """Search ROMs in RomM."""
    result = await execute_tool_with_logging(session, "romm_search_roms", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/romm_get_statistics",
    response_model=ToolResponse,
    summary="Get RomM statistics",
    description="Get RomM library statistics.",
)
async def romm_get_statistics(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get RomM statistics."""
    result = await execute_tool_with_logging(session, "romm_get_statistics", {}, request)
    return ToolResponse(**result)


class RommRecentlyAddedRequest(BaseModel):
    """Get recently added ROMs request."""

    limit: int = Field(20, description="Maximum number of ROMs to return")
    days: int = Field(30, description="Number of days to look back (0 for no limit)")


@router.post(
    "/romm_get_recently_added",
    response_model=ToolResponse,
    summary="Get recently added ROMs",
    description="Get recently added ROMs sorted by date (newest first).",
)
async def romm_get_recently_added(
    request: Request, body: RommRecentlyAddedRequest, session: AsyncSession = Depends(get_db_session)
):
    """Get recently added ROMs."""
    result = await execute_tool_with_logging(session, "romm_get_recently_added", body.model_dump(), request)
    return ToolResponse(**result)


# ============================================================================
# Komga Tools
# ============================================================================


class KomgaSearchRequest(BaseModel):
    """Search Komga request."""

    query: str = Field(..., description="Search query (searches in titles)")
    library_name: Optional[str] = Field(None, description="Library name to search in (e.g., 'Comics', 'Manga')")
    limit: int = Field(20, description="Maximum number of results per category")


@router.post(
    "/komga_get_libraries",
    response_model=ToolResponse,
    summary="Get Komga libraries",
    description="Get list of comic/manga libraries in Komga.",
)
async def komga_get_libraries(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Komga libraries."""
    result = await execute_tool_with_logging(session, "komga_get_libraries", {}, request)
    return ToolResponse(**result)


@router.post(
    "/komga_search",
    response_model=ToolResponse,
    summary="Search Komga",
    description="Search for series and books in Komga by title. Returns detailed information including genres, publisher, read progress, and URLs. Can optionally filter by library name.",
)
async def komga_search(request: Request, body: KomgaSearchRequest, session: AsyncSession = Depends(get_db_session)):
    """Search Komga."""
    result = await execute_tool_with_logging(session, "komga_search", body.model_dump(exclude_none=True), request)
    return ToolResponse(**result)


@router.post(
    "/komga_get_users",
    response_model=ToolResponse,
    summary="Get Komga users",
    description="Get list of users in Komga.",
)
async def komga_get_users(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Komga users."""
    result = await execute_tool_with_logging(session, "komga_get_users", {}, request)
    return ToolResponse(**result)


@router.post(
    "/komga_get_statistics",
    response_model=ToolResponse,
    summary="Get Komga statistics",
    description="Get Komga library statistics.",
)
async def komga_get_statistics(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Komga statistics."""
    result = await execute_tool_with_logging(session, "komga_get_statistics", {}, request)
    return ToolResponse(**result)


# ============================================================================
# Radarr Tools
# ============================================================================


class RadarrMoviesRequest(BaseModel):
    """Get movies request."""

    limit: int = Field(50, description="Maximum number of movies to return")


class RadarrSearchRequest(BaseModel):
    """Search movie request."""

    query: str = Field(..., description="Movie title to search for")


class RadarrCalendarRequest(BaseModel):
    """Get calendar request."""

    days: int = Field(7, description="Number of days ahead to look")


@router.post(
    "/radarr_get_movies",
    response_model=ToolResponse,
    summary="Get movies from Radarr",
    description="Get list of movies in Radarr library.",
)
async def radarr_get_movies(
    request: Request, body: RadarrMoviesRequest = RadarrMoviesRequest(), session: AsyncSession = Depends(get_db_session)
):
    """Get movies from Radarr."""
    result = await execute_tool_with_logging(session, "radarr_get_movies", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/radarr_search_movie",
    response_model=ToolResponse,
    summary="Search for movie",
    description="Search for a movie to add to Radarr.",
)
async def radarr_search_movie(
    request: Request, body: RadarrSearchRequest, session: AsyncSession = Depends(get_db_session)
):
    """Search for movie in Radarr."""
    result = await execute_tool_with_logging(session, "radarr_search_movie", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/radarr_get_queue",
    response_model=ToolResponse,
    summary="Get Radarr download queue",
    description="Get current download queue in Radarr.",
)
async def radarr_get_queue(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Radarr download queue."""
    result = await execute_tool_with_logging(session, "radarr_get_queue", {}, request)
    return ToolResponse(**result)


@router.post(
    "/radarr_get_calendar",
    response_model=ToolResponse,
    summary="Get Radarr calendar",
    description="Get upcoming movie releases.",
)
async def radarr_get_calendar(
    request: Request,
    body: RadarrCalendarRequest = RadarrCalendarRequest(),
    session: AsyncSession = Depends(get_db_session),
):
    """Get Radarr calendar."""
    result = await execute_tool_with_logging(session, "radarr_get_calendar", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/radarr_get_statistics",
    response_model=ToolResponse,
    summary="Get Radarr statistics",
    description="Get Radarr library statistics.",
)
async def radarr_get_statistics(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Radarr statistics."""
    result = await execute_tool_with_logging(session, "radarr_get_statistics", {}, request)
    return ToolResponse(**result)


# ============================================================================
# Sonarr Tools
# ============================================================================


class SonarrSeriesRequest(BaseModel):
    """Get series request."""

    limit: int = Field(50, description="Maximum number of series to return")


class SonarrSearchRequest(BaseModel):
    """Search series request."""

    query: str = Field(..., description="TV series title to search for")


class SonarrCalendarRequest(BaseModel):
    """Get calendar request."""

    days: int = Field(7, description="Number of days ahead to look")


@router.post(
    "/sonarr_get_series",
    response_model=ToolResponse,
    summary="Get TV series from Sonarr",
    description="Get list of TV series in Sonarr library.",
)
async def sonarr_get_series(
    request: Request, body: SonarrSeriesRequest = SonarrSeriesRequest(), session: AsyncSession = Depends(get_db_session)
):
    """Get series from Sonarr."""
    result = await execute_tool_with_logging(session, "sonarr_get_series", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/sonarr_search_series",
    response_model=ToolResponse,
    summary="Search for TV series",
    description="Search for a TV series to add to Sonarr.",
)
async def sonarr_search_series(
    request: Request, body: SonarrSearchRequest, session: AsyncSession = Depends(get_db_session)
):
    """Search for series in Sonarr."""
    result = await execute_tool_with_logging(session, "sonarr_search_series", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/sonarr_get_queue",
    response_model=ToolResponse,
    summary="Get Sonarr download queue",
    description="Get current download queue in Sonarr.",
)
async def sonarr_get_queue(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Sonarr download queue."""
    result = await execute_tool_with_logging(session, "sonarr_get_queue", {}, request)
    return ToolResponse(**result)


@router.post(
    "/sonarr_get_calendar",
    response_model=ToolResponse,
    summary="Get Sonarr calendar",
    description="Get upcoming TV episode releases.",
)
async def sonarr_get_calendar(
    request: Request,
    body: SonarrCalendarRequest = SonarrCalendarRequest(),
    session: AsyncSession = Depends(get_db_session),
):
    """Get Sonarr calendar."""
    result = await execute_tool_with_logging(session, "sonarr_get_calendar", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/sonarr_get_statistics",
    response_model=ToolResponse,
    summary="Get Sonarr statistics",
    description="Get Sonarr library statistics.",
)
async def sonarr_get_statistics(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Sonarr statistics."""
    result = await execute_tool_with_logging(session, "sonarr_get_statistics", {}, request)
    return ToolResponse(**result)


# ============================================================================
# Prowlarr Tools
# ============================================================================


class ProwlarrSearchRequest(BaseModel):
    """Search request."""

    query: str = Field(..., description="Search query")
    limit: int = Field(50, description="Maximum number of results")


@router.post(
    "/prowlarr_get_indexers",
    response_model=ToolResponse,
    summary="Get Prowlarr indexers",
    description="Get list of configured indexers.",
)
async def prowlarr_get_indexers(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Prowlarr indexers."""
    result = await execute_tool_with_logging(session, "prowlarr_get_indexers", {}, request)
    return ToolResponse(**result)


@router.post(
    "/prowlarr_search",
    response_model=ToolResponse,
    summary="Search in Prowlarr",
    description="Search across all indexers.",
)
async def prowlarr_search(
    request: Request, body: ProwlarrSearchRequest, session: AsyncSession = Depends(get_db_session)
):
    """Search in Prowlarr."""
    result = await execute_tool_with_logging(session, "prowlarr_search", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/prowlarr_get_statistics",
    response_model=ToolResponse,
    summary="Get Prowlarr statistics",
    description="Get Prowlarr overall statistics.",
)
async def prowlarr_get_statistics(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Prowlarr statistics."""
    result = await execute_tool_with_logging(session, "prowlarr_get_statistics", {}, request)
    return ToolResponse(**result)


# ============================================================================
# Audiobookshelf Tools
# ============================================================================


@router.post(
    "/audiobookshelf_get_libraries",
    response_model=ToolResponse,
    summary="Get Audiobookshelf libraries",
    description="Get list of libraries in Audiobookshelf (audiobooks and podcasts).",
)
async def audiobookshelf_get_libraries(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Audiobookshelf libraries."""
    result = await execute_tool_with_logging(session, "audiobookshelf_get_libraries", {}, request)
    return ToolResponse(**result)


class AudiobookshelfLibraryItemsRequest(BaseModel):
    """Request for library items."""

    library_name: Optional[str] = Field(
        None,
        description="Library name to get items from (e.g., 'Audiobooks', 'Podcasts'). Optional - if not specified, uses the first library.",
    )
    limit: int = Field(50, description="Maximum number of items to return")
    page: int = Field(0, description="Page number (0-indexed)")


@router.post(
    "/audiobookshelf_get_library_items",
    response_model=ToolResponse,
    summary="Get Audiobookshelf library items",
    description="Get items (audiobooks/podcasts) from a library. If no library specified, uses the first available library.",
)
async def audiobookshelf_get_library_items(
    request: Request, body: AudiobookshelfLibraryItemsRequest, session: AsyncSession = Depends(get_db_session)
):
    """Get Audiobookshelf library items."""
    result = await execute_tool_with_logging(
        session, "audiobookshelf_get_library_items", body.model_dump(exclude_none=True), request
    )
    return ToolResponse(**result)


class AudiobookshelfSearchRequest(BaseModel):
    """Search request for Audiobookshelf."""

    query: str = Field(..., description="Search query")
    library_name: Optional[str] = Field(
        None,
        description="Library name to search in (e.g., 'Audiobooks', 'Podcasts'). Optional - if not specified, uses the first library.",
    )
    limit: int = Field(25, description="Maximum number of results per category")


@router.post(
    "/audiobookshelf_search",
    response_model=ToolResponse,
    summary="Search Audiobookshelf",
    description="Search for audiobooks, podcasts, authors, or series. If no library specified, uses the first available library.",
)
async def audiobookshelf_search(
    request: Request, body: AudiobookshelfSearchRequest, session: AsyncSession = Depends(get_db_session)
):
    """Search in Audiobookshelf."""
    result = await execute_tool_with_logging(
        session, "audiobookshelf_search", body.model_dump(exclude_none=True), request
    )
    return ToolResponse(**result)


@router.post(
    "/audiobookshelf_get_users",
    response_model=ToolResponse,
    summary="Get Audiobookshelf users",
    description="Get list of users in Audiobookshelf (admin only).",
)
async def audiobookshelf_get_users(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Audiobookshelf users."""
    result = await execute_tool_with_logging(session, "audiobookshelf_get_users", {}, request)
    return ToolResponse(**result)


class AudiobookshelfListeningStatsRequest(BaseModel):
    """Request for listening statistics."""

    user_id: Optional[str] = Field(None, description="User ID to get stats for (optional, defaults to current user)")


@router.post(
    "/audiobookshelf_get_listening_stats",
    response_model=ToolResponse,
    summary="Get Audiobookshelf listening stats",
    description="Get listening statistics for current user or specified user.",
)
async def audiobookshelf_get_listening_stats(
    request: Request,
    body: AudiobookshelfListeningStatsRequest = AudiobookshelfListeningStatsRequest(),
    session: AsyncSession = Depends(get_db_session),
):
    """Get Audiobookshelf listening stats."""
    result = await execute_tool_with_logging(
        session, "audiobookshelf_get_listening_stats", body.model_dump(exclude_none=True), request
    )
    return ToolResponse(**result)


class AudiobookshelfMediaProgressRequest(BaseModel):
    """Request for media progress."""

    title: str = Field(..., description="Title of the audiobook/podcast")
    library_name: Optional[str] = Field(
        None,
        description="Library name to search in (e.g., 'Audiobooks', 'Podcasts'). Optional - if not specified, searches all libraries.",
    )


@router.post(
    "/audiobookshelf_get_media_progress",
    response_model=ToolResponse,
    summary="Get Audiobookshelf media progress",
    description="Get progress for a specific audiobook/podcast.",
)
async def audiobookshelf_get_media_progress(
    request: Request, body: AudiobookshelfMediaProgressRequest, session: AsyncSession = Depends(get_db_session)
):
    """Get Audiobookshelf media progress."""
    result = await execute_tool_with_logging(
        session, "audiobookshelf_get_media_progress", body.model_dump(exclude_none=True), request
    )
    return ToolResponse(**result)


@router.post(
    "/audiobookshelf_get_statistics",
    response_model=ToolResponse,
    summary="Get Audiobookshelf statistics",
    description="Get Audiobookshelf library statistics.",
)
async def audiobookshelf_get_statistics(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Audiobookshelf statistics."""
    result = await execute_tool_with_logging(session, "audiobookshelf_get_statistics", {}, request)
    return ToolResponse(**result)


# ============================================================================
# WikiJS Tools
# ============================================================================


class WikiJSGetPagesRequest(BaseModel):
    """Request for getting pages."""

    limit: int = Field(50, description="Maximum number of pages to return")
    locale: str = Field("en", description="Locale/language filter")


@router.post(
    "/wikijs_get_pages",
    response_model=ToolResponse,
    summary="Get WikiJS pages",
    description="Get list of wiki pages from WikiJS, ordered by most recently updated.",
)
async def wikijs_get_pages(
    request: Request,
    body: WikiJSGetPagesRequest = WikiJSGetPagesRequest(),
    session: AsyncSession = Depends(get_db_session),
):
    """Get WikiJS pages."""
    result = await execute_tool_with_logging(session, "wikijs_get_pages", body.model_dump(), request)
    return ToolResponse(**result)


class WikiJSGetPageRequest(BaseModel):
    """Request for getting a specific page."""

    page_id: int = Field(..., description="ID of the page to retrieve")


@router.post(
    "/wikijs_get_page",
    response_model=ToolResponse,
    summary="Get WikiJS page",
    description="Get detailed content of a specific wiki page by its ID.",
)
async def wikijs_get_page(
    request: Request, body: WikiJSGetPageRequest, session: AsyncSession = Depends(get_db_session)
):
    """Get WikiJS page."""
    result = await execute_tool_with_logging(session, "wikijs_get_page", body.model_dump(), request)
    return ToolResponse(**result)


class WikiJSSearchRequest(BaseModel):
    """Search request for WikiJS."""

    query: str = Field(..., description="Search query")
    locale: str = Field("en", description="Locale/language to search in")


@router.post(
    "/wikijs_search",
    response_model=ToolResponse,
    summary="Search WikiJS",
    description="Search for wiki pages by keyword or phrase.",
)
async def wikijs_search(request: Request, body: WikiJSSearchRequest, session: AsyncSession = Depends(get_db_session)):
    """Search in WikiJS."""
    result = await execute_tool_with_logging(session, "wikijs_search", body.model_dump(), request)
    return ToolResponse(**result)


class WikiJSGetPageTreeRequest(BaseModel):
    """Request for getting page tree."""

    parent_path: str = Field("", description="Parent path to start from (empty for root)")
    locale: str = Field("en", description="Locale/language filter")


@router.post(
    "/wikijs_get_page_tree",
    response_model=ToolResponse,
    summary="Get WikiJS page tree",
    description="Get the hierarchical tree structure of wiki pages.",
)
async def wikijs_get_page_tree(
    request: Request,
    body: WikiJSGetPageTreeRequest = WikiJSGetPageTreeRequest(),
    session: AsyncSession = Depends(get_db_session),
):
    """Get WikiJS page tree."""
    result = await execute_tool_with_logging(session, "wikijs_get_page_tree", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/wikijs_get_tags",
    response_model=ToolResponse,
    summary="Get WikiJS tags",
    description="Get all tags used in the wiki.",
)
async def wikijs_get_tags(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get WikiJS tags."""
    result = await execute_tool_with_logging(session, "wikijs_get_tags", {}, request)
    return ToolResponse(**result)


@router.post(
    "/wikijs_get_users",
    response_model=ToolResponse,
    summary="Get WikiJS users",
    description="Get list of users in WikiJS.",
)
async def wikijs_get_users(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get WikiJS users."""
    result = await execute_tool_with_logging(session, "wikijs_get_users", {}, request)
    return ToolResponse(**result)


@router.post(
    "/wikijs_get_statistics",
    response_model=ToolResponse,
    summary="Get WikiJS statistics",
    description="Get WikiJS statistics (page count, user count, etc.).",
)
async def wikijs_get_statistics(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get WikiJS statistics."""
    result = await execute_tool_with_logging(session, "wikijs_get_statistics", {}, request)
    return ToolResponse(**result)


class WikiJSCreatePageRequest(BaseModel):
    """Request for creating a page."""

    path: str = Field(..., description="Path for the page (e.g., 'docs/getting-started')")
    title: str = Field(..., description="Title of the page")
    content: str = Field(..., description="Markdown content of the page")
    description: str = Field("", description="Short description of the page")
    locale: str = Field("en", description="Locale/language for the page")
    tags: str = Field("", description="Tags for the page (comma-separated)")


@router.post(
    "/wikijs_create_page",
    response_model=ToolResponse,
    summary="Create WikiJS page",
    description="Create a new wiki page in WikiJS.",
)
async def wikijs_create_page(
    request: Request, body: WikiJSCreatePageRequest, session: AsyncSession = Depends(get_db_session)
):
    """Create WikiJS page."""
    result = await execute_tool_with_logging(session, "wikijs_create_page", body.model_dump(), request)
    return ToolResponse(**result)


# ============================================================================
# Authentik Tools
# ============================================================================


class AuthentikGetUsersRequest(BaseModel):
    """Request for getting users."""

    search: Optional[str] = Field(None, description="Search query to filter users")
    is_active: Optional[bool] = Field(None, description="Filter by user active status")
    limit: int = Field(20, description="Maximum number of users to return")


@router.post(
    "/authentik_get_users",
    response_model=ToolResponse,
    summary="Get Authentik users",
    description="Get list of users from Authentik with optional search and filtering.",
)
async def authentik_get_users(
    request: Request,
    body: AuthentikGetUsersRequest = AuthentikGetUsersRequest(),
    session: AsyncSession = Depends(get_db_session),
):
    """Get Authentik users."""
    result = await execute_tool_with_logging(
        session, "authentik_get_users", body.model_dump(exclude_none=True), request
    )
    return ToolResponse(**result)


class AuthentikGetUserRequest(BaseModel):
    """Request for getting a specific user."""

    user_pk: int = Field(..., description="User primary key (ID)")


@router.post(
    "/authentik_get_user",
    response_model=ToolResponse,
    summary="Get Authentik user",
    description="Get details of a specific user by their ID.",
)
async def authentik_get_user(
    request: Request, body: AuthentikGetUserRequest, session: AsyncSession = Depends(get_db_session)
):
    """Get Authentik user."""
    result = await execute_tool_with_logging(session, "authentik_get_user", body.model_dump(), request)
    return ToolResponse(**result)


class AuthentikSearchUsersRequest(BaseModel):
    """Search request for users."""

    query: str = Field(..., description="Search query")


@router.post(
    "/authentik_search_users",
    response_model=ToolResponse,
    summary="Search Authentik users",
    description="Search for users by username, name, or email.",
)
async def authentik_search_users(
    request: Request, body: AuthentikSearchUsersRequest, session: AsyncSession = Depends(get_db_session)
):
    """Search Authentik users."""
    result = await execute_tool_with_logging(session, "authentik_search_users", body.model_dump(), request)
    return ToolResponse(**result)


class AuthentikGetGroupsRequest(BaseModel):
    """Request for getting groups."""

    limit: int = Field(20, description="Maximum number of groups to return")


@router.post(
    "/authentik_get_groups",
    response_model=ToolResponse,
    summary="Get Authentik groups",
    description="Get list of groups from Authentik.",
)
async def authentik_get_groups(
    request: Request,
    body: AuthentikGetGroupsRequest = AuthentikGetGroupsRequest(),
    session: AsyncSession = Depends(get_db_session),
):
    """Get Authentik groups."""
    result = await execute_tool_with_logging(session, "authentik_get_groups", body.model_dump(), request)
    return ToolResponse(**result)


class AuthentikGetApplicationsRequest(BaseModel):
    """Request for getting applications."""

    limit: int = Field(20, description="Maximum number of applications to return")


@router.post(
    "/authentik_get_applications",
    response_model=ToolResponse,
    summary="Get Authentik applications",
    description="Get list of applications configured in Authentik.",
)
async def authentik_get_applications(
    request: Request,
    body: AuthentikGetApplicationsRequest = AuthentikGetApplicationsRequest(),
    session: AsyncSession = Depends(get_db_session),
):
    """Get Authentik applications."""
    result = await execute_tool_with_logging(session, "authentik_get_applications", body.model_dump(), request)
    return ToolResponse(**result)


class AuthentikGetEventsRequest(BaseModel):
    """Request for getting events."""

    action: Optional[str] = Field(None, description="Filter by action type")
    username: Optional[str] = Field(None, description="Filter by username")
    limit: int = Field(20, description="Maximum number of events to return")


@router.post(
    "/authentik_get_events",
    response_model=ToolResponse,
    summary="Get Authentik events",
    description="Get audit events from Authentik.",
)
async def authentik_get_events(
    request: Request,
    body: AuthentikGetEventsRequest = AuthentikGetEventsRequest(),
    session: AsyncSession = Depends(get_db_session),
):
    """Get Authentik events."""
    result = await execute_tool_with_logging(
        session, "authentik_get_events", body.model_dump(exclude_none=True), request
    )
    return ToolResponse(**result)


@router.post(
    "/authentik_get_statistics",
    response_model=ToolResponse,
    summary="Get Authentik statistics",
    description="Get Authentik statistics including user counts, groups, applications, and recent activity.",
)
async def authentik_get_statistics(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Authentik statistics."""
    result = await execute_tool_with_logging(session, "authentik_get_statistics", {}, request)
    return ToolResponse(**result)


@router.post(
    "/authentik_get_server_info",
    response_model=ToolResponse,
    summary="Get Authentik server info",
    description="Get Authentik server information including version and current user.",
)
async def authentik_get_server_info(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Authentik server info."""
    result = await execute_tool_with_logging(session, "authentik_get_server_info", {}, request)
    return ToolResponse(**result)


class AuthentikDeactivateUserRequest(BaseModel):
    """Request for deactivating a user."""

    user_pk: int = Field(..., description="User primary key (ID) to deactivate")


@router.post(
    "/authentik_deactivate_user",
    response_model=ToolResponse,
    summary="Deactivate Authentik user",
    description="Deactivate a user account (set is_active to false).",
)
async def authentik_deactivate_user(
    request: Request, body: AuthentikDeactivateUserRequest, session: AsyncSession = Depends(get_db_session)
):
    """Deactivate Authentik user."""
    result = await execute_tool_with_logging(session, "authentik_deactivate_user", body.model_dump(), request)
    return ToolResponse(**result)


# ============================================================================
# Indexer Tools (Radarr, Sonarr, Prowlarr, Jackett)
# ============================================================================


@router.post(
    "/radarr_get_indexers",
    response_model=ToolResponse,
    summary="Get Radarr indexers",
    description="Get list of configured indexers in Radarr.",
)
async def radarr_get_indexers(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Radarr indexers."""
    result = await execute_tool_with_logging(session, "radarr_get_indexers", {}, request)
    return ToolResponse(**result)


@router.post(
    "/radarr_test_indexer",
    response_model=ToolResponse,
    summary="Test Radarr indexer",
    description="Test connectivity to a specific indexer in Radarr.",
)
async def radarr_test_indexer(
    request: Request,
    body: dict = {"indexer_id": Field(..., description="ID of the indexer to test")},
    session: AsyncSession = Depends(get_db_session),
):
    """Test Radarr indexer."""
    result = await execute_tool_with_logging(session, "radarr_test_indexer", body, request)
    return ToolResponse(**result)


@router.post(
    "/radarr_test_all_indexers",
    response_model=ToolResponse,
    summary="Test all Radarr indexers",
    description="Test connectivity to all configured indexers in Radarr.",
)
async def radarr_test_all_indexers(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Test all Radarr indexers."""
    result = await execute_tool_with_logging(session, "radarr_test_all_indexers", {}, request)
    return ToolResponse(**result)


@router.post(
    "/sonarr_get_indexers",
    response_model=ToolResponse,
    summary="Get Sonarr indexers",
    description="Get list of configured indexers in Sonarr.",
)
async def sonarr_get_indexers(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Sonarr indexers."""
    result = await execute_tool_with_logging(session, "sonarr_get_indexers", {}, request)
    return ToolResponse(**result)


@router.post(
    "/sonarr_test_indexer",
    response_model=ToolResponse,
    summary="Test Sonarr indexer",
    description="Test connectivity to a specific indexer in Sonarr.",
)
async def sonarr_test_indexer(
    request: Request,
    body: dict = {"indexer_id": Field(..., description="ID of the indexer to test")},
    session: AsyncSession = Depends(get_db_session),
):
    """Test Sonarr indexer."""
    result = await execute_tool_with_logging(session, "sonarr_test_indexer", body, request)
    return ToolResponse(**result)


@router.post(
    "/sonarr_test_all_indexers",
    response_model=ToolResponse,
    summary="Test all Sonarr indexers",
    description="Test connectivity to all configured indexers in Sonarr.",
)
async def sonarr_test_all_indexers(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Test all Sonarr indexers."""
    result = await execute_tool_with_logging(session, "sonarr_test_all_indexers", {}, request)
    return ToolResponse(**result)


@router.post(
    "/prowlarr_test_indexer",
    response_model=ToolResponse,
    summary="Test Prowlarr indexer",
    description="Test connectivity to a specific indexer in Prowlarr.",
)
async def prowlarr_test_indexer(
    request: Request,
    body: dict = {"indexer_id": Field(..., description="ID of the indexer to test")},
    session: AsyncSession = Depends(get_db_session),
):
    """Test Prowlarr indexer."""
    result = await execute_tool_with_logging(session, "prowlarr_test_indexer", body, request)
    return ToolResponse(**result)


@router.post(
    "/prowlarr_test_all_indexers",
    response_model=ToolResponse,
    summary="Test all Prowlarr indexers",
    description="Test connectivity to all configured indexers in Prowlarr.",
)
async def prowlarr_test_all_indexers(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Test all Prowlarr indexers."""
    result = await execute_tool_with_logging(session, "prowlarr_test_all_indexers", {}, request)
    return ToolResponse(**result)


@router.post(
    "/prowlarr_get_applications",
    response_model=ToolResponse,
    summary="Get Prowlarr applications",
    description="Get list of applications connected to Prowlarr (Radarr, Sonarr, etc.).",
)
async def prowlarr_get_applications(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Prowlarr applications."""
    result = await execute_tool_with_logging(session, "prowlarr_get_applications", {}, request)
    return ToolResponse(**result)


@router.post(
    "/prowlarr_get_indexer_stats",
    response_model=ToolResponse,
    summary="Get Prowlarr indexer statistics",
    description="Get statistics for all indexers in Prowlarr.",
)
async def prowlarr_get_indexer_stats(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Prowlarr indexer stats."""
    result = await execute_tool_with_logging(session, "prowlarr_get_indexer_stats", {}, request)
    return ToolResponse(**result)


@router.post(
    "/jackett_get_indexers",
    response_model=ToolResponse,
    summary="Get Jackett indexers",
    description="Get list of configured indexers in Jackett.",
)
async def jackett_get_indexers(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Jackett indexers."""
    result = await execute_tool_with_logging(session, "jackett_get_indexers", {}, request)
    return ToolResponse(**result)


class JackettSearchRequest(BaseModel):
    """Search request for Jackett."""

    query: str = Field(..., description="Search query")
    indexer_ids: Optional[str] = Field(None, description="Comma-separated indexer IDs (optional)")
    categories: Optional[str] = Field(None, description="Comma-separated category IDs (optional)")


@router.post(
    "/jackett_search",
    response_model=ToolResponse,
    summary="Search Jackett",
    description="Search across Jackett indexers.",
)
async def jackett_search(request: Request, body: JackettSearchRequest, session: AsyncSession = Depends(get_db_session)):
    """Search in Jackett."""
    result = await execute_tool_with_logging(session, "jackett_search", body.model_dump(exclude_none=True), request)
    return ToolResponse(**result)


@router.post(
    "/jackett_test_indexer",
    response_model=ToolResponse,
    summary="Test Jackett indexer",
    description="Test connectivity to a specific indexer in Jackett.",
)
async def jackett_test_indexer(
    request: Request,
    body: dict = {"indexer_id": Field(..., description="ID of the indexer to test")},
    session: AsyncSession = Depends(get_db_session),
):
    """Test Jackett indexer."""
    result = await execute_tool_with_logging(session, "jackett_test_indexer", body, request)
    return ToolResponse(**result)


@router.post(
    "/jackett_test_all_indexers",
    response_model=ToolResponse,
    summary="Test all Jackett indexers",
    description="Test connectivity to all configured indexers in Jackett.",
)
async def jackett_test_all_indexers(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Test all Jackett indexers."""
    result = await execute_tool_with_logging(session, "jackett_test_all_indexers", {}, request)
    return ToolResponse(**result)


@router.post(
    "/jackett_get_statistics",
    response_model=ToolResponse,
    summary="Get Jackett statistics",
    description="Get Jackett indexer statistics.",
)
async def jackett_get_statistics(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Jackett statistics."""
    result = await execute_tool_with_logging(session, "jackett_get_statistics", {}, request)
    return ToolResponse(**result)


# ============================================================================
# Deluge Tools
# ============================================================================


class DelugeAddTorrentRequest(BaseModel):
    """Add torrent request."""

    magnet_or_url: str = Field(..., description="Magnet link or torrent URL")


@router.post(
    "/deluge_get_torrents",
    response_model=ToolResponse,
    summary="Get Deluge torrents",
    description="Get list of torrents in Deluge.",
)
async def deluge_get_torrents(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Deluge torrents."""
    result = await execute_tool_with_logging(session, "deluge_get_torrents", {}, request)
    return ToolResponse(**result)


@router.post(
    "/deluge_add_torrent",
    response_model=ToolResponse,
    summary="Add torrent to Deluge",
    description="Add a torrent to Deluge via magnet link or URL.",
)
async def deluge_add_torrent(
    request: Request, body: DelugeAddTorrentRequest, session: AsyncSession = Depends(get_db_session)
):
    """Add torrent to Deluge."""
    result = await execute_tool_with_logging(session, "deluge_add_torrent", body.model_dump(), request)
    return ToolResponse(**result)


class DelugeTorrentRequest(BaseModel):
    """Torrent operation request."""

    torrent_id: str = Field(..., description="Torrent ID/hash")


@router.post(
    "/deluge_pause_torrent",
    response_model=ToolResponse,
    summary="Pause Deluge torrent",
    description="Pause a torrent in Deluge.",
)
async def deluge_pause_torrent(
    request: Request, body: DelugeTorrentRequest, session: AsyncSession = Depends(get_db_session)
):
    """Pause Deluge torrent."""
    result = await execute_tool_with_logging(session, "deluge_pause_torrent", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/deluge_resume_torrent",
    response_model=ToolResponse,
    summary="Resume Deluge torrent",
    description="Resume a paused torrent in Deluge.",
)
async def deluge_resume_torrent(
    request: Request, body: DelugeTorrentRequest, session: AsyncSession = Depends(get_db_session)
):
    """Resume Deluge torrent."""
    result = await execute_tool_with_logging(session, "deluge_resume_torrent", body.model_dump(), request)
    return ToolResponse(**result)


class DelugeRemoveTorrentRequest(BaseModel):
    """Remove torrent request."""

    torrent_id: str = Field(..., description="Torrent ID/hash")
    remove_data: bool = Field(False, description="Also remove downloaded data")


@router.post(
    "/deluge_remove_torrent",
    response_model=ToolResponse,
    summary="Remove Deluge torrent",
    description="Remove a torrent from Deluge.",
)
async def deluge_remove_torrent(
    request: Request, body: DelugeRemoveTorrentRequest, session: AsyncSession = Depends(get_db_session)
):
    """Remove Deluge torrent."""
    result = await execute_tool_with_logging(session, "deluge_remove_torrent", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/deluge_get_statistics",
    response_model=ToolResponse,
    summary="Get Deluge statistics",
    description="Get Deluge client statistics.",
)
async def deluge_get_statistics(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Deluge statistics."""
    result = await execute_tool_with_logging(session, "deluge_get_statistics", {}, request)
    return ToolResponse(**result)


# ============================================================================
# RomM additional tools
# ============================================================================


@router.post(
    "/romm_get_collections",
    response_model=ToolResponse,
    summary="Get RomM collections",
    description="Get list of ROM collections in RomM.",
)
async def romm_get_collections(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get RomM collections."""
    result = await execute_tool_with_logging(session, "romm_get_collections", {}, request)
    return ToolResponse(**result)


@router.post(
    "/romm_get_users",
    response_model=ToolResponse,
    summary="Get RomM users",
    description="Get list of users in RomM.",
)
async def romm_get_users(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get RomM users."""
    result = await execute_tool_with_logging(session, "romm_get_users", {}, request)
    return ToolResponse(**result)


@router.post(
    "/romm_search_roms",
    response_model=ToolResponse,
    summary="Search ROMs",
    description="Search for ROMs by name in RomM.",
)
async def romm_search_roms(request: Request, body: RommSearchRequest, session: AsyncSession = Depends(get_db_session)):
    """Search ROMs in RomM."""
    result = await execute_tool_with_logging(session, "romm_search_roms", body.model_dump(), request)
    return ToolResponse(**result)


# ============================================================================
# System additional tools
# ============================================================================


class SystemGetLogsRequest(BaseModel):
    """Get logs request."""

    level: str = Field("info", description="Log level filter: debug, info, warning, error")
    limit: int = Field(100, description="Maximum number of log entries")


@router.post(
    "/system_get_logs",
    response_model=ToolResponse,
    summary="Get system logs",
    description="Get recent system logs with optional level filtering.",
)
async def system_get_logs(
    request: Request, body: SystemGetLogsRequest = SystemGetLogsRequest(), session: AsyncSession = Depends(get_db_session)
):
    """Get system logs."""
    result = await execute_tool_with_logging(session, "system_get_logs", body.model_dump(), request)
    return ToolResponse(**result)


class SystemGetAlertsRequest(BaseModel):
    """Get alerts request."""

    active_only: bool = Field(True, description="Only return active alerts")


@router.post(
    "/system_get_alerts",
    response_model=ToolResponse,
    summary="Get system alerts",
    description="Get current system alerts.",
)
async def system_get_alerts(
    request: Request,
    body: SystemGetAlertsRequest = SystemGetAlertsRequest(),
    session: AsyncSession = Depends(get_db_session),
):
    """Get system alerts."""
    result = await execute_tool_with_logging(session, "system_get_alerts", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/system_get_services",
    response_model=ToolResponse,
    summary="Get configured services",
    description="Get list of all configured services and their status.",
)
async def system_get_services(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get configured services."""
    result = await execute_tool_with_logging(session, "system_get_services", {}, request)
    return ToolResponse(**result)


@router.post(
    "/system_get_users",
    response_model=ToolResponse,
    summary="Get MCParr users",
    description="Get list of users configured in MCParr.",
)
async def system_get_users(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get MCParr users."""
    result = await execute_tool_with_logging(session, "system_get_users", {}, request)
    return ToolResponse(**result)


class SystemTestServiceRequest(BaseModel):
    """Test service request."""

    service_name: str = Field(..., description="Name of the service to test")


@router.post(
    "/system_test_service",
    response_model=ToolResponse,
    summary="Test service connection",
    description="Test connectivity to a specific service.",
)
async def system_test_service(
    request: Request, body: SystemTestServiceRequest, session: AsyncSession = Depends(get_db_session)
):
    """Test service connection."""
    result = await execute_tool_with_logging(session, "system_test_service", body.model_dump(), request)
    return ToolResponse(**result)


@router.post(
    "/system_test_all_services",
    response_model=ToolResponse,
    summary="Test all services",
    description="Test connectivity to all enabled services and return their status summary.",
)
async def system_test_all_services(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Test all enabled services."""
    result = await execute_tool_with_logging(session, "system_test_all_services", {}, request)
    return ToolResponse(**result)


# ============================================================================
# Overseerr additional tools
# ============================================================================


@router.post(
    "/overseerr_search_media",
    response_model=ToolResponse,
    summary="Search media in Overseerr",
    description="Search for movies or TV shows in Overseerr.",
)
async def overseerr_search_media(
    request: Request, body: OverseerrSearchRequest, session: AsyncSession = Depends(get_db_session)
):
    """Search media in Overseerr."""
    result = await execute_tool_with_logging(session, "overseerr_search_media", body.model_dump(exclude_none=True), request)
    return ToolResponse(**result)


@router.post(
    "/overseerr_check_availability",
    response_model=ToolResponse,
    summary="Check media availability",
    description="Check if a movie or TV show is available in the library.",
)
async def overseerr_check_availability(
    request: Request, body: OverseerrSearchRequest, session: AsyncSession = Depends(get_db_session)
):
    """Check media availability."""
    result = await execute_tool_with_logging(session, "overseerr_check_availability", body.model_dump(exclude_none=True), request)
    return ToolResponse(**result)


@router.post(
    "/overseerr_get_users",
    response_model=ToolResponse,
    summary="Get Overseerr users",
    description="Get list of users in Overseerr.",
)
async def overseerr_get_users(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Overseerr users."""
    result = await execute_tool_with_logging(session, "overseerr_get_users", {}, request)
    return ToolResponse(**result)


@router.post(
    "/overseerr_get_statistics",
    response_model=ToolResponse,
    summary="Get Overseerr statistics",
    description="Get Overseerr request statistics.",
)
async def overseerr_get_statistics(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Get Overseerr statistics."""
    result = await execute_tool_with_logging(session, "overseerr_get_statistics", {}, request)
    return ToolResponse(**result)


# ============================================================================
# Open WebUI Auto-Configuration
# ============================================================================

# Tool filter groups for Open WebUI configuration
# Names are in French for display in Open WebUI interface
OPENWEBUI_TOOL_GROUPS = {
    "media": {
        "name": "MCParr - Média (Plex/Tautulli)",
        "description": "Plex and Tautulli media tools",
        "tools": "plex_get_active_sessions,plex_get_libraries,plex_get_media_details,plex_get_on_deck,plex_get_recently_added,plex_search_media,tautulli_get_activity,tautulli_get_history,tautulli_get_libraries,tautulli_get_recently_added,tautulli_get_server_info,tautulli_get_statistics,tautulli_get_top_movies,tautulli_get_top_music,tautulli_get_top_platforms,tautulli_get_top_tv_shows,tautulli_get_top_users,tautulli_get_user_stats,tautulli_get_users,tautulli_get_watch_stats_summary",
    },
    "books": {
        "name": "MCParr - Livres & Audio",
        "description": "Audiobookshelf and Komga tools",
        "tools": "audiobookshelf_get_libraries,audiobookshelf_get_library_items,audiobookshelf_get_listening_stats,audiobookshelf_get_media_progress,audiobookshelf_get_statistics,audiobookshelf_get_users,audiobookshelf_search,komga_get_libraries,komga_get_statistics,komga_get_users,komga_search",
    },
    "download": {
        "name": "MCParr - Téléchargement",
        "description": "Radarr, Sonarr, Prowlarr, Overseerr, Jackett, and Deluge tools",
        "tools": "deluge_add_torrent,deluge_get_statistics,deluge_get_torrents,deluge_pause_torrent,deluge_remove_torrent,deluge_resume_torrent,jackett_get_indexers,jackett_get_statistics,jackett_search,jackett_test_all_indexers,jackett_test_indexer,overseerr_check_availability,overseerr_get_requests,overseerr_get_statistics,overseerr_get_trending,overseerr_get_users,overseerr_request_media,overseerr_search_media,prowlarr_get_applications,prowlarr_get_indexer_stats,prowlarr_get_indexers,prowlarr_get_statistics,prowlarr_search,prowlarr_test_all_indexers,prowlarr_test_indexer,radarr_get_calendar,radarr_get_indexers,radarr_get_movies,radarr_get_queue,radarr_get_statistics,radarr_search_movie,radarr_test_all_indexers,radarr_test_indexer,sonarr_get_calendar,sonarr_get_indexers,sonarr_get_queue,sonarr_get_series,sonarr_get_statistics,sonarr_search_series,sonarr_test_all_indexers,sonarr_test_indexer",
    },
    "games": {
        "name": "MCParr - Jeux (RomM)",
        "description": "RomM ROM management tools",
        "tools": "romm_get_collections,romm_get_platforms,romm_get_recently_added,romm_get_roms,romm_get_statistics,romm_get_users,romm_search_roms",
    },
    "system": {
        "name": "MCParr - Système & Support",
        "description": "System monitoring and Zammad support tools",
        "tools": "system_get_alerts,system_get_health,system_get_logs,system_get_metrics,system_get_services,system_get_users,system_list_tools,system_test_all_services,system_test_service,zammad_add_comment,zammad_create_ticket,zammad_get_ticket_details,zammad_get_ticket_stats,zammad_get_tickets,zammad_search_tickets,zammad_update_ticket_status",
    },
    "knowledge": {
        "name": "MCParr - Connaissances & IA",
        "description": "WikiJS and Open WebUI tools",
        "tools": "openwebui_get_chats,openwebui_get_models,openwebui_get_statistics,openwebui_get_status,openwebui_get_users,openwebui_search_users,wikijs_create_page,wikijs_get_page,wikijs_get_page_tree,wikijs_get_pages,wikijs_get_statistics,wikijs_get_tags,wikijs_get_users,wikijs_search",
    },
    "auth": {
        "name": "MCParr - Authentification (SSO)",
        "description": "Authentik SSO tools",
        "tools": "authentik_deactivate_user,authentik_get_applications,authentik_get_events,authentik_get_groups,authentik_get_server_info,authentik_get_statistics,authentik_get_user,authentik_get_users,authentik_search_users",
    },
}


class OpenWebUIAutoConfigRequest(BaseModel):
    """Request for auto-configuring Open WebUI."""

    mcparr_external_url: str = Field(..., description="External URL of MCParr (e.g., https://mcparr.example.com)")
    groups: Optional[list[str]] = Field(
        None, description="Specific groups to configure (default: all). Options: media, books, download, games, system, knowledge, auth"
    )
    replace_existing: bool = Field(
        False, description="Replace existing MCParr tool connections (default: append)"
    )


class OpenWebUIAutoConfigResponse(BaseModel):
    """Response for auto-configuration."""

    success: bool
    message: str
    configured_groups: list[str] = []
    total_tools: int = 0
    errors: list[str] = []


@router.post(
    "/configure_openwebui",
    response_model=OpenWebUIAutoConfigResponse,
    summary="Auto-configure Open WebUI tools",
    description="Automatically configure Open WebUI external tool connections for MCParr. Requires Open WebUI service to be configured with admin API key.",
    include_in_schema=False,
)
async def configure_openwebui(
    request: Request, body: OpenWebUIAutoConfigRequest, session: AsyncSession = Depends(get_db_session)
) -> OpenWebUIAutoConfigResponse:
    """
    Automatically configure Open WebUI with MCParr tool connections.

    This endpoint:
    1. Verifies Open WebUI service is configured and accessible
    2. Gets existing tool server connections
    3. Creates/updates MCParr tool connections by category
    4. Returns status of configuration
    """
    errors = []
    configured_groups = []
    total_tools = 0

    # Get Open WebUI service configuration
    result = await session.execute(
        select(ServiceConfig).where(
            ServiceConfig.service_type == "openwebui",
            ServiceConfig.enabled == True,
        )
    )
    openwebui_config = result.scalar_one_or_none()

    if not openwebui_config:
        return OpenWebUIAutoConfigResponse(
            success=False,
            message="Open WebUI service not configured or not enabled in MCParr",
            errors=["Please configure Open WebUI service first in the Services tab"],
        )

    # Build Open WebUI API URL
    openwebui_url = openwebui_config.base_url.rstrip("/")
    if openwebui_config.port:
        openwebui_url = f"{openwebui_url}:{openwebui_config.port}"

    # Get admin API key
    api_key = openwebui_config.api_key
    if not api_key:
        return OpenWebUIAutoConfigResponse(
            success=False,
            message="Open WebUI API key not configured",
            errors=["Please add an admin API key for Open WebUI in the Services tab"],
        )

    # Determine which groups to configure
    groups_to_configure = body.groups if body.groups else list(OPENWEBUI_TOOL_GROUPS.keys())

    # Validate group names
    invalid_groups = [g for g in groups_to_configure if g not in OPENWEBUI_TOOL_GROUPS]
    if invalid_groups:
        return OpenWebUIAutoConfigResponse(
            success=False,
            message=f"Invalid group names: {', '.join(invalid_groups)}",
            errors=[f"Valid groups are: {', '.join(OPENWEBUI_TOOL_GROUPS.keys())}"],
        )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Test Open WebUI connectivity
            try:
                test_response = await client.get(
                    f"{openwebui_url}/api/v1/auths/",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if test_response.status_code != 200:
                    return OpenWebUIAutoConfigResponse(
                        success=False,
                        message="Cannot connect to Open WebUI API",
                        errors=[f"API returned status {test_response.status_code}. Check API key permissions."],
                    )
            except Exception as e:
                return OpenWebUIAutoConfigResponse(
                    success=False,
                    message="Cannot connect to Open WebUI",
                    errors=[str(e)],
                )

            # Step 2: Get existing tool server connections
            existing_connections = []
            try:
                existing_response = await client.get(
                    f"{openwebui_url}/api/v1/configs/tool_servers",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if existing_response.status_code == 200:
                    data = existing_response.json()
                    existing_connections = data.get("TOOL_SERVER_CONNECTIONS", [])
            except Exception as e:
                logger.warning(f"Could not get existing connections: {e}")

            # Step 3: Build new connections
            mcparr_url = body.mcparr_external_url.rstrip("/")
            new_connections = []

            # Always filter out existing MCParr connections to avoid duplicates
            # Keep all non-MCParr connections intact
            non_mcparr_connections = [
                c for c in existing_connections
                if not c.get("url", "").startswith(mcparr_url)
                and not c.get("name", "").startswith("MCParr")
            ]

            logger.info(
                f"[OpenWebUI Config] Keeping {len(non_mcparr_connections)} non-MCParr connections, "
                f"replacing {len(existing_connections) - len(non_mcparr_connections)} MCParr connections"
            )

            for group_id in groups_to_configure:
                group_config = OPENWEBUI_TOOL_GROUPS[group_id]
                tools_list = group_config["tools"]
                tool_count = len(tools_list.split(","))

                connection = {
                    "url": mcparr_url,
                    "path": "/tools/openapi.json",
                    "type": "openapi",
                    "auth_type": "session",
                    "key": "",
                    "config": {
                        "function_name_filter_list": tools_list,
                    },
                    # Display info in Open WebUI interface ("Nom d'utilisateur" field)
                    "info": {
                        "name": group_config["name"],
                        "description": group_config["description"],
                    },
                }

                new_connections.append(connection)
                configured_groups.append(group_id)
                total_tools += tool_count
                logger.info(f"[OpenWebUI Config] Added group '{group_config['name']}' with {tool_count} tools")

            # Step 4: Combine non-MCParr connections with new MCParr connections
            all_connections = non_mcparr_connections + new_connections

            # Step 5: Update Open WebUI configuration
            update_response = await client.post(
                f"{openwebui_url}/api/v1/configs/tool_servers",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={"TOOL_SERVER_CONNECTIONS": all_connections},
            )

            if update_response.status_code != 200:
                return OpenWebUIAutoConfigResponse(
                    success=False,
                    message="Failed to update Open WebUI configuration",
                    errors=[f"API returned status {update_response.status_code}: {update_response.text}"],
                )

            return OpenWebUIAutoConfigResponse(
                success=True,
                message=f"Successfully configured {len(configured_groups)} tool groups with {total_tools} tools",
                configured_groups=configured_groups,
                total_tools=total_tools,
            )

    except Exception as e:
        logger.error(f"[OpenWebUI Config] Error: {e}")
        return OpenWebUIAutoConfigResponse(
            success=False,
            message="Error configuring Open WebUI",
            errors=[str(e)],
        )
