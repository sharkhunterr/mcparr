"""Circuit Breaker Pattern Implementation.

This module implements the circuit breaker pattern to improve system resilience
by preventing cascading failures when external services become unavailable.
"""

from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import logging
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Circuit is open, calls are rejected
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""
    failure_threshold: int = 5           # Number of failures before opening
    recovery_timeout: int = 60           # Seconds to wait before testing recovery
    success_threshold: int = 2           # Successes needed to close from half-open
    timeout: float = 30.0               # Request timeout in seconds
    expected_exception: tuple = (Exception,)  # Exceptions that count as failures


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """Circuit breaker implementation for protecting service calls."""

    def __init__(self, name: str, config: CircuitBreakerConfig):
        """Initialize circuit breaker.

        Args:
            name: Unique name for this circuit breaker
            config: Configuration for the circuit breaker
        """
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
        self.call_count = 0
        self._lock = asyncio.Lock()

    async def call(self, func: Callable[[], Awaitable[Any]], *args, **kwargs) -> Any:
        """Execute a function through the circuit breaker.

        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: When circuit is open
            Original exception: When function fails
        """
        async with self._lock:
            await self._update_state()

            if self.state == CircuitState.OPEN:
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Service calls are being rejected."
                )

            self.call_count += 1

        # Execute the function with timeout
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )

            # Record success
            async with self._lock:
                await self._record_success()

            return result

        except self.config.expected_exception as e:
            # Record failure
            async with self._lock:
                await self._record_failure()

            logger.warning(
                f"Circuit breaker '{self.name}' recorded failure: {str(e)}"
            )
            raise

        except asyncio.TimeoutError as e:
            # Timeout is also considered a failure
            async with self._lock:
                await self._record_failure()

            logger.warning(
                f"Circuit breaker '{self.name}' timeout after {self.config.timeout}s"
            )
            raise

    async def _update_state(self) -> None:
        """Update circuit breaker state based on current conditions."""
        now = datetime.utcnow()

        if self.state == CircuitState.OPEN:
            # Check if we should transition to half-open
            if (self.last_failure_time and
                now - self.last_failure_time >= timedelta(seconds=self.config.recovery_timeout)):

                logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0

        elif self.state == CircuitState.HALF_OPEN:
            # In half-open, we allow limited testing
            pass

        # CLOSED state doesn't need special handling here

    async def _record_success(self) -> None:
        """Record a successful call."""
        self.last_success_time = datetime.utcnow()

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                logger.info(f"Circuit breaker '{self.name}' transitioning to CLOSED")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0

        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    async def _record_failure(self) -> None:
        """Record a failed call."""
        self.last_failure_time = datetime.utcnow()
        self.failure_count += 1

        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                logger.warning(
                    f"Circuit breaker '{self.name}' transitioning to OPEN "
                    f"after {self.failure_count} failures"
                )
                self.state = CircuitState.OPEN

        elif self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open goes back to open
            logger.warning(
                f"Circuit breaker '{self.name}' transitioning back to OPEN "
                f"from HALF_OPEN after failure"
            )
            self.state = CircuitState.OPEN
            self.success_count = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics.

        Returns:
            Dictionary with current stats
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "call_count": self.call_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout
            }
        }

    async def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        async with self._lock:
            logger.info(f"Circuit breaker '{self.name}' manually reset to CLOSED")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.call_count = 0
            self.last_failure_time = None
            self.last_success_time = None

    async def force_open(self) -> None:
        """Force circuit breaker to open state."""
        async with self._lock:
            logger.warning(f"Circuit breaker '{self.name}' manually forced to OPEN")
            self.state = CircuitState.OPEN
            self.last_failure_time = datetime.utcnow()


class CircuitBreakerManager:
    """Manager for multiple circuit breakers."""

    def __init__(self):
        """Initialize circuit breaker manager."""
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._default_config = CircuitBreakerConfig()

    def get_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create a circuit breaker.

        Args:
            name: Circuit breaker name
            config: Optional configuration (uses default if not provided)

        Returns:
            CircuitBreaker instance
        """
        if name not in self._breakers:
            breaker_config = config or self._default_config
            self._breakers[name] = CircuitBreaker(name, breaker_config)
            logger.info(f"Created new circuit breaker: {name}")

        return self._breakers[name]

    def remove_breaker(self, name: str) -> bool:
        """Remove a circuit breaker.

        Args:
            name: Circuit breaker name

        Returns:
            True if removed, False if not found
        """
        if name in self._breakers:
            del self._breakers[name]
            logger.info(f"Removed circuit breaker: {name}")
            return True
        return False

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers.

        Returns:
            Dictionary mapping names to stats
        """
        return {name: breaker.get_stats() for name, breaker in self._breakers.items()}

    async def reset_all(self) -> None:
        """Reset all circuit breakers to closed state."""
        for breaker in self._breakers.values():
            await breaker.reset()
        logger.info("All circuit breakers reset")

    def get_breaker_names(self) -> list:
        """Get names of all circuit breakers."""
        return list(self._breakers.keys())


# Global circuit breaker manager
circuit_manager = CircuitBreakerManager()


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    success_threshold: int = 2,
    timeout: float = 30.0,
    expected_exception: tuple = (Exception,)
):
    """Decorator to add circuit breaker protection to async functions.

    Args:
        name: Circuit breaker name
        failure_threshold: Failures before opening
        recovery_timeout: Seconds before testing recovery
        success_threshold: Successes needed to close
        timeout: Request timeout in seconds
        expected_exception: Exceptions that count as failures

    Returns:
        Decorated function with circuit breaker protection
    """
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        success_threshold=success_threshold,
        timeout=timeout,
        expected_exception=expected_exception
    )

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            breaker = circuit_manager.get_breaker(name, config)
            return await breaker.call(func, *args, **kwargs)

        return wrapper

    return decorator


# Service-specific circuit breaker configurations
def get_service_breaker_config(service_type: str) -> CircuitBreakerConfig:
    """Get circuit breaker configuration for a specific service type.

    Args:
        service_type: Type of service

    Returns:
        Appropriate configuration for the service
    """
    service_configs = {
        "plex": CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30,
            success_threshold=2,
            timeout=15.0
        ),
        "tautulli": CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30,
            success_threshold=2,
            timeout=10.0
        ),
        "overseerr": CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            success_threshold=2,
            timeout=20.0
        ),
        "zammad": CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=45,
            success_threshold=2,
            timeout=25.0
        ),
        "authentik": CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30,
            success_threshold=1,
            timeout=15.0
        )
    }

    return service_configs.get(service_type.lower(), CircuitBreakerConfig())


async def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get the global circuit breaker manager."""
    return circuit_manager


# Helper functions for service adapters
async def call_with_circuit_breaker(
    service_name: str,
    service_type: str,
    func: Callable[[], Awaitable[Any]],
    *args,
    **kwargs
) -> Any:
    """Call a function with circuit breaker protection for a specific service.

    Args:
        service_name: Name of the service
        service_type: Type of the service
        func: Function to call
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Raises:
        CircuitBreakerError: When circuit is open
        Original exception: When function fails
    """
    breaker_name = f"{service_type}:{service_name}"
    config = get_service_breaker_config(service_type)
    breaker = circuit_manager.get_breaker(breaker_name, config)

    return await breaker.call(func, *args, **kwargs)