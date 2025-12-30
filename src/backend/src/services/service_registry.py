"""Service Registry and Discovery System.

This module provides a centralized registry for service adapters,
allowing dynamic discovery and instantiation of service integrations.
"""

from typing import Dict, List, Type, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.service_config import ServiceConfig, ServiceType
from ..adapters.base import BaseServiceAdapter
from ..adapters.plex import PlexAdapter
from ..adapters.tautulli import TautulliAdapter
from ..adapters.overseerr import OverseerrAdapter
from ..adapters.zammad import ZammadAdapter
from ..adapters.authentik import AuthentikAdapter
from ..adapters.openwebui import OpenWebUIAdapter
from ..adapters.komga import KomgaAdapter
from ..adapters.romm import RommAdapter
from ..adapters.audiobookshelf import AudiobookshelfAdapter
from ..adapters.wikijs import WikiJSAdapter


class ServiceRegistry:
    """Registry for managing service adapters and their discovery."""

    def __init__(self):
        """Initialize the service registry with available adapters."""
        self._adapters: Dict[str, Type[BaseServiceAdapter]] = {}
        self._register_default_adapters()

    def _register_default_adapters(self) -> None:
        """Register all available service adapters."""
        # Register known service adapters
        self.register_adapter("plex", PlexAdapter)
        self.register_adapter("tautulli", TautulliAdapter)
        self.register_adapter("overseerr", OverseerrAdapter)
        self.register_adapter("zammad", ZammadAdapter)
        self.register_adapter("authentik", AuthentikAdapter)
        self.register_adapter("openwebui", OpenWebUIAdapter)
        self.register_adapter("komga", KomgaAdapter)
        self.register_adapter("romm", RommAdapter)
        self.register_adapter("audiobookshelf", AudiobookshelfAdapter)
        self.register_adapter("wikijs", WikiJSAdapter)

    def register_adapter(self, service_type: str, adapter_class: Type[BaseServiceAdapter]) -> None:
        """Register a service adapter for a specific service type.

        Args:
            service_type: The type of service this adapter handles
            adapter_class: The adapter class to register
        """
        self._adapters[service_type.lower()] = adapter_class

    def get_adapter_class(self, service_type: str) -> Optional[Type[BaseServiceAdapter]]:
        """Get the adapter class for a specific service type.

        Args:
            service_type: The type of service to get adapter for

        Returns:
            The adapter class if found, None otherwise
        """
        return self._adapters.get(service_type.lower())

    def get_available_service_types(self) -> List[str]:
        """Get list of all available service types."""
        return list(self._adapters.keys())

    def has_adapter(self, service_type: str) -> bool:
        """Check if an adapter is available for the given service type."""
        return service_type.lower() in self._adapters

    async def create_adapter(
        self,
        service_config: ServiceConfig,
        timeout: int = 30,
        verify_ssl: bool = True
    ) -> Optional[BaseServiceAdapter]:
        """Create and return an adapter instance for the given service config.

        Args:
            service_config: Service configuration to create adapter for
            timeout: HTTP request timeout in seconds
            verify_ssl: Whether to verify SSL certificates

        Returns:
            Adapter instance if successful, None if service type not supported
        """
        adapter_class = self.get_adapter_class(service_config.service_type.value if hasattr(service_config.service_type, 'value') else service_config.service_type)
        if not adapter_class:
            return None

        return adapter_class(
            service_config=service_config,
            timeout=timeout,
            verify_ssl=verify_ssl
        )

    async def get_service_capabilities(self, service_type: str) -> List[str]:
        """Get the capabilities supported by a service adapter.

        Args:
            service_type: The service type to check capabilities for

        Returns:
            List of capability names supported by the adapter
        """
        adapter_class = self.get_adapter_class(service_type)
        if not adapter_class:
            return []

        # Create a temporary instance to get capabilities
        # Note: This is a bit of a hack since we need a ServiceConfig
        # In practice, capabilities should be class-level properties
        try:
            # Try to get capabilities without instantiating if possible
            if hasattr(adapter_class, 'supported_capabilities'):
                capabilities = adapter_class.supported_capabilities
                if callable(capabilities):
                    # It's a property or method, we need an instance
                    return []
                else:
                    # It's a class attribute
                    return [cap.value for cap in capabilities]
            return []
        except Exception:
            return []

    async def discover_services(
        self,
        db: AsyncSession,
        service_type: Optional[str] = None
    ) -> List[ServiceConfig]:
        """Discover all configured services, optionally filtered by type.

        Args:
            db: Database session
            service_type: Optional service type to filter by

        Returns:
            List of service configurations
        """
        query = select(ServiceConfig)

        if service_type:
            query = query.where(ServiceConfig.service_type == ServiceType(service_type))

        result = await db.execute(query)
        return result.scalars().all()

    async def test_all_services(self, db: AsyncSession) -> Dict[str, Any]:
        """Test connectivity to all configured services.

        Args:
            db: Database session

        Returns:
            Dictionary with test results for each service
        """
        services = await self.discover_services(db)
        results = {}

        for service in services:
            service_type_str = service.service_type.value if hasattr(service.service_type, 'value') else service.service_type
            if not self.has_adapter(service_type_str):
                results[service.id] = {
                    "success": False,
                    "error": f"No adapter available for service type: {service_type_str}"
                }
                continue

            try:
                adapter = await self.create_adapter(service)
                if adapter:
                    async with adapter:
                        test_result = await adapter.test_connection()
                        results[service.id] = {
                            "success": test_result.success,
                            "message": test_result.message,
                            "response_time_ms": test_result.response_time_ms,
                            "details": test_result.details
                        }
                else:
                    results[service.id] = {
                        "success": False,
                        "error": "Failed to create adapter"
                    }
            except Exception as e:
                results[service.id] = {
                    "success": False,
                    "error": f"Exception during test: {str(e)}"
                }

        return results

    async def get_service_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """Get statistics for all configured services.

        Args:
            db: Database session

        Returns:
            Aggregated statistics across all services
        """
        services = await self.discover_services(db)
        stats = {
            "total_services": len(services),
            "services_by_type": {},
            "active_services": 0,
            "inactive_services": 0,
            "error_services": 0,
            "supported_service_types": self.get_available_service_types()
        }

        for service in services:
            service_type = service.service_type.value if hasattr(service.service_type, 'value') else service.service_type
            stats["services_by_type"][service_type] = stats["services_by_type"].get(service_type, 0) + 1

            if service.status.value if hasattr(service.status, 'value') else service.status == "active":
                stats["active_services"] += 1
            elif service.status.value if hasattr(service.status, 'value') else service.status == "inactive":
                stats["inactive_services"] += 1
            else:
                stats["error_services"] += 1

        return stats

    async def auto_discover_services(
        self,
        network_range: Optional[str] = None,
        common_ports: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """Automatically discover services on the network.

        This is a placeholder for future implementation of network discovery.

        Args:
            network_range: Network range to scan (e.g., "192.168.1.0/24")
            common_ports: List of common ports to check

        Returns:
            List of discovered service candidates
        """
        # TODO: Implement actual network discovery
        # This could use nmap, port scanning, or service-specific discovery methods

        discovered = []

        # Placeholder implementation
        if common_ports is None:
            common_ports = [
                32400,  # Plex
                8096,   # Jellyfin
                5055,   # Overseerr
                8181,   # Tautulli
                8080,   # Various services
                443,    # HTTPS
                80      # HTTP
            ]

        # In a real implementation, this would:
        # 1. Scan the network range for open ports
        # 2. Attempt to identify services by their responses
        # 3. Return candidate services for manual verification

        return discovered

    def validate_service_config(self, service_type: str, config: Dict[str, Any]) -> List[str]:
        """Validate a service configuration for a given service type.

        Args:
            service_type: The service type to validate against
            config: The configuration to validate

        Returns:
            List of validation errors (empty if valid)
        """
        adapter_class = self.get_adapter_class(service_type)
        if not adapter_class:
            return [f"Unknown service type: {service_type}"]

        # Basic validation that all adapters should support
        errors = []

        if not config.get("base_url"):
            errors.append("Base URL is required")

        base_url = config.get("base_url", "")
        if base_url and not base_url.startswith(("http://", "https://")):
            errors.append("Base URL must start with http:// or https://")

        # Port validation
        port = config.get("port")
        if port is not None:
            try:
                port_int = int(port)
                if port_int < 1 or port_int > 65535:
                    errors.append("Port must be between 1 and 65535")
            except (ValueError, TypeError):
                errors.append("Port must be a valid integer")

        return errors


# Global registry instance
service_registry = ServiceRegistry()


async def get_service_registry() -> ServiceRegistry:
    """Get the global service registry instance."""
    return service_registry