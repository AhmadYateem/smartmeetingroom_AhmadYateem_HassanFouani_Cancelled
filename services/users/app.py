"""
Users Service - Authentication and User Management
Port: 5001

Handles:
- User registration and authentication
- User profile management
- User role management (RBAC)
- Password management
- User booking history

Team Member: Ahmad Yateem
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, get_jwt
from prometheus_flask_exporter import PrometheusMetrics

from configs.config import get_config
from database.models import db, User, Booking, init_db
from utils.auth import hash_password, verify_password, generate_tokens, get_current_user, admin_required
from utils.validators import (
    validate_required_fields,
    validate_email_format,
    validate_username,
    validate_password,
    validate_role,
    ValidationError
)
from utils.sanitizers import sanitize_username, sanitize_email, sanitize_string
from utils.responses import *
from utils.decorators import handle_errors, audit_log, rate_limit, validate_json
from utils.logger import setup_logger
from utils.http_client import ServiceClients
from utils.cache import cache, cached, invalidate_cache

# Initialize Flask app
app = Flask(__name__)
config = get_config()
app.config.from_object(config)

# Initialize extensions
CORS(app)
jwt = JWTManager(app)
db.init_app(app)
metrics = PrometheusMetrics(app)

# Setup logger
logger = setup_logger('users-service')


# Database initialization
with app.app_context():
    db.create_all()
    logger.info("Users Service database initialized")


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.

    Returns:
        200: Service is healthy
    """
    return success_response({'status': 'healthy', 'service': 'users'})


@app.route('/api/auth/register', methods=['POST'])
@handle_errors
@validate_json
@rate_limit(limit=10, window=3600)  # 10 registrations per hour
@audit_log('user_register', 'user')
def register():
    """
    Register a new user.

    Request Body:
        username: Unique username (3-50 chars, alphanumeric, underscore, hyphen)
        email: Valid email address
        password: Strong password (min 8 chars, upper, lower, digit, special char)
        full_name: User's full name
        role: Optional role (default: 'user')

    Returns:
        201: User created successfully with JWT tokens
        400: Validation error
        409: Username or email already exists

    Example:
        POST /api/auth/register
        {
            "username": "johndoe",
            "email": "john@example.com",
            "password": "SecurePass123!",
            "full_name": "John Doe",
            "role": "user"
        }
    """
    data = request.get_json()

    # Validate required fields
    validate_required_fields(data, ['username', 'email', 'password', 'full_name'])

    # Sanitize inputs
    username = sanitize_username(data['username'])
    email = sanitize_email(data['email'])
    full_name = sanitize_string(data['full_name'], max_length=100)
    role = data.get('role', 'user')

    # Validate inputs
    validate_username(username)
    email = validate_email_format(email)
    validate_password(data['password'])
    validate_role(role)

    # Check if username already exists
    if User.query.filter_by(username=username).first():
        return conflict_response(f"Username '{username}' is already taken")

    # Check if email already exists
    if User.query.filter_by(email=email).first():
        return conflict_response(f"Email '{email}' is already registered")

    # Hash password
    password_hash = hash_password(data['password'])

    # Create user
    user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        full_name=full_name,
        role=role,
        is_active=True
    )

    db.session.add(user)
    db.session.commit()

    # Generate tokens
    tokens = generate_tokens(user.id, user.username, user.role)

    logger.info(f"User registered: {username} (ID: {user.id})")

    return created_response({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role
        },
        'tokens': tokens
    }, message="User registered successfully")


@app.route('/api/auth/login', methods=['POST'])
@handle_errors
@validate_json
@rate_limit(limit=20, window=300)  # 20 login attempts per 5 minutes
def login():
    """
    User login.

    Request Body:
        username: Username or email
        password: User password

    Returns:
        200: Login successful with JWT tokens
        401: Invalid credentials or account locked
        404: User not found

    Example:
        POST /api/auth/login
        {
            "username": "johndoe",
            "password": "SecurePass123!"
        }
    """
    data = request.get_json()

    validate_required_fields(data, ['username', 'password'])

    username_or_email = sanitize_string(data['username'])

    # Find user by username or email
    user = User.query.filter(
        (User.username == username_or_email) | (User.email == username_or_email)
    ).first()

    if not user:
        return unauthorized_response("Invalid username or password")

    # Check if account is locked
    if user.is_locked():
        time_remaining = int((user.locked_until - datetime.utcnow()).total_seconds() / 60)
        return unauthorized_response(
            f"Account is locked due to too many failed login attempts. Try again in {time_remaining} minutes."
        )

    # Verify password
    if not verify_password(data['password'], user.password_hash):
        # Increment failed attempts
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= config.MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(seconds=config.ACCOUNT_LOCK_DURATION)
            logger.warning(f"Account locked: {user.username}")

        db.session.commit()
        return unauthorized_response("Invalid username or password")

    # Check if account is active
    if not user.is_active:
        return unauthorized_response("Account is disabled")

    # Reset failed attempts and update last login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.utcnow()
    db.session.commit()

    # Generate tokens
    tokens = generate_tokens(user.id, user.username, user.role)

    logger.info(f"User logged in: {user.username}")

    return success_response({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role
        },
        'tokens': tokens
    }, message="Login successful")


@app.route('/api/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
@handle_errors
def refresh_token():
    """
    Refresh access token using refresh token.

    Returns:
        200: New access token
        401: Invalid refresh token
    """
    current_user_id = get_jwt_identity()
    claims = get_jwt()

    user = User.query.get(current_user_id)
    if not user or not user.is_active:
        return unauthorized_response("User not found or inactive")

    # Generate new tokens
    tokens = generate_tokens(user.id, user.username, user.role)

    return success_response({'tokens': tokens}, message="Token refreshed successfully")


@app.route('/api/users', methods=['GET'])
@jwt_required()
@admin_required
@handle_errors
@rate_limit(limit=100, window=60)
def get_all_users():
    """
    Get all users (Admin only).

    Query Parameters:
        page: Page number (default: 1)
        per_page: Items per page (default: 20, max: 100)
        role: Filter by role
        is_active: Filter by active status (true/false)

    Returns:
        200: List of users with pagination

    Example:
        GET /api/users?page=1&per_page=20&role=user
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    role_filter = request.args.get('role')
    is_active = request.args.get('is_active')

    query = User.query

    # Apply filters
    if role_filter:
        query = query.filter_by(role=role_filter)

    if is_active is not None:
        is_active_bool = is_active.lower() == 'true'
        query = query.filter_by(is_active=is_active_bool)

    # Order by creation date
    query = query.order_by(User.created_at.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    users = [{
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'role': user.role,
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat(),
        'last_login': user.last_login.isoformat() if user.last_login else None
    } for user in pagination.items]

    return paginated_response(users, page, per_page, pagination.total)


@app.route('/api/users/<int:user_id>', methods=['GET'])
@jwt_required()
@handle_errors
def get_user(user_id):
    """
    Get user by ID.

    Returns:
        200: User details
        403: Forbidden (can only view own profile unless admin)
        404: User not found
    """
    current_user = get_current_user()

    # Users can only view their own profile unless admin
    if current_user['user_id'] != user_id and current_user['role'] != 'admin':
        return forbidden_response("You can only view your own profile")

    user = User.query.get(user_id)
    if not user:
        return not_found_response("User not found")

    return success_response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'role': user.role,
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat(),
        'last_login': user.last_login.isoformat() if user.last_login else None
    })


@app.route('/api/users/profile', methods=['GET'])
@jwt_required()
@handle_errors
def get_profile():
    """
    Get current user's profile.

    Returns:
        200: User profile
        404: User not found
    """
    current_user = get_current_user()
    user = User.query.get(current_user['user_id'])

    if not user:
        return not_found_response("User not found")

    return success_response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'role': user.role,
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat(),
        'last_login': user.last_login.isoformat() if user.last_login else None
    })


@app.route('/api/users/profile', methods=['PUT'])
@jwt_required()
@handle_errors
@validate_json
@audit_log('update_profile', 'user')
def update_profile():
    """
    Update current user's profile.

    Request Body:
        email: New email (optional)
        full_name: New full name (optional)
        password: New password (optional)

    Returns:
        200: Profile updated successfully
        400: Validation error
        409: Email already in use
    """
    current_user = get_current_user()
    user = User.query.get(current_user['user_id'])

    if not user:
        return not_found_response("User not found")

    data = request.get_json()

    # Update email
    if 'email' in data:
        new_email = sanitize_email(data['email'])
        new_email = validate_email_format(new_email)

        # Check if email is already used by another user
        existing_user = User.query.filter_by(email=new_email).first()
        if existing_user and existing_user.id != user.id:
            return conflict_response("Email is already in use")

        user.email = new_email

    # Update full name
    if 'full_name' in data:
        user.full_name = sanitize_string(data['full_name'], max_length=100)

    # Update password
    if 'password' in data:
        validate_password(data['password'])
        user.password_hash = hash_password(data['password'])

    db.session.commit()

    # Invalidate cache
    invalidate_cache(f'user:{user.id}')

    logger.info(f"Profile updated: {user.username}")

    return success_response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'role': user.role
    }, message="Profile updated successfully")


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
@admin_required
@handle_errors
@audit_log('delete_user', 'user')
def delete_user(user_id):
    """
    Delete a user (Admin only).

    Returns:
        200: User deleted successfully
        404: User not found
        403: Cannot delete yourself
    """
    current_user = get_current_user()

    if current_user['user_id'] == user_id:
        return forbidden_response("You cannot delete your own account")

    user = User.query.get(user_id)
    if not user:
        return not_found_response("User not found")

    username = user.username
    db.session.delete(user)
    db.session.commit()

    # Invalidate cache
    invalidate_cache(f'user:{user_id}')

    logger.info(f"User deleted: {username}")

    return success_response(message=f"User '{username}' deleted successfully")


@app.route('/api/users/<int:user_id>/bookings', methods=['GET'])
@jwt_required()
@handle_errors
@cached(key_prefix='user_bookings', ttl=300)
def get_user_bookings(user_id):
    """
    Get user's booking history.

    Query Parameters:
        page: Page number (default: 1)
        per_page: Items per page (default: 20)

    Returns:
        200: List of bookings
        403: Can only view own bookings unless admin
        404: User not found
    """
    current_user = get_current_user()

    # Users can only view their own bookings unless admin
    if current_user['user_id'] != user_id and current_user['role'] != 'admin':
        return forbidden_response("You can only view your own bookings")

    user = User.query.get(user_id)
    if not user:
        return not_found_response("User not found")

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    # Get bookings
    query = Booking.query.filter_by(user_id=user_id).order_by(Booking.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    bookings = [{
        'id': booking.id,
        'room_id': booking.room_id,
        'title': booking.title,
        'start_time': booking.start_time.isoformat(),
        'end_time': booking.end_time.isoformat(),
        'status': booking.status,
        'created_at': booking.created_at.isoformat()
    } for booking in pagination.items]

    return paginated_response(bookings, page, per_page, pagination.total)


if __name__ == '__main__':
    port = int(os.getenv('USER_SERVICE_PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=config.DEBUG)
