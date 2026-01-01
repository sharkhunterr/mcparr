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


def generate_openwebui_openapi_spec() -> dict:
    """Generate a simplified OpenAPI 3.0.3 spec compatible with Open WebUI."""
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "MCParr AI Tools",
            "description": "AI tools for homelab services management",
            "version": "1.0.0",
        },
        "paths": {
            "/tools/system_get_health": {
                "post": {
                    "operationId": "system_get_health",
                    "summary": "Get system health status",
                    "description": (
                        "Get overall system health status including CPU, memory, " "disk usage and any issues detected."
                    ),
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/system_get_metrics": {
                "post": {
                    "operationId": "system_get_metrics",
                    "summary": "Get system metrics",
                    "description": (
                        "Get current system resource metrics including CPU, memory, " "disk, network usage and uptime."
                    ),
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/plex_get_libraries": {
                "post": {
                    "operationId": "plex_get_libraries",
                    "summary": "Get Plex libraries",
                    "description": "Get list of all Plex media libraries (Movies, TV Shows, Music, etc.)",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/plex_search_media": {
                "post": {
                    "operationId": "plex_search_media",
                    "summary": "Search Plex media",
                    "description": (
                        "Search for movies, TV shows, or other media in Plex library " "by title, actor, director, etc."
                    ),
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["query"],
                                    "properties": {
                                        "query": {
                                            "type": "string",
                                            "description": "Search query (title, actor, director, etc.)",
                                        },
                                        "media_type": {
                                            "type": "string",
                                            "description": "Type of media: movie, show, episode, artist, album, track",
                                        },
                                        "limit": {
                                            "type": "integer",
                                            "default": 10,
                                            "description": "Maximum number of results to return",
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/plex_get_recently_added": {
                "post": {
                    "operationId": "plex_get_recently_added",
                    "summary": "Get recently added media",
                    "description": "Get recently added media to Plex library. Can filter by library name.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "library_name": {
                                            "type": "string",
                                            "description": "Name of the library (e.g., 'Movies', 'TV Shows')",
                                        },
                                        "limit": {
                                            "type": "integer",
                                            "default": 10,
                                            "description": "Maximum number of items to return",
                                        },
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/plex_get_on_deck": {
                "post": {
                    "operationId": "plex_get_on_deck",
                    "summary": "Get On Deck items",
                    "description": "Get 'On Deck' items (continue watching) for the Plex server.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "limit": {
                                            "type": "integer",
                                            "default": 10,
                                            "description": "Maximum number of items to return",
                                        }
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/plex_get_media_details": {
                "post": {
                    "operationId": "plex_get_media_details",
                    "summary": "Get media details",
                    "description": (
                        "Get detailed information about a specific movie or TV show " "including cast, genres, rating."
                    ),
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["title"],
                                    "properties": {
                                        "title": {"type": "string", "description": "Title of the movie or TV show"},
                                        "year": {
                                            "type": "integer",
                                            "description": "Release year (helps with disambiguation)",
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/plex_get_active_sessions": {
                "post": {
                    "operationId": "plex_get_active_sessions",
                    "summary": "Get active streaming sessions",
                    "description": "Get list of currently active streaming sessions on Plex (who is watching what).",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/overseerr_search": {
                "post": {
                    "operationId": "overseerr_search",
                    "summary": "Search Overseerr",
                    "description": "Search for movies or TV shows in Overseerr to check availability or request.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["query"],
                                    "properties": {
                                        "query": {
                                            "type": "string",
                                            "description": "Search query for movies or TV shows",
                                        },
                                        "media_type": {"type": "string", "description": "Filter by type: movie or tv"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/overseerr_get_requests": {
                "post": {
                    "operationId": "overseerr_get_requests",
                    "summary": "Get Overseerr requests",
                    "description": "Get list of pending and recent media requests from Overseerr.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/overseerr_request_media": {
                "post": {
                    "operationId": "overseerr_request_media",
                    "summary": "Request media on Overseerr",
                    "description": "Request a movie or TV show to be added to the library via Overseerr.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["title", "media_type"],
                                    "properties": {
                                        "title": {"type": "string", "description": "Title of the media to request"},
                                        "media_type": {"type": "string", "description": "Type of media: movie or tv"},
                                        "year": {"type": "integer", "description": "Release year for disambiguation"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/overseerr_get_trending": {
                "post": {
                    "operationId": "overseerr_get_trending",
                    "summary": "Get trending media",
                    "description": "Get trending movies and TV shows from Overseerr.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/tautulli_get_activity": {
                "post": {
                    "operationId": "tautulli_get_activity",
                    "summary": "Get Plex activity",
                    "description": (
                        "Get current Plex streaming activity including active sessions, "
                        "bandwidth usage, and stream counts."
                    ),
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/tautulli_get_history": {
                "post": {
                    "operationId": "tautulli_get_history",
                    "summary": "Get play history",
                    "description": "Get play history from Tautulli with optional user filtering.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "length": {
                                            "type": "integer",
                                            "default": 25,
                                            "description": "Number of history items to return",
                                        },
                                        "user": {"type": "string", "description": "Filter history by username"},
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/tautulli_get_users": {
                "post": {
                    "operationId": "tautulli_get_users",
                    "summary": "Get Plex users",
                    "description": "Get list of all Plex users known to Tautulli with their details and permissions.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/tautulli_get_libraries": {
                "post": {
                    "operationId": "tautulli_get_libraries",
                    "summary": "Get library statistics",
                    "description": "Get library statistics from Tautulli including item counts and types.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/tautulli_get_statistics": {
                "post": {
                    "operationId": "tautulli_get_statistics",
                    "summary": "Get comprehensive statistics",
                    "description": (
                        "Get comprehensive statistics including activity, history, " "users, and libraries overview."
                    ),
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/tautulli_get_recently_added": {
                "post": {
                    "operationId": "tautulli_get_recently_added",
                    "summary": "Get recently added via Tautulli",
                    "description": "Get recently added items to Plex libraries via Tautulli.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "count": {
                                            "type": "integer",
                                            "default": 25,
                                            "description": "Number of recently added items to return",
                                        }
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/tautulli_get_server_info": {
                "post": {
                    "operationId": "tautulli_get_server_info",
                    "summary": "Get server info",
                    "description": "Get Tautulli and Plex server information including versions and status.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/tautulli_get_my_stats": {
                "post": {
                    "operationId": "tautulli_get_my_stats",
                    "summary": "Get my personal viewing statistics",
                    "description": (
                        "Get your personal viewing history and statistics from Tautulli. "
                        "Shows movies and TV shows you have watched. "
                        "Requires a user mapping between Open WebUI and Tautulli to be configured."
                    ),
                    "requestBody": {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "length": {
                                            "type": "integer",
                                            "description": "Number of history items to return",
                                            "default": 25,
                                        }
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/tautulli_get_top_users": {
                "post": {
                    "operationId": "tautulli_get_top_users",
                    "summary": "Get top Plex users",
                    "description": "Get top Plex users by play count or watch duration over a specified period.",
                    "requestBody": {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "days": {
                                            "type": "integer",
                                            "description": "Number of days to analyze",
                                            "default": 30,
                                        },
                                        "stats_type": {
                                            "type": "string",
                                            "enum": ["plays", "duration"],
                                            "description": "Type of stats",
                                            "default": "plays",
                                        },
                                        "limit": {
                                            "type": "integer",
                                            "description": "Number of users to return",
                                            "default": 10,
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/tautulli_get_top_movies": {
                "post": {
                    "operationId": "tautulli_get_top_movies",
                    "summary": "Get top watched movies",
                    "description": "Get top watched movies over a specified period, optionally filtered by user.",
                    "requestBody": {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "days": {
                                            "type": "integer",
                                            "description": "Number of days to analyze",
                                            "default": 30,
                                        },
                                        "stats_type": {
                                            "type": "string",
                                            "enum": ["plays", "duration"],
                                            "description": "Type of stats",
                                            "default": "plays",
                                        },
                                        "limit": {
                                            "type": "integer",
                                            "description": "Number of movies to return",
                                            "default": 10,
                                        },
                                        "username": {"type": "string", "description": "Filter by username (optional)"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/tautulli_get_top_tv_shows": {
                "post": {
                    "operationId": "tautulli_get_top_tv_shows",
                    "summary": "Get top watched TV shows",
                    "description": "Get top watched TV shows over a specified period, optionally filtered by user.",
                    "requestBody": {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "days": {
                                            "type": "integer",
                                            "description": "Number of days to analyze",
                                            "default": 30,
                                        },
                                        "stats_type": {
                                            "type": "string",
                                            "enum": ["plays", "duration"],
                                            "description": "Type of stats",
                                            "default": "plays",
                                        },
                                        "limit": {
                                            "type": "integer",
                                            "description": "Number of TV shows to return",
                                            "default": 10,
                                        },
                                        "username": {"type": "string", "description": "Filter by username (optional)"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/tautulli_get_top_music": {
                "post": {
                    "operationId": "tautulli_get_top_music",
                    "summary": "Get top listened music",
                    "description": "Get top listened music over a specified period, optionally filtered by user.",
                    "requestBody": {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "days": {
                                            "type": "integer",
                                            "description": "Number of days to analyze",
                                            "default": 30,
                                        },
                                        "stats_type": {
                                            "type": "string",
                                            "enum": ["plays", "duration"],
                                            "description": "Type of stats",
                                            "default": "plays",
                                        },
                                        "limit": {
                                            "type": "integer",
                                            "description": "Number of music items to return",
                                            "default": 10,
                                        },
                                        "username": {"type": "string", "description": "Filter by username (optional)"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/tautulli_get_top_platforms": {
                "post": {
                    "operationId": "tautulli_get_top_platforms",
                    "summary": "Get top streaming platforms",
                    "description": "Get most used platforms/devices for streaming over a specified period.",
                    "requestBody": {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "days": {
                                            "type": "integer",
                                            "description": "Number of days to analyze",
                                            "default": 30,
                                        },
                                        "stats_type": {
                                            "type": "string",
                                            "enum": ["plays", "duration"],
                                            "description": "Type of stats",
                                            "default": "plays",
                                        },
                                        "limit": {
                                            "type": "integer",
                                            "description": "Number of platforms to return",
                                            "default": 10,
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/tautulli_get_user_stats": {
                "post": {
                    "operationId": "tautulli_get_user_stats",
                    "summary": "Get user statistics",
                    "description": (
                        "Get detailed watch statistics for a specific user "
                        "including watch time, top content, and devices."
                    ),
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["username"],
                                    "properties": {
                                        "username": {
                                            "type": "string",
                                            "description": "Username or friendly name of the user",
                                        },
                                        "days": {
                                            "type": "integer",
                                            "description": "Number of days to analyze",
                                            "default": 30,
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/tautulli_get_watch_stats_summary": {
                "post": {
                    "operationId": "tautulli_get_watch_stats_summary",
                    "summary": "Get watch statistics summary",
                    "description": (
                        "Get a comprehensive summary of watch statistics "
                        "including top users, movies, TV shows, and platforms."
                    ),
                    "requestBody": {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "days": {
                                            "type": "integer",
                                            "description": "Number of days to analyze",
                                            "default": 30,
                                        },
                                        "stats_type": {
                                            "type": "string",
                                            "enum": ["plays", "duration"],
                                            "description": "Type of stats",
                                            "default": "plays",
                                        },
                                        "limit": {
                                            "type": "integer",
                                            "description": "Number of items per category",
                                            "default": 5,
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/zammad_get_tickets": {
                "post": {
                    "operationId": "zammad_get_tickets",
                    "summary": "Get support tickets",
                    "description": "Get list of support tickets from Zammad with their status.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/zammad_search_tickets": {
                "post": {
                    "operationId": "zammad_search_tickets",
                    "summary": "Search tickets",
                    "description": "Search Zammad tickets by keyword.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["query"],
                                    "properties": {
                                        "query": {"type": "string", "description": "Search query for tickets"},
                                        "limit": {
                                            "type": "integer",
                                            "default": 10,
                                            "description": "Maximum number of results",
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/zammad_create_ticket": {
                "post": {
                    "operationId": "zammad_create_ticket",
                    "summary": "Create support ticket",
                    "description": "Create a new support ticket in Zammad.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["title", "body"],
                                    "properties": {
                                        "title": {"type": "string", "description": "Ticket title/subject"},
                                        "body": {"type": "string", "description": "Ticket body/description"},
                                        "customer_email": {"type": "string", "description": "Customer email address"},
                                        "priority": {
                                            "type": "string",
                                            "default": "normal",
                                            "description": "Priority: low, normal, high",
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/zammad_get_organizations": {
                "post": {
                    "operationId": "zammad_get_organizations",
                    "summary": "Get organizations",
                    "description": "Get list of organizations from Zammad.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/zammad_get_users": {
                "post": {
                    "operationId": "zammad_get_users",
                    "summary": "Get Zammad users",
                    "description": "Get list of users from Zammad.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/zammad_get_ticket_details": {
                "post": {
                    "operationId": "zammad_get_ticket_details",
                    "summary": "Get ticket details",
                    "description": "Get detailed information about a specific ticket including all articles/messages.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["ticket_id"],
                                    "properties": {
                                        "ticket_id": {
                                            "type": "integer",
                                            "description": "ID or number of the ticket to retrieve (e.g., 1 or 20001)",
                                        }
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/zammad_add_comment": {
                "post": {
                    "operationId": "zammad_add_comment",
                    "summary": "Add comment to ticket",
                    "description": "Add a comment/reply to an existing ticket.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["ticket_id", "comment"],
                                    "properties": {
                                        "ticket_id": {"type": "integer", "description": "ID of the ticket"},
                                        "comment": {"type": "string", "description": "Comment content"},
                                        "internal": {
                                            "type": "boolean",
                                            "default": False,
                                            "description": "Whether the comment is internal (not visible to customer)",
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/zammad_update_ticket_status": {
                "post": {
                    "operationId": "zammad_update_ticket_status",
                    "summary": "Update ticket status",
                    "description": "Update the status of a ticket (open, pending, closed).",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["ticket_id", "status"],
                                    "properties": {
                                        "ticket_id": {"type": "integer", "description": "ID of the ticket"},
                                        "status": {
                                            "type": "string",
                                            "enum": ["open", "pending", "closed"],
                                            "description": "New status for the ticket",
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/zammad_get_ticket_stats": {
                "post": {
                    "operationId": "zammad_get_ticket_stats",
                    "summary": "Get ticket statistics",
                    "description": "Get statistics about tickets (open count, pending, closed, etc.).",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/openwebui_get_status": {
                "post": {
                    "operationId": "openwebui_get_status",
                    "summary": "Get Open WebUI status",
                    "description": "Get Open WebUI service status including version and current user info.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/openwebui_get_users": {
                "post": {
                    "operationId": "openwebui_get_users",
                    "summary": "Get Open WebUI users",
                    "description": "Get list of all users registered in Open WebUI (requires admin privileges).",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "limit": {
                                            "type": "integer",
                                            "default": 50,
                                            "description": "Maximum number of users to return",
                                        }
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/openwebui_get_models": {
                "post": {
                    "operationId": "openwebui_get_models",
                    "summary": "Get available AI models",
                    "description": "Get list of available AI models in Open WebUI.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/openwebui_get_chats": {
                "post": {
                    "operationId": "openwebui_get_chats",
                    "summary": "Get chat history",
                    "description": "Get chat history for the authenticated user.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "limit": {
                                            "type": "integer",
                                            "default": 20,
                                            "description": "Maximum number of chats to return",
                                        }
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/openwebui_get_statistics": {
                "post": {
                    "operationId": "openwebui_get_statistics",
                    "summary": "Get Open WebUI statistics",
                    "description": "Get Open WebUI statistics including user count, models, and chat activity.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/openwebui_search_users": {
                "post": {
                    "operationId": "openwebui_search_users",
                    "summary": "Search Open WebUI users",
                    "description": "Search for users by email or name in Open WebUI (requires admin privileges).",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["query"],
                                    "properties": {
                                        "query": {"type": "string", "description": "Search query (email or name)"}
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            # ============== ROMM ==============
            "/tools/romm_get_platforms": {
                "post": {
                    "operationId": "romm_get_platforms",
                    "summary": "Get ROM platforms",
                    "description": "Get list of gaming platforms in RomM.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/romm_get_roms": {
                "post": {
                    "operationId": "romm_get_roms",
                    "summary": "Get ROMs",
                    "description": "Get list of ROMs, optionally filtered by platform.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "platform_id": {"type": "integer", "description": "Platform ID to filter"},
                                        "limit": {"type": "integer", "default": 50, "description": "Max results"},
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/romm_search": {
                "post": {
                    "operationId": "romm_search",
                    "summary": "Search ROMs",
                    "description": "Search for ROMs by name.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["query"],
                                    "properties": {"query": {"type": "string", "description": "Search query"}},
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/romm_get_statistics": {
                "post": {
                    "operationId": "romm_get_statistics",
                    "summary": "Get RomM statistics",
                    "description": "Get RomM library statistics.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            # ============== KOMGA ==============
            "/tools/komga_get_libraries": {
                "post": {
                    "operationId": "komga_get_libraries",
                    "summary": "Get Komga libraries",
                    "description": "Get list of comic/manga libraries in Komga.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/komga_get_series": {
                "post": {
                    "operationId": "komga_get_series",
                    "summary": "Get Komga series",
                    "description": "Get list of comic/manga series.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "library_id": {"type": "string", "description": "Library ID to filter"},
                                        "limit": {"type": "integer", "default": 50, "description": "Max results"},
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/komga_search": {
                "post": {
                    "operationId": "komga_search",
                    "summary": "Search Komga",
                    "description": "Search for series and books in Komga.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["query"],
                                    "properties": {"query": {"type": "string", "description": "Search query"}},
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/komga_get_statistics": {
                "post": {
                    "operationId": "komga_get_statistics",
                    "summary": "Get Komga statistics",
                    "description": "Get Komga library statistics.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            # ============== SONARR ==============
            "/tools/sonarr_get_series": {
                "post": {
                    "operationId": "sonarr_get_series",
                    "summary": "Get TV series from Sonarr",
                    "description": "Get list of TV series in Sonarr library.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "limit": {"type": "integer", "default": 50, "description": "Max results"}
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/sonarr_search_series": {
                "post": {
                    "operationId": "sonarr_search_series",
                    "summary": "Search for TV series",
                    "description": "Search for a TV series to add to Sonarr.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["query"],
                                    "properties": {"query": {"type": "string", "description": "TV series title"}},
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/sonarr_get_queue": {
                "post": {
                    "operationId": "sonarr_get_queue",
                    "summary": "Get Sonarr download queue",
                    "description": "Get current download queue in Sonarr.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/sonarr_get_calendar": {
                "post": {
                    "operationId": "sonarr_get_calendar",
                    "summary": "Get Sonarr calendar",
                    "description": "Get upcoming TV episode releases.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "days": {"type": "integer", "default": 7, "description": "Days ahead"}
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/sonarr_get_statistics": {
                "post": {
                    "operationId": "sonarr_get_statistics",
                    "summary": "Get Sonarr statistics",
                    "description": "Get Sonarr library statistics.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            # ============== RADARR ==============
            "/tools/radarr_get_movies": {
                "post": {
                    "operationId": "radarr_get_movies",
                    "summary": "Get movies from Radarr",
                    "description": "Get list of movies in Radarr library.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "limit": {"type": "integer", "default": 50, "description": "Max results"}
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/radarr_search_movie": {
                "post": {
                    "operationId": "radarr_search_movie",
                    "summary": "Search for movie",
                    "description": "Search for a movie to add to Radarr.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["query"],
                                    "properties": {"query": {"type": "string", "description": "Movie title"}},
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/radarr_get_queue": {
                "post": {
                    "operationId": "radarr_get_queue",
                    "summary": "Get Radarr download queue",
                    "description": "Get current download queue in Radarr.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/radarr_get_calendar": {
                "post": {
                    "operationId": "radarr_get_calendar",
                    "summary": "Get Radarr calendar",
                    "description": "Get upcoming movie releases.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "days": {"type": "integer", "default": 7, "description": "Days ahead"}
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/radarr_get_statistics": {
                "post": {
                    "operationId": "radarr_get_statistics",
                    "summary": "Get Radarr statistics",
                    "description": "Get Radarr library statistics.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            # ============== PROWLARR ==============
            "/tools/prowlarr_get_indexers": {
                "post": {
                    "operationId": "prowlarr_get_indexers",
                    "summary": "Get Prowlarr indexers",
                    "description": "Get list of configured indexers.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/prowlarr_search": {
                "post": {
                    "operationId": "prowlarr_search",
                    "summary": "Search in Prowlarr",
                    "description": "Search across all indexers.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["query"],
                                    "properties": {
                                        "query": {"type": "string", "description": "Search query"},
                                        "limit": {"type": "integer", "default": 50, "description": "Max results"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
            "/tools/prowlarr_get_statistics": {
                "post": {
                    "operationId": "prowlarr_get_statistics",
                    "summary": "Get Prowlarr statistics",
                    "description": "Get Prowlarr overall statistics.",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ToolResponse"}}},
                        }
                    },
                }
            },
        },
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


# ============================================================================
# Komga Tools
# ============================================================================


class KomgaSeriesRequest(BaseModel):
    """Get series request."""

    library_id: Optional[str] = Field(None, description="Filter by library ID")
    limit: int = Field(50, description="Maximum number of series to return")


class KomgaSearchRequest(BaseModel):
    """Search Komga request."""

    query: str = Field(..., description="Search query")


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
    "/komga_get_series",
    response_model=ToolResponse,
    summary="Get Komga series",
    description="Get list of comic/manga series.",
)
async def komga_get_series(
    request: Request, body: KomgaSeriesRequest = KomgaSeriesRequest(), session: AsyncSession = Depends(get_db_session)
):
    """Get Komga series."""
    result = await execute_tool_with_logging(session, "komga_get_series", body.model_dump(exclude_none=True), request)
    return ToolResponse(**result)


@router.post(
    "/komga_search",
    response_model=ToolResponse,
    summary="Search Komga",
    description="Search for series and books in Komga.",
)
async def komga_search(request: Request, body: KomgaSearchRequest, session: AsyncSession = Depends(get_db_session)):
    """Search Komga."""
    result = await execute_tool_with_logging(session, "komga_search", body.model_dump(), request)
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

    library_id: str = Field(..., description="Library ID to get items from")
    limit: int = Field(50, description="Maximum number of items to return")
    page: int = Field(0, description="Page number (0-indexed)")


@router.post(
    "/audiobookshelf_get_library_items",
    response_model=ToolResponse,
    summary="Get Audiobookshelf library items",
    description="Get items (audiobooks/podcasts) from a library.",
)
async def audiobookshelf_get_library_items(
    request: Request, body: AudiobookshelfLibraryItemsRequest, session: AsyncSession = Depends(get_db_session)
):
    """Get Audiobookshelf library items."""
    result = await execute_tool_with_logging(session, "audiobookshelf_get_library_items", body.model_dump(), request)
    return ToolResponse(**result)


class AudiobookshelfItemRequest(BaseModel):
    """Request for a specific item."""

    item_id: str = Field(..., description="ID of the audiobook/podcast to get")


@router.post(
    "/audiobookshelf_get_item",
    response_model=ToolResponse,
    summary="Get Audiobookshelf item",
    description="Get detailed information about a specific audiobook or podcast.",
)
async def audiobookshelf_get_item(
    request: Request, body: AudiobookshelfItemRequest, session: AsyncSession = Depends(get_db_session)
):
    """Get Audiobookshelf item."""
    result = await execute_tool_with_logging(session, "audiobookshelf_get_item", body.model_dump(), request)
    return ToolResponse(**result)


class AudiobookshelfSearchRequest(BaseModel):
    """Search request for Audiobookshelf."""

    library_id: str = Field(..., description="Library ID to search in")
    query: str = Field(..., description="Search query")
    limit: int = Field(25, description="Maximum number of results per category")


@router.post(
    "/audiobookshelf_search",
    response_model=ToolResponse,
    summary="Search Audiobookshelf",
    description="Search for audiobooks, podcasts, authors, or series in a library.",
)
async def audiobookshelf_search(
    request: Request, body: AudiobookshelfSearchRequest, session: AsyncSession = Depends(get_db_session)
):
    """Search in Audiobookshelf."""
    result = await execute_tool_with_logging(session, "audiobookshelf_search", body.model_dump(), request)
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

    library_item_id: str = Field(..., description="ID of the library item")
    episode_id: Optional[str] = Field(None, description="Episode ID for podcasts (optional)")


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
