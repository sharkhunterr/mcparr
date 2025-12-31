"""Service connection testing functionality."""

import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters.audiobookshelf import AudiobookshelfAdapter
from ..adapters.authentik import AuthentikAdapter
from ..adapters.base import BaseServiceAdapter, ConnectionTestResult
from ..adapters.deluge import DelugeAdapter
from ..adapters.jackett import JackettAdapter
from ..adapters.komga import KomgaAdapter
from ..adapters.ollama import OllamaAdapter
from ..adapters.openwebui import OpenWebUIAdapter
from ..adapters.overseerr import OverseerrAdapter
from ..adapters.plex import PlexAdapter
from ..adapters.prowlarr import ProwlarrAdapter
from ..adapters.radarr import RadarrAdapter
from ..adapters.romm import RommAdapter
from ..adapters.sonarr import SonarrAdapter
from ..adapters.tautulli import TautulliAdapter
from ..adapters.wikijs import WikiJSAdapter
from ..adapters.zammad import ZammadAdapter
from ..models.service_config import ServiceConfig, ServiceHealthHistory

logger = logging.getLogger(__name__)


class ServiceTester:
    """Service for testing connections to homelab services."""

    # Registry of available adapters
    ADAPTER_REGISTRY = {
        "plex": PlexAdapter,
        "overseerr": OverseerrAdapter,
        "zammad": ZammadAdapter,
        "tautulli": TautulliAdapter,
        "authentik": AuthentikAdapter,
        "openwebui": OpenWebUIAdapter,
        "ollama": OllamaAdapter,
        "radarr": RadarrAdapter,
        "sonarr": SonarrAdapter,
        "prowlarr": ProwlarrAdapter,
        "jackett": JackettAdapter,
        "deluge": DelugeAdapter,
        "komga": KomgaAdapter,
        "romm": RommAdapter,
        "audiobookshelf": AudiobookshelfAdapter,
        "wikijs": WikiJSAdapter,
    }

    @classmethod
    def get_adapter_for_service(cls, service_config: ServiceConfig) -> Optional[BaseServiceAdapter]:
        """Get the appropriate adapter for a service configuration."""
        adapter_class = cls.ADAPTER_REGISTRY.get(service_config.service_type.lower())
        if not adapter_class:
            logger.warning(f"No adapter found for service type: {service_config.service_type}")
            return None

        try:
            return adapter_class(service_config)
        except Exception as e:
            logger.error(f"Failed to create adapter for service {service_config.id}: {e}")
            return None

    @classmethod
    async def test_service_connection(
        cls, service_config: ServiceConfig, db_session: Optional[AsyncSession] = None
    ) -> ConnectionTestResult:
        """Test connection to a service using its adapter."""
        logger.info(f"Testing connection to service: {service_config.name} ({service_config.service_type})")

        # Get the appropriate adapter
        adapter = cls.get_adapter_for_service(service_config)
        if not adapter:
            return ConnectionTestResult(
                success=False,
                message=f"No adapter available for service type: {service_config.service_type}",
                details={"error": "unsupported_service_type"},
            )

        try:
            # Test the connection using the adapter
            async with adapter:
                result = await adapter.test_connection()

            # Update service with test results if database session is provided
            if db_session:
                try:
                    service_config.update_test_result(
                        success=result.success, error=result.message if not result.success else None
                    )

                    # Store health history record
                    health_record = ServiceHealthHistory(
                        service_id=service_config.id,
                        success=result.success,
                        response_time_ms=result.response_time_ms,
                        error_message=result.message if not result.success else None,
                    )
                    db_session.add(health_record)

                    await db_session.commit()
                    logger.info(f"Updated test results for service {service_config.name}")
                except Exception as e:
                    logger.warning(f"Failed to update test results in database: {e}")

            logger.info(
                f"Connection test completed for {service_config.name}: " f"{'SUCCESS' if result.success else 'FAILED'}"
            )

            return result

        except Exception as e:
            logger.error(f"Error testing service {service_config.name}: {e}")

            error_result = ConnectionTestResult(
                success=False,
                message=f"Test failed with error: {str(e)}",
                details={"error": "test_exception", "exception": str(e)},
            )

            # Update service with error if database session is provided
            if db_session:
                try:
                    service_config.update_test_result(success=False, error=str(e))

                    # Store health history record for error
                    health_record = ServiceHealthHistory(
                        service_id=service_config.id, success=False, response_time_ms=None, error_message=str(e)
                    )
                    db_session.add(health_record)

                    await db_session.commit()
                except Exception as db_error:
                    logger.warning(f"Failed to update error in database: {db_error}")

            return error_result

    @classmethod
    async def get_service_info(cls, service_config: ServiceConfig) -> Optional[Dict[str, Any]]:
        """Get detailed service information using its adapter."""
        logger.info(f"Getting service info for: {service_config.name}")

        adapter = cls.get_adapter_for_service(service_config)
        if not adapter:
            return None

        try:
            async with adapter:
                service_info = await adapter.get_service_info()

            logger.info(f"Retrieved service info for {service_config.name}")
            return service_info

        except Exception as e:
            logger.error(f"Error getting service info for {service_config.name}: {e}")
            return None

    @classmethod
    async def get_service_statistics(cls, service_config: ServiceConfig) -> Dict[str, Any]:
        """Get service statistics using its adapter if supported."""
        logger.info(f"Getting statistics for: {service_config.name}")

        adapter = cls.get_adapter_for_service(service_config)
        if not adapter:
            return {"error": "No adapter available"}

        try:
            async with adapter:
                # Check if adapter has statistics method
                if hasattr(adapter, "get_statistics"):
                    stats = await adapter.get_statistics()
                    logger.info(f"Retrieved statistics for {service_config.name}")
                    return stats
                else:
                    return {"error": "Statistics not supported for this service type"}

        except Exception as e:
            logger.error(f"Error getting statistics for {service_config.name}: {e}")
            return {"error": str(e)}

    @classmethod
    def validate_service_config(cls, service_config: ServiceConfig) -> Dict[str, Any]:
        """Validate a service configuration using its adapter."""
        logger.info(f"Validating configuration for: {service_config.name}")

        adapter = cls.get_adapter_for_service(service_config)
        if not adapter:
            return {"valid": False, "errors": [f"No adapter available for service type: {service_config.service_type}"]}

        try:
            errors = adapter.validate_config()
            is_valid = len(errors) == 0

            logger.info(
                f"Configuration validation for {service_config.name}: "
                f"{'VALID' if is_valid else 'INVALID'} ({len(errors)} errors)"
            )

            return {
                "valid": is_valid,
                "errors": errors,
                "service_type": adapter.service_type,
                "supported_capabilities": [cap.value for cap in adapter.supported_capabilities],
            }

        except Exception as e:
            logger.error(f"Error validating configuration for {service_config.name}: {e}")
            return {"valid": False, "errors": [f"Validation failed: {str(e)}"]}

    @classmethod
    def get_supported_service_types(cls) -> Dict[str, Dict[str, Any]]:
        """Get information about all supported service types."""
        supported_types = {}

        for service_type, adapter_class in cls.ADAPTER_REGISTRY.items():
            try:
                # Create a dummy service config to get adapter info
                dummy_config = type(
                    "DummyConfig",
                    (),
                    {
                        "service_type": service_type,
                        "base_url": "http://example.com",
                        "get_config_value": lambda self, key, default=None: default,
                    },
                )()

                adapter = adapter_class(dummy_config)

                supported_types[service_type] = {
                    "name": service_type.title(),
                    "capabilities": [cap.value for cap in adapter.supported_capabilities],
                    "description": f"{service_type.title()} service adapter",
                }

            except Exception as e:
                logger.warning(f"Error getting info for service type {service_type}: {e}")
                supported_types[service_type] = {
                    "name": service_type.title(),
                    "capabilities": [],
                    "description": f"{service_type.title()} service adapter (error loading)",
                }

        return supported_types
