"""Service adapters package."""

from .authentik import AuthentikAdapter
from .base import (
    AdapterError,
    AuthenticationError,
    BaseServiceAdapter,
    ConnectionTestResult,
    ServiceCapability,
    TokenAuthAdapter,
)
from .deluge import DelugeAdapter
from .jackett import JackettAdapter
from .komga import KomgaAdapter
from .ollama import OllamaAdapter
from .openwebui import OpenWebUIAdapter
from .overseerr import OverseerrAdapter
from .plex import PlexAdapter
from .prowlarr import ProwlarrAdapter
from .radarr import RadarrAdapter
from .romm import RommAdapter
from .sonarr import SonarrAdapter
from .tautulli import TautulliAdapter
from .zammad import ZammadAdapter

__all__ = [
    # Base classes
    "BaseServiceAdapter",
    "TokenAuthAdapter",
    "ServiceCapability",
    "ConnectionTestResult",
    "AdapterError",
    "AuthenticationError",
    # Adapters
    "PlexAdapter",
    "OverseerrAdapter",
    "ZammadAdapter",
    "TautulliAdapter",
    "AuthentikAdapter",
    "OpenWebUIAdapter",
    "OllamaAdapter",
    "RadarrAdapter",
    "SonarrAdapter",
    "ProwlarrAdapter",
    "JackettAdapter",
    "DelugeAdapter",
    "KomgaAdapter",
    "RommAdapter",
]
