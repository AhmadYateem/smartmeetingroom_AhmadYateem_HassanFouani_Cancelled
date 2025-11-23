"""
Authentication utilities for JWT token management and password hashing.
"""

import bcrypt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    verify_jwt_in_request,
    get_jwt
)
from configs.config import Config


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    salt = bcrypt.gensalt(rounds=Config.BCRYPT_LOG_ROUNDS)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        password: Plain text password
        password_hash: Hashed password

    Returns:
        Boolean indicating if password matches
    """
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def generate_tokens(user_id: int, username: str, role: str):
    """
    Generate access and refresh tokens for a user.

    Args:
        user_id: User ID
        username: Username
        role: User role

    Returns:
        Dictionary with access_token and refresh_token
    """
    additional_claims = {
        'user_id': user_id,
        'username': username,
        'role': role
    }

    access_token = create_access_token(
        identity=user_id,
        additional_claims=additional_claims,
        expires_delta=timedelta(seconds=Config.JWT_ACCESS_TOKEN_EXPIRES)
    )

    refresh_token = create_refresh_token(
        identity=user_id,
        additional_claims=additional_claims,
        expires_delta=timedelta(seconds=Config.JWT_REFRESH_TOKEN_EXPIRES)
    )

    return {
        'access_token': access_token,
        'refresh_token': refresh_token
    }


def jwt_required_custom(fn):
    """
    Decorator to require JWT authentication for route.

    Returns:
        Decorated function
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return fn(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': 'Authentication required', 'message': str(e)}), 401

    return wrapper


def get_current_user():
    """
    Get current user information from JWT token.

    Returns:
        Dictionary with user_id, username, and role
    """
    try:
        verify_jwt_in_request()
        claims = get_jwt()
        return {
            'user_id': claims.get('user_id'),
            'username': claims.get('username'),
            'role': claims.get('role')
        }
    except:
        return None


def role_required(*roles):
    """
    Decorator to require specific role(s) for route access.

    Args:
        roles: One or more role names

    Returns:
        Decorated function
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
                claims = get_jwt()
                user_role = claims.get('role')

                if user_role not in roles:
                    return jsonify({
                        'error': 'Forbidden',
                        'message': f'Required role: {", ".join(roles)}'
                    }), 403

                return fn(*args, **kwargs)
            except Exception as e:
                return jsonify({'error': 'Authentication failed', 'message': str(e)}), 401

        return wrapper
    return decorator


def admin_required(fn):
    """
    Decorator to require admin role for route access.

    Returns:
        Decorated function
    """
    return role_required('admin')(fn)


def moderator_required(fn):
    """
    Decorator to require moderator or admin role for route access.

    Returns:
        Decorated function
    """
    return role_required('admin', 'moderator')(fn)


def facility_manager_required(fn):
    """
    Decorator to require facility_manager or admin role for route access.

    Returns:
        Decorated function
    """
    return role_required('admin', 'facility_manager')(fn)
