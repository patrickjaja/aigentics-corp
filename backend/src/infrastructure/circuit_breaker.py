"""Circuit breaker pattern for external service protection.

This module implements the circuit breaker pattern to prevent cascading failures
when external services are unavailable or degraded. The circuit breaker monitors
failures and temporarily blocks requests when the failure threshold is exceeded.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Too many failures, requests are blocked
- HALF_OPEN: Testing if service recovered, limited requests allowed
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Failures before opening
    timeout: int = 60  # Seconds to wait before trying again
    success_threshold: int = 2  # Successes in half-open before closing
    monitoring_period: int = 60  # Period to track failures (seconds)


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""

    pass


class CircuitBreaker:
    """Circuit breaker implementation.

    The circuit breaker tracks failures over a monitoring period and opens
    when the failure threshold is exceeded. After a timeout period, it enters
    half-open state to test if the service has recovered.

    Example:
        breaker = CircuitBreaker(failure_threshold=5, timeout=60)

        @breaker.protected
        async def call_external_api():
            return await external_api.call()

        try:
            result = await call_external_api()
        except CircuitBreakerError:
            # Circuit is open, use fallback
            result = fallback_value
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        success_threshold: int = 2,
        monitoring_period: int = 60,
        name: str = "default",
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before entering half-open state
            success_threshold: Successes needed in half-open to close
            monitoring_period: Period to track failures (seconds)
            name: Name for logging and identification
        """
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            timeout=timeout,
            success_threshold=success_threshold,
            monitoring_period=monitoring_period,
        )
        self.name = name
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.opened_at: Optional[datetime] = None
        self.failure_times: list[datetime] = []
        self._lock = asyncio.Lock()

    async def can_execute(self) -> bool:
        """Check if request can execute through circuit breaker.

        Returns:
            True if request should proceed, False if blocked
        """
        async with self._lock:
            current_time = datetime.utcnow()

            if self.state == CircuitState.CLOSED:
                return True

            elif self.state == CircuitState.OPEN:
                # Check if timeout has elapsed
                if self.opened_at and (
                    current_time - self.opened_at
                ).total_seconds() >= self.config.timeout:
                    logger.info(
                        f"Circuit breaker '{self.name}' entering HALF_OPEN state "
                        f"after {self.config.timeout}s timeout"
                    )
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    return True

                return False

            elif self.state == CircuitState.HALF_OPEN:
                # Allow limited requests to test recovery
                return True

            return False

    async def record_success(self) -> None:
        """Record a successful execution."""
        async with self._lock:
            current_time = datetime.utcnow()

            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                logger.debug(
                    f"Circuit breaker '{self.name}' success in HALF_OPEN: "
                    f"{self.success_count}/{self.config.success_threshold}"
                )

                if self.success_count >= self.config.success_threshold:
                    logger.info(
                        f"Circuit breaker '{self.name}' closing after "
                        f"{self.success_count} consecutive successes"
                    )
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    self.opened_at = None
                    self.failure_times = []

            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success in closed state
                self.failure_count = 0
                self.failure_times = []

    async def record_failure(self) -> None:
        """Record a failed execution."""
        async with self._lock:
            current_time = datetime.utcnow()
            self.last_failure_time = current_time

            # Clean up old failure times outside monitoring period
            cutoff_time = current_time - timedelta(
                seconds=self.config.monitoring_period
            )
            self.failure_times = [
                t for t in self.failure_times if t > cutoff_time
            ]

            # Add new failure
            self.failure_times.append(current_time)
            self.failure_count = len(self.failure_times)

            logger.warning(
                f"Circuit breaker '{self.name}' failure recorded: "
                f"{self.failure_count}/{self.config.failure_threshold} "
                f"in last {self.config.monitoring_period}s"
            )

            if self.state == CircuitState.HALF_OPEN:
                # Failure in half-open means service still degraded
                logger.warning(
                    f"Circuit breaker '{self.name}' reopening after failure "
                    f"in HALF_OPEN state"
                )
                self.state = CircuitState.OPEN
                self.opened_at = current_time
                self.success_count = 0

            elif self.state == CircuitState.CLOSED:
                # Check if we've hit the threshold
                if self.failure_count >= self.config.failure_threshold:
                    logger.error(
                        f"Circuit breaker '{self.name}' OPENING after "
                        f"{self.failure_count} failures in "
                        f"{self.config.monitoring_period}s"
                    )
                    self.state = CircuitState.OPEN
                    self.opened_at = current_time

    def protected(self, func: Callable) -> Callable:
        """Decorator to protect a function with circuit breaker.

        Args:
            func: Function to protect

        Returns:
            Protected function
        """

        async def wrapper(*args, **kwargs):
            if not await self.can_execute():
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is {self.state.value}"
                )

            try:
                result = await func(*args, **kwargs)
                await self.record_success()
                return result

            except Exception as e:
                await self.record_failure()
                raise

        return wrapper

    def get_state(self) -> dict:
        """Get current circuit breaker state.

        Returns:
            Dictionary with state information
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": (
                self.last_failure_time.isoformat()
                if self.last_failure_time
                else None
            ),
            "opened_at": (
                self.opened_at.isoformat() if self.opened_at else None
            ),
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "timeout": self.config.timeout,
                "success_threshold": self.config.success_threshold,
                "monitoring_period": self.config.monitoring_period,
            },
        }

    async def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        async with self._lock:
            logger.info(f"Circuit breaker '{self.name}' manually reset")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.opened_at = None
            self.last_failure_time = None
            self.failure_times = []

    async def force_open(self) -> None:
        """Manually force circuit breaker to open state."""
        async with self._lock:
            logger.warning(f"Circuit breaker '{self.name}' manually opened")
            self.state = CircuitState.OPEN
            self.opened_at = datetime.utcnow()


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers.

    This allows centralized monitoring and control of all circuit breakers
    in the application.
    """

    def __init__(self):
        """Initialize circuit breaker registry."""
        self._breakers: dict[str, CircuitBreaker] = {}

    def register(self, name: str, breaker: CircuitBreaker) -> None:
        """Register a circuit breaker.

        Args:
            name: Unique name for the breaker
            breaker: CircuitBreaker instance
        """
        self._breakers[name] = breaker
        logger.info(f"Registered circuit breaker: {name}")

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name.

        Args:
            name: Name of the breaker

        Returns:
            CircuitBreaker instance or None if not found
        """
        return self._breakers.get(name)

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: int = 60,
    ) -> CircuitBreaker:
        """Get existing breaker or create new one.

        Args:
            name: Name of the breaker
            failure_threshold: Failures before opening
            timeout: Timeout before half-open

        Returns:
            CircuitBreaker instance
        """
        if name not in self._breakers:
            breaker = CircuitBreaker(
                failure_threshold=failure_threshold,
                timeout=timeout,
                name=name,
            )
            self.register(name, breaker)

        return self._breakers[name]

    def get_all_states(self) -> dict[str, dict]:
        """Get state of all circuit breakers.

        Returns:
            Dictionary mapping names to state dicts
        """
        return {name: breaker.get_state() for name, breaker in self._breakers.items()}

    async def reset_all(self) -> None:
        """Reset all circuit breakers to closed state."""
        for breaker in self._breakers.values():
            await breaker.reset()

    def get_open_breakers(self) -> list[str]:
        """Get list of names of open circuit breakers.

        Returns:
            List of breaker names in OPEN state
        """
        return [
            name
            for name, breaker in self._breakers.items()
            if breaker.state == CircuitState.OPEN
        ]


# Global registry instance
_registry: Optional[CircuitBreakerRegistry] = None


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry.

    Returns:
        Global CircuitBreakerRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = CircuitBreakerRegistry()
    return _registry
