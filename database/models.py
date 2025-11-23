"""
Database models for Smart Meeting Room Management System.
Defines all SQLAlchemy models for Users, Rooms, Bookings, Reviews, and Audit Logs.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, INET

db = SQLAlchemy()


class BaseModel(db.Model):
    """Base model class with common fields and methods."""

    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Convert model instance to dictionary."""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            elif isinstance(value, (list, dict)):
                result[column.name] = value
            else:
                result[column.name] = value
        return result

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.id}>"


class User(BaseModel):
    """
    User model for authentication and user management.

    Attributes:
        username: Unique username for login
        email: Unique email address
        password_hash: Hashed password
        full_name: User's full name
        role: User role (admin, user, facility_manager, moderator, auditor, service)
        is_active: Whether the account is active
        last_login: Timestamp of last successful login
        failed_login_attempts: Number of consecutive failed login attempts
        locked_until: Timestamp until which the account is locked
    """

    __tablename__ = 'users'

    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(
        db.String(20),
        nullable=False,
        default='user',
        server_default=text("'user'")
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime)

    # Relationships
    bookings = db.relationship('Booking', back_populates='user', lazy='dynamic', foreign_keys='Booking.user_id')
    reviews = db.relationship('Review', back_populates='user', lazy='dynamic', foreign_keys='Review.user_id')
    flagged_reviews = db.relationship('Review', back_populates='flagger', lazy='dynamic',
                                      foreign_keys='Review.flagged_by')
    cancelled_bookings = db.relationship('Booking', back_populates='canceller', lazy='dynamic',
                                         foreign_keys='Booking.cancelled_by')

    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'user', 'facility_manager', 'moderator', 'auditor', 'service')",
            name='check_user_role'
        ),
        Index('idx_users_username', 'username'),
        Index('idx_users_email', 'email'),
        Index('idx_users_role', 'role'),
    )

    def is_locked(self):
        """Check if user account is currently locked."""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until

    def has_role(self, *roles):
        """Check if user has any of the specified roles."""
        return self.role in roles


class Room(BaseModel):
    """
    Room model for meeting room management.

    Attributes:
        name: Unique room name
        capacity: Maximum number of people
        floor: Floor number
        building: Building name
        location: Detailed location description
        equipment: List of available equipment
        amenities: List of amenities
        status: Current room status (available, booked, maintenance, out_of_service)
        hourly_rate: Cost per hour for booking
        image_url: URL to room image
    """

    __tablename__ = 'rooms'

    name = db.Column(db.String(100), unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    floor = db.Column(db.Integer)
    building = db.Column(db.String(50))
    location = db.Column(db.String(200))
    equipment = db.Column(ARRAY(db.String), default=list)
    amenities = db.Column(ARRAY(db.String), default=list)
    status = db.Column(
        db.String(20),
        default='available',
        nullable=False
    )
    hourly_rate = db.Column(db.Numeric(10, 2))
    image_url = db.Column(db.String(500))

    # Relationships
    bookings = db.relationship('Booking', back_populates='room', lazy='dynamic')
    reviews = db.relationship('Review', back_populates='room', lazy='dynamic')

    __table_args__ = (
        CheckConstraint('capacity > 0', name='check_room_capacity'),
        CheckConstraint(
            "status IN ('available', 'booked', 'maintenance', 'out_of_service')",
            name='check_room_status'
        ),
        Index('idx_rooms_capacity', 'capacity'),
        Index('idx_rooms_status', 'status'),
        Index('idx_rooms_location', 'location'),
        Index('idx_rooms_building', 'building'),
    )

    def is_available(self):
        """Check if room is available for booking."""
        return self.status == 'available'


class Booking(BaseModel):
    """
    Booking model for meeting room reservations.

    Attributes:
        user_id: ID of user who made the booking
        room_id: ID of booked room
        title: Booking title/subject
        description: Detailed description
        start_time: Booking start time
        end_time: Booking end time
        status: Booking status (pending, confirmed, cancelled, completed, no_show)
        attendees: Number of expected attendees
        is_recurring: Whether this is a recurring booking
        recurrence_pattern: Pattern for recurring bookings (daily, weekly, monthly)
        recurrence_end_date: End date for recurring bookings
        cancellation_reason: Reason for cancellation
        cancelled_at: Timestamp of cancellation
        cancelled_by: ID of user who cancelled
    """

    __tablename__ = 'bookings'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False, index=True)
    status = db.Column(
        db.String(20),
        default='confirmed',
        nullable=False
    )
    attendees = db.Column(db.Integer)
    is_recurring = db.Column(db.Boolean, default=False, nullable=False)
    recurrence_pattern = db.Column(db.String(20))
    recurrence_end_date = db.Column(db.Date)
    cancellation_reason = db.Column(db.Text)
    cancelled_at = db.Column(db.DateTime)
    cancelled_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships
    user = db.relationship('User', back_populates='bookings', foreign_keys=[user_id])
    room = db.relationship('Room', back_populates='bookings')
    reviews = db.relationship('Review', back_populates='booking', lazy='dynamic')
    canceller = db.relationship('User', back_populates='cancelled_bookings', foreign_keys=[cancelled_by])

    __table_args__ = (
        CheckConstraint('end_time > start_time', name='check_booking_times'),
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'cancelled', 'completed', 'no_show')",
            name='check_booking_status'
        ),
        CheckConstraint(
            "recurrence_pattern IS NULL OR recurrence_pattern IN ('daily', 'weekly', 'monthly')",
            name='check_recurrence_pattern'
        ),
        Index('idx_bookings_user_id', 'user_id'),
        Index('idx_bookings_room_id', 'room_id'),
        Index('idx_bookings_start_time', 'start_time'),
        Index('idx_bookings_end_time', 'end_time'),
        Index('idx_bookings_status', 'status'),
        Index('idx_bookings_date_range', 'start_time', 'end_time'),
    )

    def has_conflict(self, room_id, start_time, end_time, exclude_booking_id=None):
        """
        Check if booking conflicts with existing bookings.

        Args:
            room_id: Room ID to check
            start_time: Start time of new booking
            end_time: End time of new booking
            exclude_booking_id: Booking ID to exclude from check (for updates)

        Returns:
            Boolean indicating if conflict exists
        """
        query = Booking.query.filter(
            Booking.room_id == room_id,
            Booking.status.in_(['pending', 'confirmed']),
            db.or_(
                db.and_(Booking.start_time <= start_time, Booking.end_time > start_time),
                db.and_(Booking.start_time < end_time, Booking.end_time >= end_time),
                db.and_(Booking.start_time >= start_time, Booking.end_time <= end_time)
            )
        )

        if exclude_booking_id:
            query = query.filter(Booking.id != exclude_booking_id)

        return query.first() is not None


class Review(BaseModel):
    """
    Review model for room feedback and ratings.

    Attributes:
        user_id: ID of user who submitted review
        room_id: ID of reviewed room
        booking_id: ID of booking being reviewed
        rating: Rating from 1-5
        title: Review title
        comment: Review comment/description
        pros: Positive aspects
        cons: Negative aspects
        is_flagged: Whether review has been flagged
        flag_reason: Reason for flagging
        flagged_by: ID of user who flagged
        flagged_at: Timestamp of flagging
        is_hidden: Whether review is hidden by moderators
        hidden_reason: Reason for hiding
        helpful_count: Number of helpful votes
        unhelpful_count: Number of unhelpful votes
        edited_at: Timestamp of last edit
    """

    __tablename__ = 'reviews'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='CASCADE'))
    rating = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200))
    comment = db.Column(db.Text)
    pros = db.Column(db.Text)
    cons = db.Column(db.Text)
    is_flagged = db.Column(db.Boolean, default=False, nullable=False)
    flag_reason = db.Column(db.String(200))
    flagged_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    flagged_at = db.Column(db.DateTime)
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)
    hidden_reason = db.Column(db.String(200))
    helpful_count = db.Column(db.Integer, default=0, nullable=False)
    unhelpful_count = db.Column(db.Integer, default=0, nullable=False)
    edited_at = db.Column(db.DateTime)

    # Relationships
    user = db.relationship('User', back_populates='reviews', foreign_keys=[user_id])
    room = db.relationship('Room', back_populates='reviews')
    booking = db.relationship('Booking', back_populates='reviews')
    flagger = db.relationship('User', back_populates='flagged_reviews', foreign_keys=[flagged_by])

    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='check_review_rating'),
        db.UniqueConstraint('user_id', 'booking_id', name='unique_user_booking_review'),
        Index('idx_reviews_room_id', 'room_id'),
        Index('idx_reviews_user_id', 'user_id'),
        Index('idx_reviews_rating', 'rating'),
        Index('idx_reviews_flagged', 'is_flagged'),
        Index('idx_reviews_hidden', 'is_hidden'),
    )


class AuditLog(BaseModel):
    """
    Audit log model for tracking system changes and actions.

    Attributes:
        user_id: ID of user who performed action
        service: Service name where action occurred
        action: Action performed
        resource_type: Type of resource affected
        resource_id: ID of affected resource
        old_values: Previous values (JSON)
        new_values: New values (JSON)
        ip_address: IP address of requester
        user_agent: User agent string
        success: Whether action was successful
        error_message: Error message if action failed
    """

    __tablename__ = 'audit_logs'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    service = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.Integer)
    old_values = db.Column(JSONB)
    new_values = db.Column(JSONB)
    ip_address = db.Column(INET)
    user_agent = db.Column(db.Text)
    success = db.Column(db.Boolean, default=True, nullable=False)
    error_message = db.Column(db.Text)

    # Relationships
    user = db.relationship('User', backref='audit_logs')

    __table_args__ = (
        Index('idx_audit_logs_user_id', 'user_id'),
        Index('idx_audit_logs_service', 'service'),
        Index('idx_audit_logs_action', 'action'),
        Index('idx_audit_logs_created_at', 'created_at'),
        Index('idx_audit_logs_resource', 'resource_type', 'resource_id'),
    )


def init_db(app):
    """
    Initialize database with Flask app.

    Args:
        app: Flask application instance
    """
    db.init_app(app)

    with app.app_context():
        db.create_all()


def reset_db(app):
    """
    Reset database (drop all tables and recreate).

    Args:
        app: Flask application instance
    """
    with app.app_context():
        db.drop_all()
        db.create_all()
