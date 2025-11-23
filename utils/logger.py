"""
Logging utilities for structured application logging.
"""

import logging
import sys
from pathlib import Path
from pythonjsonlogger import jsonlogger
from configs.config import Config


def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """
    Setup and configure logger with JSON formatting.

    Args:
        name: Logger name (typically module or service name)
        log_file: Optional log file path

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Set log level from config
    log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # JSON formatter for structured logging
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if log file specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Create default logger
app_logger = setup_logger('smartmeetingroom', Config.LOG_FILE)


def log_request(logger: logging.Logger, method: str, endpoint: str, user_id: int = None):
    """
    Log incoming HTTP request.

    Args:
        logger: Logger instance
        method: HTTP method
        endpoint: Request endpoint
        user_id: Optional user ID
    """
    logger.info(
        'Incoming request',
        extra={
            'event_type': 'request',
            'method': method,
            'endpoint': endpoint,
            'user_id': user_id
        }
    )


def log_response(logger: logging.Logger, method: str, endpoint: str, status_code: int,
                 duration_ms: float, user_id: int = None):
    """
    Log HTTP response.

    Args:
        logger: Logger instance
        method: HTTP method
        endpoint: Request endpoint
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        user_id: Optional user ID
    """
    logger.info(
        'Response sent',
        extra={
            'event_type': 'response',
            'method': method,
            'endpoint': endpoint,
            'status_code': status_code,
            'duration_ms': duration_ms,
            'user_id': user_id
        }
    )


def log_error(logger: logging.Logger, error: Exception, context: dict = None):
    """
    Log error with context.

    Args:
        logger: Logger instance
        error: Exception object
        context: Optional context dictionary
    """
    log_data = {
        'event_type': 'error',
        'error_type': type(error).__name__,
        'error_message': str(error)
    }

    if context:
        log_data.update(context)

    logger.error('Error occurred', extra=log_data, exc_info=True)


def log_audit(logger: logging.Logger, user_id: int, action: str, resource_type: str,
              resource_id: int = None, details: dict = None):
    """
    Log audit event.

    Args:
        logger: Logger instance
        user_id: User ID performing action
        action: Action performed
        resource_type: Type of resource
        resource_id: Optional resource ID
        details: Optional additional details
    """
    log_data = {
        'event_type': 'audit',
        'user_id': user_id,
        'action': action,
        'resource_type': resource_type,
        'resource_id': resource_id
    }

    if details:
        log_data['details'] = details

    logger.info('Audit event', extra=log_data)
