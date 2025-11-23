"""
Pytest configuration and fixtures for testing.
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask
from database.models import db, User, Room, Booking, Review
from configs.config import TestingConfig
from utils.auth import hash_password, generate_tokens


@pytest.fixture(scope='session')
def app():
    """Create Flask app for testing."""
    app = Flask(__name__)
    app.config.from_object(TestingConfig)

    # Initialize database
    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Create database session for testing."""
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.rollback()
        db.session.remove()


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    user = User(
        username='testuser',
        email='test@example.com',
        password_hash=hash_password('TestPass123!'),
        full_name='Test User',
        role='user',
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session):
    """Create an admin user for testing."""
    user = User(
        username='admin',
        email='admin@example.com',
        password_hash=hash_password('AdminPass123!'),
        full_name='Admin User',
        role='admin',
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(sample_user):
    """Generate JWT token for authenticated requests."""
    tokens = generate_tokens(sample_user.id, sample_user.username, sample_user.role)
    return {
        'Authorization': f'Bearer {tokens["access_token"]}',
        'Content-Type': 'application/json'
    }


@pytest.fixture
def admin_auth_headers(admin_user):
    """Generate JWT token for admin requests."""
    tokens = generate_tokens(admin_user.id, admin_user.username, admin_user.role)
    return {
        'Authorization': f'Bearer {tokens["access_token"]}',
        'Content-Type': 'application/json'
    }


@pytest.fixture
def sample_room(db_session):
    """Create a sample room for testing."""
    room = Room(
        name='Conference Room A',
        capacity=10,
        floor=1,
        building='Main Building',
        location='East Wing',
        equipment=['projector', 'whiteboard'],
        amenities=['wifi', 'coffee_machine'],
        status='available'
    )
    db_session.add(room)
    db_session.commit()
    db_session.refresh(room)
    return room


@pytest.fixture
def sample_booking(db_session, sample_user, sample_room):
    """Create a sample booking for testing."""
    from datetime import datetime, timedelta

    booking = Booking(
        user_id=sample_user.id,
        room_id=sample_room.id,
        title='Team Meeting',
        description='Weekly sync',
        start_time=datetime.utcnow() + timedelta(days=1),
        end_time=datetime.utcnow() + timedelta(days=1, hours=1),
        status='confirmed',
        attendees=5
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)
    return booking


@pytest.fixture
def sample_review(db_session, sample_user, sample_room, sample_booking):
    """Create a sample review for testing."""
    review = Review(
        user_id=sample_user.id,
        room_id=sample_room.id,
        booking_id=sample_booking.id,
        rating=5,
        title='Great room!',
        comment='Perfect for our team meetings',
        pros='Good equipment, comfortable seating',
        cons='None'
    )
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)
    return review
