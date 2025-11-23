"""
Circuit Breaker Pattern implementation for fault-tolerant inter-service communication.
Part II Enhancement: Enhanced Inter-Service Communication
"""

import time
from enum import Enum
from functools import wraps
from typing import Callable, Any
from utils.logger import setup_logger
from utils.exceptions import CircuitBreakerOpenError

logger = setup_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"  # Circuit is open, requests fail immediately
    HALF_OPEN = "HALF_OPEN"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit Breaker implementation for resilient inter-service communication.

    The circuit breaker prevents cascading failures by:
    - Monitoring failure rates
    - Opening circuit when failure threshold is reached
    - Allowing periodic retry attempts
    - Closing circuit when service recovers

    Attributes:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        expected_exception: Exception type that triggers circuit breaker
    """

    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.

        Args:
            service_name: Name of the service being protected
            failure_threshold: Number of consecutive failures to trigger open state
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type that counts as failure
        """
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

        logger.info(
            f"Circuit breaker initialized for {service_name}",
            extra={
                'service': service_name,
                'failure_threshold': failure_threshold,
                'recovery_timeout': recovery_timeout
            }
        )

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function positional arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception if function fails
        """
        # Check if circuit is open
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                logger.warning(
                    f"Circuit breaker is OPEN for {self.service_name}",
                    extra={
                        'service': self.service_name,
                        'state': self.state.value,
                        'failure_count': self.failure_count
                    }
                )
                raise CircuitBreakerOpenError(self.service_name)

        try:
            # Execute function
            result = func(*args, **kwargs)

            # Record success
            self._on_success()

            return result

        except self.expected_exception as e:
            # Record failure
            self._on_failure()

            logger.error(
                f"Circuit breaker recorded failure for {self.service_name}",
                extra={
                    'service': self.service_name,
                    'state': self.state.value,
                    'failure_count': self.failure_count,
                    'error': str(e)
                }
            )

            raise

    def _should_attempt_reset(self) -> bool:
        """
        Check if enough time has passed to attempt reset.

        Returns:
            Boolean indicating if reset should be attempted
        """
        if self.last_failure_time is None:
            return True

        return time.time() - self.last_failure_time >= self.recovery_timeout

    def _on_success(self):
        """Handle successful function execution."""
        self.success_count += 1

        if self.state == CircuitState.HALF_OPEN:
            # Service has recovered, close the circuit
            self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed function execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Service still failing, reopen circuit
            self._transition_to_open()
        elif self.failure_count >= self.failure_threshold:
            # Threshold reached, open circuit
            self._transition_to_open()

    def _transition_to_open(self):
        """Transition circuit to OPEN state."""
        self.state = CircuitState.OPEN
        logger.warning(
            f"Circuit breaker OPENED for {self.service_name}",
            extra={
                'service': self.service_name,
                'state': self.state.value,
                'failure_count': self.failure_count
            }
        )

    def _transition_to_half_open(self):
        """Transition circuit to HALF_OPEN state."""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        logger.info(
            f"Circuit breaker HALF_OPEN for {self.service_name}",
            extra={
                'service': self.service_name,
                'state': self.state.value
            }
        )

    def _transition_to_closed(self):
        """Transition circuit to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        logger.info(
            f"Circuit breaker CLOSED for {self.service_name}",
            extra={
                'service': self.service_name,
                'state': self.state.value
            }
        )

    def reset(self):
        """Manually reset the circuit breaker."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None

        logger.info(
            f"Circuit breaker manually reset for {self.service_name}",
            extra={'service': self.service_name}
        )

    def get_state(self) -> dict:
        """
        Get current circuit breaker state.

        Returns:
            Dictionary with state information
        """
        return {
            'service': self.service_name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time
        }


# Global circuit breakers for each service
_circuit_breakers = {}


def get_circuit_breaker(service_name: str, **kwargs) -> CircuitBreaker:
    """
    Get or create circuit breaker for a service.

    Args:
        service_name: Name of the service
        **kwargs: Circuit breaker configuration options

    Returns:
        CircuitBreaker instance
    """
    if service_name not in _circuit_breakers:
        _circuit_breakers[service_name] = CircuitBreaker(service_name, **kwargs)

    return _circuit_breakers[service_name]


def with_circuit_breaker(service_name: str, **breaker_kwargs):
    """
    Decorator to protect function with circuit breaker.

    Args:
        service_name: Name of the service
        **breaker_kwargs: Circuit breaker configuration options

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            circuit_breaker = get_circuit_breaker(service_name, **breaker_kwargs)
            return circuit_breaker.call(func, *args, **kwargs)

        return wrapper

    return decorator


def get_all_circuit_states() -> dict:
    """
    Get state of all circuit breakers.

    Returns:
        Dictionary mapping service names to their states
    """
    return {
        name: breaker.get_state()
        for name, breaker in _circuit_breakers.items()
    }
