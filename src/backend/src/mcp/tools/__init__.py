"""MCP Tools for homelab service integration."""

from .base import BaseTool, ToolRegistry
from .deluge_tools import DelugeTools
from .jackett_tools import JackettTools
from .komga_tools import KomgaTools
from .openwebui_tools import OpenWebUITools
from .overseerr_tools import OverseerrTools
from .plex_tools import PlexTools
from .prowlarr_tools import ProwlarrTools
from .radarr_tools import RadarrTools
from .romm_tools import RommTools
from .sonarr_tools import SonarrTools
from .system_tools import SystemTools
from .zammad_tools import ZammadTools

__all__ = [
    "BaseTool",
    "ToolRegistry",
    "PlexTools",
    "OverseerrTools",
    "ZammadTools",
    "SystemTools",
    "OpenWebUITools",
    "RadarrTools",
    "SonarrTools",
    "ProwlarrTools",
    "JackettTools",
    "DelugeTools",
    "KomgaTools",
    "RommTools",
]
