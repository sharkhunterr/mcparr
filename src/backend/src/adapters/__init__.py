"""Service adapters package."""

from .base import (
    BaseServiceAdapter,
    TokenAuthAdapter,
    ServiceCapability,
    ConnectionTestResult,
    AdapterError,
    AuthenticationError
)
from .plex import PlexAdapter
from .overseerr import OverseerrAdapter
from .zammad import ZammadAdapter
from .tautulli import TautulliAdapter
from .authentik import AuthentikAdapter
from .openwebui import OpenWebUIAdapter
from .ollama import OllamaAdapter
from .radarr import RadarrAdapter
from .sonarr import SonarrAdapter
from .prowlarr import ProwlarrAdapter
from .jackett import JackettAdapter
from .deluge import DelugeAdapter
from .komga import KomgaAdapter
from .romm import RommAdapter

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
