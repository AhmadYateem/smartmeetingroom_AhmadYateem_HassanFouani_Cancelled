"""
Input validation utilities for request data validation.
"""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from email_validator import validate_email, EmailNotValidError


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def validate_required_fields(data: Dict, required_fields: List[str]) -> None:
    """
    Validate that all required fields are present in data.

    Args:
        data: Dictionary to validate
        required_fields: List of required field names

    Raises:
        ValidationError: If any required field is missing
    """
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]

    if missing_fields:
        raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")


def validate_email_format(email: str) -> str:
    """
    Validate email format.

    Args:
        email: Email address to validate

    Returns:
        Normalized email address

    Raises:
        ValidationError: If email format is invalid
    """
    try:
        valid = validate_email(email)
        return valid.email
    except EmailNotValidError as e:
        raise ValidationError(f"Invalid email format: {str(e)}")


def validate_username(username: str) -> None:
    """
    Validate username format.

    Args:
        username: Username to validate

    Raises:
        ValidationError: If username format is invalid
    """
    if not username or len(username) < 3:
        raise ValidationError("Username must be at least 3 characters long")

    if len(username) > 50:
        raise ValidationError("Username must not exceed 50 characters")

    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        raise ValidationError("Username can only contain letters, numbers, underscores, and hyphens")


def validate_password(password: str) -> None:
    """
    Validate password strength.

    Args:
        password: Password to validate

    Raises:
        ValidationError: If password doesn't meet requirements
    """
    if not password or len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long")

    if len(password) > 128:
        raise ValidationError("Password must not exceed 128 characters")

    if not re.search(r'[A-Z]', password):
        raise ValidationError("Password must contain at least one uppercase letter")

    if not re.search(r'[a-z]', password):
        raise ValidationError("Password must contain at least one lowercase letter")

    if not re.search(r'[0-9]', password):
        raise ValidationError("Password must contain at least one digit")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError("Password must contain at least one special character")


def validate_role(role: str) -> None:
    """
    Validate user role.

    Args:
        role: Role to validate

    Raises:
        ValidationError: If role is invalid
    """
    valid_roles = ['admin', 'user', 'facility_manager', 'moderator', 'auditor', 'service']

    if role not in valid_roles:
        raise ValidationError(f"Invalid role. Must be one of: {', '.join(valid_roles)}")


def validate_room_capacity(capacity: int) -> None:
    """
    Validate room capacity.

    Args:
        capacity: Capacity to validate

    Raises:
        ValidationError: If capacity is invalid
    """
    if not isinstance(capacity, int) or capacity <= 0:
        raise ValidationError("Room capacity must be a positive integer")

    if capacity > 1000:
        raise ValidationError("Room capacity cannot exceed 1000")


def validate_room_status(status: str) -> None:
    """
    Validate room status.

    Args:
        status: Status to validate

    Raises:
        ValidationError: If status is invalid
    """
    valid_statuses = ['available', 'booked', 'maintenance', 'out_of_service']

    if status not in valid_statuses:
        raise ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")


def validate_booking_times(start_time: datetime, end_time: datetime) -> None:
    """
    Validate booking start and end times.

    Args:
        start_time: Booking start time
        end_time: Booking end time

    Raises:
        ValidationError: If times are invalid
    """
    if not isinstance(start_time, datetime) or not isinstance(end_time, datetime):
        raise ValidationError("Start time and end time must be datetime objects")

    if start_time >= end_time:
        raise ValidationError("End time must be after start time")

    if start_time < datetime.utcnow():
        raise ValidationError("Booking start time cannot be in the past")

    duration = end_time - start_time

    if duration < timedelta(minutes=30):
        raise ValidationError("Booking duration must be at least 30 minutes")

    if duration > timedelta(days=7):
        raise ValidationError("Booking duration cannot exceed 7 days")


def validate_booking_status(status: str) -> None:
    """
    Validate booking status.

    Args:
        status: Status to validate

    Raises:
        ValidationError: If status is invalid
    """
    valid_statuses = ['pending', 'confirmed', 'cancelled', 'completed', 'no_show']

    if status not in valid_statuses:
        raise ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")


def validate_rating(rating: int) -> None:
    """
    Validate review rating.

    Args:
        rating: Rating to validate

    Raises:
        ValidationError: If rating is invalid
    """
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        raise ValidationError("Rating must be an integer between 1 and 5")


def validate_review_comment(comment: str) -> None:
    """
    Validate review comment.

    Args:
        comment: Comment to validate

    Raises:
        ValidationError: If comment is invalid
    """
    if comment and len(comment) > 2000:
        raise ValidationError("Comment must not exceed 2000 characters")


def validate_recurrence_pattern(pattern: str) -> None:
    """
    Validate booking recurrence pattern.

    Args:
        pattern: Pattern to validate

    Raises:
        ValidationError: If pattern is invalid
    """
    valid_patterns = ['daily', 'weekly', 'monthly']

    if pattern and pattern not in valid_patterns:
        raise ValidationError(f"Invalid recurrence pattern. Must be one of: {', '.join(valid_patterns)}")


def validate_date_format(date_string: str) -> datetime:
    """
    Validate and parse date string in ISO format.

    Args:
        date_string: Date string to validate

    Returns:
        Parsed datetime object

    Raises:
        ValidationError: If date format is invalid
    """
    try:
        return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        raise ValidationError("Invalid date format. Use ISO 8601 format (YYYY-MM-DDTHH:MM:SS)")


def validate_pagination_params(page: int, per_page: int) -> None:
    """
    Validate pagination parameters.

    Args:
        page: Page number
        per_page: Items per page

    Raises:
        ValidationError: If parameters are invalid
    """
    if not isinstance(page, int) or page < 1:
        raise ValidationError("Page must be a positive integer")

    if not isinstance(per_page, int) or per_page < 1:
        raise ValidationError("Items per page must be a positive integer")

    if per_page > 100:
        raise ValidationError("Items per page cannot exceed 100")
