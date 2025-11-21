"""
Custom decorators for cross-cutting concerns.
"""

import time
from functools import wraps
from flask import request, g
from database.models import db, AuditLog
from utils.auth import get_current_user
from utils.logger import setup_logger
from utils.responses import rate_limit_response
from utils.exceptions import SMRException

logger = setup_logger(__name__)


def audit_log(action: str, resource_type: str = None):
    """
    Decorator to automatically log actions to audit log.

    Args:
        action: Action being performed
        resource_type: Type of resource being affected

    Returns:
        Decorated function
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            user_id = user['user_id'] if user else None

            # Get request details
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent')

            try:
                # Execute the function
                result = fn(*args, **kwargs)

                # Log successful action
                audit_entry = AuditLog(
                    user_id=user_id,
                    service=request.blueprint or 'unknown',
                    action=action,
                    resource_type=resource_type,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=True
                )
                db.session.add(audit_entry)
                db.session.commit()

                return result

            except Exception as e:
                # Log failed action
                audit_entry = AuditLog(
                    user_id=user_id,
                    service=request.blueprint or 'unknown',
                    action=action,
                    resource_type=resource_type,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    error_message=str(e)
                )
                db.session.add(audit_entry)
                db.session.commit()

                raise

        return wrapper
    return decorator


def measure_time(fn):
    """
    Decorator to measure and log function execution time.

    Returns:
        Decorated function
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = fn(*args, **kwargs)
            return result
        finally:
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            logger.info(
                f"{fn.__name__} execution time: {duration:.2f}ms",
                extra={'function': fn.__name__, 'duration_ms': duration}
            )

    return wrapper


def handle_errors(fn):
    """
    Decorator to handle exceptions and return appropriate responses.

    Returns:
        Decorated function
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except SMRException as e:
            logger.error(f"SMR Exception in {fn.__name__}: {str(e)}")
            from utils.responses import error_response
            return error_response(e.message, status_code=e.status_code)
        except Exception as e:
            logger.exception(f"Unexpected error in {fn.__name__}: {str(e)}")
            from utils.responses import server_error_response
            return server_error_response("An unexpected error occurred")

    return wrapper


def validate_json(fn):
    """
    Decorator to validate that request contains valid JSON.

    Returns:
        Decorated function
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not request.is_json:
            from utils.responses import error_response
            return error_response("Request must be JSON", status_code=400)

        return fn(*args, **kwargs)

    return wrapper


class SimpleRateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self):
        self.requests = {}

    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """
        Check if request is allowed based on rate limit.

        Args:
            key: Rate limit key (e.g., IP address or user ID)
            limit: Maximum number of requests
            window: Time window in seconds

        Returns:
            Boolean indicating if request is allowed
        """
        now = time.time()

        # Clean old entries
        if key in self.requests:
            self.requests[key] = [
                timestamp for timestamp in self.requests[key]
                if now - timestamp < window
            ]
        else:
            self.requests[key] = []

        # Check if limit exceeded
        if len(self.requests[key]) >= limit:
            return False

        # Add current request
        self.requests[key].append(now)
        return True


# Global rate limiter instance
rate_limiter = SimpleRateLimiter()


def rate_limit(limit: int = 60, window: int = 60, key_func=None):
    """
    Decorator to apply rate limiting to routes.

    Args:
        limit: Maximum number of requests
        window: Time window in seconds
        key_func: Optional function to generate rate limit key

    Returns:
        Decorated function
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Generate rate limit key
            if key_func:
                key = key_func()
            else:
                user = get_current_user()
                if user:
                    key = f"user:{user['user_id']}"
                else:
                    key = f"ip:{request.remote_addr}"

            # Check rate limit
            if not rate_limiter.is_allowed(key, limit, window):
                logger.warning(f"Rate limit exceeded for {key}")
                return rate_limit_response(
                    message=f"Rate limit exceeded. Maximum {limit} requests per {window} seconds.",
                    retry_after=window
                )

            return fn(*args, **kwargs)

        return wrapper
    return decorator


def cache_response(ttl: int = 300):
    """
    Decorator to cache response (requires Redis implementation).

    Args:
        ttl: Time to live in seconds

    Returns:
        Decorated function
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # This is a placeholder for Redis caching
            # Will be implemented with Redis integration
            return fn(*args, **kwargs)

        return wrapper
    return decorator


def require_service_account(fn):
    """
    Decorator to require service account authentication for inter-service calls.

    Returns:
        Decorated function
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_current_user()

        if not user or user['role'] != 'service':
            from utils.responses import forbidden_response
            return forbidden_response("Service account required")

        return fn(*args, **kwargs)

    return wrapper
