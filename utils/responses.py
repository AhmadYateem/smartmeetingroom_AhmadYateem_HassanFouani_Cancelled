"""
Standardized API response utilities.
"""

from flask import jsonify
from typing import Any, Dict, List, Optional


def success_response(data: Any = None, message: str = None, status_code: int = 200):
    """
    Create successful API response.

    Args:
        data: Response data
        message: Optional success message
        status_code: HTTP status code

    Returns:
        Flask JSON response
    """
    response = {
        'success': True,
        'data': data
    }

    if message:
        response['message'] = message

    return jsonify(response), status_code


def error_response(message: str, errors: List[str] = None, status_code: int = 400):
    """
    Create error API response.

    Args:
        message: Error message
        errors: Optional list of specific errors
        status_code: HTTP status code

    Returns:
        Flask JSON response
    """
    response = {
        'success': False,
        'error': message
    }

    if errors:
        response['errors'] = errors

    return jsonify(response), status_code


def created_response(data: Any, message: str = "Resource created successfully", location: str = None):
    """
    Create 201 Created response.

    Args:
        data: Created resource data
        message: Success message
        location: Optional resource location URL

    Returns:
        Flask JSON response
    """
    response = jsonify({
        'success': True,
        'message': message,
        'data': data
    })

    if location:
        response.headers['Location'] = location

    return response, 201


def no_content_response():
    """
    Create 204 No Content response.

    Returns:
        Flask response
    """
    return '', 204


def paginated_response(items: List[Any], page: int, per_page: int, total: int,
                       message: str = None):
    """
    Create paginated response.

    Args:
        items: List of items for current page
        page: Current page number
        per_page: Items per page
        total: Total number of items
        message: Optional message

    Returns:
        Flask JSON response
    """
    total_pages = (total + per_page - 1) // per_page

    response = {
        'success': True,
        'data': items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_items': total,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    }

    if message:
        response['message'] = message

    return jsonify(response), 200


def validation_error_response(errors: Dict[str, List[str]]):
    """
    Create validation error response with field-specific errors.

    Args:
        errors: Dictionary of field names to error messages

    Returns:
        Flask JSON response
    """
    return jsonify({
        'success': False,
        'error': 'Validation failed',
        'validation_errors': errors
    }), 400


def unauthorized_response(message: str = "Authentication required"):
    """
    Create 401 Unauthorized response.

    Args:
        message: Error message

    Returns:
        Flask JSON response
    """
    return jsonify({
        'success': False,
        'error': message
    }), 401


def forbidden_response(message: str = "Access forbidden"):
    """
    Create 403 Forbidden response.

    Args:
        message: Error message

    Returns:
        Flask JSON response
    """
    return jsonify({
        'success': False,
        'error': message
    }), 403


def not_found_response(message: str = "Resource not found"):
    """
    Create 404 Not Found response.

    Args:
        message: Error message

    Returns:
        Flask JSON response
    """
    return jsonify({
        'success': False,
        'error': message
    }), 404


def conflict_response(message: str = "Resource conflict"):
    """
    Create 409 Conflict response.

    Args:
        message: Error message

    Returns:
        Flask JSON response
    """
    return jsonify({
        'success': False,
        'error': message
    }), 409


def rate_limit_response(message: str = "Rate limit exceeded", retry_after: int = None):
    """
    Create 429 Too Many Requests response.

    Args:
        message: Error message
        retry_after: Optional seconds until rate limit resets

    Returns:
        Flask JSON response
    """
    response = jsonify({
        'success': False,
        'error': message
    })

    if retry_after:
        response.headers['Retry-After'] = str(retry_after)

    return response, 429


def server_error_response(message: str = "Internal server error"):
    """
    Create 500 Internal Server Error response.

    Args:
        message: Error message

    Returns:
        Flask JSON response
    """
    return jsonify({
        'success': False,
        'error': message
    }), 500


def service_unavailable_response(message: str = "Service temporarily unavailable"):
    """
    Create 503 Service Unavailable response.

    Args:
        message: Error message

    Returns:
        Flask JSON response
    """
    return jsonify({
        'success': False,
        'error': message
    }), 503
