"""Utilities package initialization."""

from utils.auth import (
    hash_password,
    verify_password,
    generate_tokens,
    jwt_required_custom,
    get_current_user,
    role_required,
    admin_required,
    moderator_required,
    facility_manager_required
)
from utils.validators import ValidationError
from utils.sanitizers import (
    sanitize_html,
    sanitize_string,
    sanitize_username,
    sanitize_email,
    sanitize_comment,
    has_sql_injection_pattern,
    has_xss_pattern
)
from utils.logger import setup_logger, app_logger
from utils.exceptions import *
from utils.responses import *
from utils.decorators import *
from utils.circuit_breaker import CircuitBreaker, get_circuit_breaker, with_circuit_breaker
from utils.cache import cache, cached, invalidate_cache
from utils.http_client import ServiceClient, ServiceClients

__all__ = [
    'hash_password',
    'verify_password',
    'generate_tokens',
    'jwt_required_custom',
    'get_current_user',
    'role_required',
    'admin_required',
    'moderator_required',
    'facility_manager_required',
    'ValidationError',
    'sanitize_html',
    'sanitize_string',
    'sanitize_username',
    'sanitize_email',
    'sanitize_comment',
    'has_sql_injection_pattern',
    'has_xss_pattern',
    'setup_logger',
    'app_logger',
    'CircuitBreaker',
    'get_circuit_breaker',
    'with_circuit_breaker',
    'cache',
    'cached',
    'invalidate_cache',
    'ServiceClient',
    'ServiceClients'
]
