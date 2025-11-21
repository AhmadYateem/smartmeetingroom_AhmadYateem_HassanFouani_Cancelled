"""
Integration tests for user registration and authentication workflow.
Team Member: Ahmad Yateem
"""

import pytest
import json


class TestUserAuthenticationWorkflow:
    """Test complete user authentication workflow."""

    def test_user_registration_and_login(self, client):
        """Test user can register and then login."""

        # Step 1: Register a new user
        register_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'full_name': 'New User'
        }

        response = client.post(
            '/api/auth/register',
            data=json.dumps(register_data),
            content_type='application/json'
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'access_token' in data['data']['tokens']

        # Step 2: Login with the new user
        login_data = {
            'username': 'newuser',
            'password': 'SecurePass123!'
        }

        response = client.post(
            '/api/auth/login',
            data=json.dumps(login_data),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'access_token' in data['data']['tokens']

    def test_registration_duplicate_username(self, client, sample_user):
        """Test registration with duplicate username."""

        register_data = {
            'username': sample_user.username,
            'email': 'different@example.com',
            'password': 'SecurePass123!',
            'full_name': 'Test User'
        }

        response = client.post(
            '/api/auth/register',
            data=json.dumps(register_data),
            content_type='application/json'
        )

        assert response.status_code == 409
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'already taken' in data['error']

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""

        login_data = {
            'username': 'nonexistent',
            'password': 'WrongPass123!'
        }

        response = client.post(
            '/api/auth/login',
            data=json.dumps(login_data),
            content_type='application/json'
        )

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False

    def test_get_profile_authenticated(self, client, sample_user, auth_headers):
        """Test getting user profile with authentication."""

        response = client.get(
            '/api/users/profile',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['username'] == sample_user.username

    def test_get_profile_unauthenticated(self, client):
        """Test getting profile without authentication."""

        response = client.get('/api/users/profile')

        assert response.status_code == 401


class TestBookingWorkflow:
    """Test complete booking workflow."""

    def test_create_and_cancel_booking(self, client, sample_user, sample_room, auth_headers):
        """Test creating and then cancelling a booking."""
        from datetime import datetime, timedelta

        # Step 1: Create booking
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat()
        end_time = (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat()

        booking_data = {
            'room_id': sample_room.id,
            'title': 'Test Meeting',
            'description': 'Integration test booking',
            'start_time': start_time,
            'end_time': end_time,
            'attendees': 5
        }

        response = client.post(
            '/api/bookings',
            data=json.dumps(booking_data),
            headers=auth_headers
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        booking_id = data['data']['id']

        # Step 2: Get booking details
        response = client.get(
            f'/api/bookings/{booking_id}',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['status'] == 'confirmed'

        # Step 3: Cancel booking
        response = client.delete(
            f'/api/bookings/{booking_id}',
            headers=auth_headers
        )

        assert response.status_code == 200

        # Step 4: Verify booking is cancelled
        response = client.get(
            f'/api/bookings/{booking_id}',
            headers=auth_headers
        )

        data = json.loads(response.data)
        assert data['data']['status'] == 'cancelled'
