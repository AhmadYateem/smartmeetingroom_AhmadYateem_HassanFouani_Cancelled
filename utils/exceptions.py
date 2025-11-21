"""
Custom exception classes for the Smart Meeting Room System.
"""


class SMRException(Exception):
    """Base exception class for Smart Meeting Room System."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(SMRException):
    """Exception raised for validation errors."""

    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class AuthenticationError(SMRException):
    """Exception raised for authentication failures."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class AuthorizationError(SMRException):
    """Exception raised for authorization failures."""

    def __init__(self, message: str = "Access forbidden"):
        super().__init__(message, status_code=403)


class NotFoundError(SMRException):
    """Exception raised when resource is not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ConflictError(SMRException):
    """Exception raised for resource conflicts."""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, status_code=409)


class RateLimitError(SMRException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)


class ServiceUnavailableError(SMRException):
    """Exception raised when service is unavailable."""

    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(message, status_code=503)


class DatabaseError(SMRException):
    """Exception raised for database errors."""

    def __init__(self, message: str = "Database error occurred"):
        super().__init__(message, status_code=500)


class ExternalServiceError(SMRException):
    """Exception raised when external service call fails."""

    def __init__(self, message: str = "External service error", service_name: str = None):
        self.service_name = service_name
        super().__init__(message, status_code=502)


class BookingConflictError(ConflictError):
    """Exception raised when booking time slot conflicts with existing booking."""

    def __init__(self, message: str = "Booking time slot is already reserved"):
        super().__init__(message)


class AccountLockedError(AuthenticationError):
    """Exception raised when user account is locked."""

    def __init__(self, message: str = "Account is locked due to too many failed login attempts"):
        super().__init__(message)


class CircuitBreakerOpenError(ServiceUnavailableError):
    """Exception raised when circuit breaker is open."""

    def __init__(self, service_name: str):
        super().__init__(f"Circuit breaker is open for {service_name}")
        self.service_name = service_name
