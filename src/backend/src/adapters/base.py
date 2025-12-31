"""Base adapter class for homelab service integrations."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import httpx

if TYPE_CHECKING:
    from src.models.service_config import ServiceConfig

logger = logging.getLogger(__name__)


class ConnectionTestResult:
    """Result of a service connection test."""

    def __init__(
        self,
        success: bool,
        message: Optional[str] = None,
        response_time_ms: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.message = message
        self.response_time_ms = response_time_ms
        self.details = details or {}
        self.tested_at = datetime.utcnow()


class ServiceCapability(Enum):
    """Capabilities that a service adapter can provide."""

    USER_MANAGEMENT = "user_management"
    MEDIA_CONTENT = "media_content"
    TICKET_SYSTEM = "ticket_system"
    MONITORING = "monitoring"
    AUTHENTICATION = "authentication"
    API_ACCESS = "api_access"


class BaseServiceAdapter(ABC):
    """Base class for all service adapters."""

    def __init__(self, service_config: "ServiceConfig", timeout: int = 30, verify_ssl: bool = True):
        """Initialize the adapter.

        Args:
            service_config: Service configuration object
            timeout: HTTP request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.service_config = service_config
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")

        # Initialize HTTP client
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self._client is None:
            headers = self.get_auth_headers()
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
                follow_redirects=True,
            )

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def base_url(self) -> str:
        """Get the base URL for the service."""
        url = self.service_config.base_url
        if self.service_config.port:
            if ":" not in url.split("://", 1)[1]:  # No port specified
                url = f"{url}:{self.service_config.port}"
        return url

    @property
    @abstractmethod
    def service_type(self) -> str:
        """Get the service type identifier."""
        pass

    @property
    @abstractmethod
    def supported_capabilities(self) -> List[ServiceCapability]:
        """Get list of capabilities this adapter supports."""
        pass

    @abstractmethod
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        pass

    @abstractmethod
    async def test_connection(self) -> ConnectionTestResult:
        """Test connection to the service."""
        pass

    @abstractmethod
    async def get_service_info(self) -> Dict[str, Any]:
        """Get basic service information."""
        pass

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Make an HTTP request to the service.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (will be appended to base_url)
            **kwargs: Additional arguments for httpx request

        Returns:
            HTTP response

        Raises:
            httpx.RequestError: For network errors
            httpx.HTTPStatusError: For HTTP errors
        """
        await self._ensure_client()

        start_time = datetime.utcnow()
        try:
            response = await self._client.request(method, endpoint, **kwargs)
            response.raise_for_status()

            end_time = datetime.utcnow()
            response_time = int((end_time - start_time).total_seconds() * 1000)

            self.logger.debug(f"{method} {endpoint} - {response.status_code} ({response_time:.1f}ms)")

            return response

        except httpx.RequestError as e:
            self.logger.error(f"Request failed: {method} {endpoint} - {e}")
            raise
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error: {method} {endpoint} - " f"{e.response.status_code} {e.response.text}")
            raise

    async def _safe_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make a safe HTTP request that returns None on error.

        Useful for optional operations where failures shouldn't crash the adapter.
        """
        try:
            response = await self._make_request(method, endpoint, **kwargs)
            return response.json() if response.content else None
        except Exception as e:
            self.logger.warning(f"Safe request failed: {method} {endpoint} - {e}")
            return None

    def has_capability(self, capability: ServiceCapability) -> bool:
        """Check if this adapter supports a specific capability."""
        return capability in self.supported_capabilities

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with optional default."""
        return self.service_config.get_config_value(key, default)

    def validate_config(self) -> List[str]:
        """Validate the service configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Basic validation
        if not self.service_config.base_url:
            errors.append("Base URL is required")

        if not self.service_config.base_url.startswith(("http://", "https://")):
            errors.append("Base URL must start with http:// or https://")

        return errors


class AuthenticatedAdapter(BaseServiceAdapter):
    """Base class for adapters that require authentication."""

    @abstractmethod
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        pass

    @abstractmethod
    async def validate_auth(self) -> bool:
        """Validate authentication credentials."""
        pass


class TokenAuthAdapter(AuthenticatedAdapter):
    """Base class for token-based authentication."""

    @property
    @abstractmethod
    def token_config_key(self) -> str:
        """Configuration key for the auth token."""
        pass

    def get_auth_headers(self) -> Dict[str, str]:
        """Get token-based auth headers."""
        # First try to get token from api_key field
        token = self.service_config.api_key

        # Fall back to config if api_key is not set
        if not token:
            token = self.get_config_value(self.token_config_key)

        if not token:
            return {}

        return self._format_token_header(token)

    @abstractmethod
    def _format_token_header(self, token: str) -> Dict[str, str]:
        """Format the token into appropriate headers."""
        pass

    async def validate_auth(self) -> bool:
        """Validate token authentication."""
        try:
            # Try to get service info as auth test
            await self.get_service_info()
            return True
        except Exception as e:
            self.logger.warning(f"Auth validation failed: {e}")
            return False


class BasicAuthAdapter(AuthenticatedAdapter):
    """Base class for basic authentication (username/password)."""

    @property
    @abstractmethod
    def username_config_key(self) -> str:
        """Configuration key for username."""
        pass

    @property
    @abstractmethod
    def password_config_key(self) -> str:
        """Configuration key for password."""
        pass

    def get_auth_headers(self) -> Dict[str, str]:
        """Get basic auth headers."""
        username = self.get_config_value(self.username_config_key)
        password = self.get_config_value(self.password_config_key)

        if not username or not password:
            return {}

        import base64

        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        return {"Authorization": f"Basic {credentials}"}

    async def validate_auth(self) -> bool:
        """Validate basic authentication."""
        try:
            await self.get_service_info()
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return False
            raise
        except Exception as e:
            self.logger.warning(f"Auth validation failed: {e}")
            return False


# Exception classes for adapters
class AdapterError(Exception):
    """Base exception for adapter errors."""

    pass


class ConnectionError(AdapterError):
    """Connection-related error."""

    pass


class AuthenticationError(AdapterError):
    """Authentication-related error."""

    pass


class ConfigurationError(AdapterError):
    """Configuration-related error."""

    pass
