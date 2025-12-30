"""MCP Tools for homelab service integration."""

from .base import BaseTool, ToolRegistry
from .plex_tools import PlexTools
from .overseerr_tools import OverseerrTools
from .zammad_tools import ZammadTools
from .system_tools import SystemTools
from .openwebui_tools import OpenWebUITools
from .radarr_tools import RadarrTools
from .sonarr_tools import SonarrTools
from .prowlarr_tools import ProwlarrTools
from .jackett_tools import JackettTools
from .deluge_tools import DelugeTools
from .komga_tools import KomgaTools
from .romm_tools import RommTools

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
