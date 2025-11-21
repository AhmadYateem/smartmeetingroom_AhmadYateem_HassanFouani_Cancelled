"""
Unit tests for validation utilities.
Team Member: Ahmad Yateem & Hassan Fouani
"""

import pytest
from datetime import datetime, timedelta
from utils.validators import (
    validate_email_format,
    validate_username,
    validate_password,
    validate_role,
    validate_room_capacity,
    validate_booking_times,
    validate_rating,
    ValidationError
)


class TestEmailValidation:
    """Test email validation."""

    def test_valid_email(self):
        """Test valid email formats."""
        assert validate_email_format('test@example.com') == 'test@example.com'
        assert validate_email_format('user.name@example.co.uk') == 'user.name@example.co.uk'

    def test_invalid_email(self):
        """Test invalid email formats."""
        with pytest.raises(ValidationError):
            validate_email_format('invalid-email')

        with pytest.raises(ValidationError):
            validate_email_format('test@')

        with pytest.raises(ValidationError):
            validate_email_format('@example.com')


class TestUsernameValidation:
    """Test username validation."""

    def test_valid_username(self):
        """Test valid usernames."""
        validate_username('johndoe')
        validate_username('user_123')
        validate_username('test-user')

    def test_invalid_username_too_short(self):
        """Test username too short."""
        with pytest.raises(ValidationError, match='at least 3 characters'):
            validate_username('ab')

    def test_invalid_username_too_long(self):
        """Test username too long."""
        with pytest.raises(ValidationError, match='must not exceed 50 characters'):
            validate_username('a' * 51)

    def test_invalid_username_characters(self):
        """Test username with invalid characters."""
        with pytest.raises(ValidationError, match='can only contain'):
            validate_username('user@name')


class TestPasswordValidation:
    """Test password validation."""

    def test_valid_password(self):
        """Test valid password."""
        validate_password('SecurePass123!')
        validate_password('Test@1234')

    def test_password_too_short(self):
        """Test password too short."""
        with pytest.raises(ValidationError, match='at least 8 characters'):
            validate_password('Test1!')

    def test_password_no_uppercase(self):
        """Test password without uppercase."""
        with pytest.raises(ValidationError, match='uppercase letter'):
            validate_password('testpass123!')

    def test_password_no_lowercase(self):
        """Test password without lowercase."""
        with pytest.raises(ValidationError, match='lowercase letter'):
            validate_password('TESTPASS123!')

    def test_password_no_digit(self):
        """Test password without digit."""
        with pytest.raises(ValidationError, match='digit'):
            validate_password('TestPass!')

    def test_password_no_special_char(self):
        """Test password without special character."""
        with pytest.raises(ValidationError, match='special character'):
            validate_password('TestPass123')


class TestRoleValidation:
    """Test role validation."""

    def test_valid_roles(self):
        """Test valid roles."""
        validate_role('admin')
        validate_role('user')
        validate_role('facility_manager')
        validate_role('moderator')

    def test_invalid_role(self):
        """Test invalid role."""
        with pytest.raises(ValidationError, match='Invalid role'):
            validate_role('super_admin')


class TestRoomCapacityValidation:
    """Test room capacity validation."""

    def test_valid_capacity(self):
        """Test valid capacities."""
        validate_room_capacity(1)
        validate_room_capacity(50)
        validate_room_capacity(1000)

    def test_invalid_capacity_zero(self):
        """Test capacity of zero."""
        with pytest.raises(ValidationError, match='positive integer'):
            validate_room_capacity(0)

    def test_invalid_capacity_negative(self):
        """Test negative capacity."""
        with pytest.raises(ValidationError, match='positive integer'):
            validate_room_capacity(-5)

    def test_invalid_capacity_too_large(self):
        """Test capacity exceeding maximum."""
        with pytest.raises(ValidationError, match='cannot exceed 1000'):
            validate_room_capacity(1001)


class TestBookingTimesValidation:
    """Test booking times validation."""

    def test_valid_booking_times(self):
        """Test valid booking times."""
        start = datetime.utcnow() + timedelta(hours=1)
        end = start + timedelta(hours=2)
        validate_booking_times(start, end)

    def test_end_before_start(self):
        """Test end time before start time."""
        start = datetime.utcnow() + timedelta(hours=2)
        end = datetime.utcnow() + timedelta(hours=1)

        with pytest.raises(ValidationError, match='End time must be after start time'):
            validate_booking_times(start, end)

    def test_booking_in_past(self):
        """Test booking in the past."""
        start = datetime.utcnow() - timedelta(hours=1)
        end = start + timedelta(hours=1)

        with pytest.raises(ValidationError, match='cannot be in the past'):
            validate_booking_times(start, end)

    def test_booking_too_short(self):
        """Test booking duration too short."""
        start = datetime.utcnow() + timedelta(hours=1)
        end = start + timedelta(minutes=15)

        with pytest.raises(ValidationError, match='at least 30 minutes'):
            validate_booking_times(start, end)


class TestRatingValidation:
    """Test rating validation."""

    def test_valid_ratings(self):
        """Test valid ratings."""
        for rating in range(1, 6):
            validate_rating(rating)

    def test_invalid_rating_too_low(self):
        """Test rating below 1."""
        with pytest.raises(ValidationError, match='between 1 and 5'):
            validate_rating(0)

    def test_invalid_rating_too_high(self):
        """Test rating above 5."""
        with pytest.raises(ValidationError, match='between 1 and 5'):
            validate_rating(6)

    def test_invalid_rating_type(self):
        """Test non-integer rating."""
        with pytest.raises(ValidationError, match='between 1 and 5'):
            validate_rating(3.5)
