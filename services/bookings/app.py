"""
Bookings Service - Meeting Room Booking Management
Port: 5003

Handles:
- Creating and managing bookings
- Checking room availability
- Conflict detection and resolution
- Booking history and status management
- Recurring bookings

Team Member: Ahmad Yateem
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required
from prometheus_flask_exporter import PrometheusMetrics
from sqlalchemy import or_, and_

from configs.config import get_config
from database.models import db, Booking, Room, User, init_db
from utils.auth import get_current_user, admin_required
from utils.validators import (
    validate_required_fields,
    validate_booking_times,
    validate_booking_status,
    validate_recurrence_pattern,
    validate_date_format,
    ValidationError
)
from utils.sanitizers import sanitize_string
from utils.responses import *
from utils.decorators import handle_errors, audit_log, rate_limit, validate_json
from utils.logger import setup_logger
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
logger = setup_logger('bookings-service')

# Database initialization
with app.app_context():
    db.create_all()
    logger.info("Bookings Service database initialized")


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.

    Returns:
        200: Service is healthy
    """
    return success_response({'status': 'healthy', 'service': 'bookings'})


@app.route('/api/bookings', methods=['GET'])
@jwt_required()
@handle_errors
@rate_limit(limit=100, window=60)
def get_all_bookings():
    """
    Get all bookings (filtered by user role).

    Query Parameters:
        page: Page number (default: 1)
        per_page: Items per page (default: 20, max: 100)
        room_id: Filter by room
        status: Filter by status
        start_date: Filter bookings starting from this date
        end_date: Filter bookings ending before this date

    Returns:
        200: List of bookings with pagination

    Note:
        - Regular users see only their own bookings
        - Admins see all bookings
    """
    current_user = get_current_user()

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    query = Booking.query

    # Regular users can only see their own bookings
    if current_user['role'] not in ['admin', 'facility_manager', 'auditor']:
        query = query.filter_by(user_id=current_user['user_id'])

    # Apply filters
    room_id = request.args.get('room_id', type=int)
    if room_id:
        query = query.filter_by(room_id=room_id)

    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)

    start_date = request.args.get('start_date')
    if start_date:
        try:
            start_dt = validate_date_format(start_date)
            query = query.filter(Booking.start_time >= start_dt)
        except ValidationError:
            return error_response("Invalid start_date format")

    end_date = request.args.get('end_date')
    if end_date:
        try:
            end_dt = validate_date_format(end_date)
            query = query.filter(Booking.end_time <= end_dt)
        except ValidationError:
            return error_response("Invalid end_date format")

    # Order by start time
    query = query.order_by(Booking.start_time.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    bookings = [{
        'id': booking.id,
        'user_id': booking.user_id,
        'room_id': booking.room_id,
        'title': booking.title,
        'description': booking.description,
        'start_time': booking.start_time.isoformat(),
        'end_time': booking.end_time.isoformat(),
        'status': booking.status,
        'attendees': booking.attendees,
        'is_recurring': booking.is_recurring,
        'created_at': booking.created_at.isoformat()
    } for booking in pagination.items]

    return paginated_response(bookings, page, per_page, pagination.total)


@app.route('/api/bookings/<int:booking_id>', methods=['GET'])
@jwt_required()
@handle_errors
def get_booking(booking_id):
    """
    Get booking details by ID.

    Returns:
        200: Booking details
        403: Forbidden (can only view own bookings unless admin)
        404: Booking not found
    """
    current_user = get_current_user()

    booking = Booking.query.get(booking_id)
    if not booking:
        return not_found_response("Booking not found")

    # Users can only view their own bookings unless admin
    if (booking.user_id != current_user['user_id'] and
            current_user['role'] not in ['admin', 'facility_manager', 'auditor']):
        return forbidden_response("You can only view your own bookings")

    return success_response({
        'id': booking.id,
        'user_id': booking.user_id,
        'room_id': booking.room_id,
        'title': booking.title,
        'description': booking.description,
        'start_time': booking.start_time.isoformat(),
        'end_time': booking.end_time.isoformat(),
        'status': booking.status,
        'attendees': booking.attendees,
        'is_recurring': booking.is_recurring,
        'recurrence_pattern': booking.recurrence_pattern,
        'recurrence_end_date': booking.recurrence_end_date.isoformat() if booking.recurrence_end_date else None,
        'cancellation_reason': booking.cancellation_reason,
        'cancelled_at': booking.cancelled_at.isoformat() if booking.cancelled_at else None,
        'created_at': booking.created_at.isoformat(),
        'updated_at': booking.updated_at.isoformat()
    })


@app.route('/api/bookings', methods=['POST'])
@jwt_required()
@handle_errors
@validate_json
@audit_log('create_booking', 'booking')
@rate_limit(limit=50, window=3600)
def create_booking():
    """
    Create a new booking.

    Request Body:
        room_id: Room ID (required)
        title: Booking title (required)
        description: Booking description (optional)
        start_time: Start time in ISO 8601 format (required)
        end_time: End time in ISO 8601 format (required)
        attendees: Number of attendees (optional)
        is_recurring: Whether booking is recurring (optional, default: false)
        recurrence_pattern: Pattern for recurring bookings (daily/weekly/monthly)
        recurrence_end_date: End date for recurring bookings

    Returns:
        201: Booking created successfully
        400: Validation error
        404: Room not found
        409: Time slot conflict

    Example:
        POST /api/bookings
        {
            "room_id": 1,
            "title": "Team Meeting",
            "description": "Weekly team sync",
            "start_time": "2025-11-25T10:00:00Z",
            "end_time": "2025-11-25T11:00:00Z",
            "attendees": 5
        }
    """
    current_user = get_current_user()
    data = request.get_json()

    # Validate required fields
    validate_required_fields(data, ['room_id', 'title', 'start_time', 'end_time'])

    room_id = data['room_id']
    title = sanitize_string(data['title'], max_length=200)
    description = sanitize_string(data.get('description', ''), max_length=2000)

    # Parse and validate times
    try:
        start_time = validate_date_format(data['start_time'])
        end_time = validate_date_format(data['end_time'])
        validate_booking_times(start_time, end_time)
    except ValidationError as e:
        return error_response(str(e))

    # Check if room exists and is available
    room = Room.query.get(room_id)
    if not room:
        return not_found_response("Room not found")

    if room.status != 'available':
        return conflict_response(f"Room is currently {room.status}")

    # Validate attendees doesn't exceed room capacity
    attendees = data.get('attendees')
    if attendees and attendees > room.capacity:
        return error_response(f"Number of attendees ({attendees}) exceeds room capacity ({room.capacity})")

    # Check for conflicts
    conflict = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.status.in_(['pending', 'confirmed']),
        or_(
            and_(Booking.start_time <= start_time, Booking.end_time > start_time),
            and_(Booking.start_time < end_time, Booking.end_time >= end_time),
            and_(Booking.start_time >= start_time, Booking.end_time <= end_time)
        )
    ).first()

    if conflict:
        return conflict_response(
            f"Time slot conflicts with existing booking (ID: {conflict.id}). "
            f"Conflicting booking: {conflict.start_time.isoformat()} - {conflict.end_time.isoformat()}"
        )

    # Handle recurring bookings
    is_recurring = data.get('is_recurring', False)
    recurrence_pattern = None
    recurrence_end_date = None

    if is_recurring:
        recurrence_pattern = data.get('recurrence_pattern', 'weekly')
        validate_recurrence_pattern(recurrence_pattern)

        if 'recurrence_end_date' in data:
            try:
                recurrence_end_date = validate_date_format(data['recurrence_end_date']).date()
            except ValidationError:
                return error_response("Invalid recurrence_end_date format")

    # Create booking
    booking = Booking(
        user_id=current_user['user_id'],
        room_id=room_id,
        title=title,
        description=description,
        start_time=start_time,
        end_time=end_time,
        status='confirmed',
        attendees=attendees,
        is_recurring=is_recurring,
        recurrence_pattern=recurrence_pattern,
        recurrence_end_date=recurrence_end_date
    )

    db.session.add(booking)
    db.session.commit()

    # Invalidate relevant caches
    invalidate_cache(f'user_bookings:{current_user["user_id"]}')
    invalidate_cache(f'room_bookings:{room_id}')

    logger.info(f"Booking created: {title} (ID: {booking.id}) by user {current_user['username']}")

    return created_response({
        'id': booking.id,
        'room_id': booking.room_id,
        'title': booking.title,
        'start_time': booking.start_time.isoformat(),
        'end_time': booking.end_time.isoformat(),
        'status': booking.status
    }, message="Booking created successfully")


@app.route('/api/bookings/<int:booking_id>', methods=['PUT'])
@jwt_required()
@handle_errors
@validate_json
@audit_log('update_booking', 'booking')
def update_booking(booking_id):
    """
    Update a booking.

    Request Body:
        title: Booking title (optional)
        description: Booking description (optional)
        start_time: Start time (optional)
        end_time: End time (optional)
        attendees: Number of attendees (optional)
        status: Booking status (optional)

    Returns:
        200: Booking updated successfully
        400: Validation error
        403: Forbidden (can only update own bookings)
        404: Booking not found
        409: Time slot conflict
    """
    current_user = get_current_user()

    booking = Booking.query.get(booking_id)
    if not booking:
        return not_found_response("Booking not found")

    # Users can only update their own bookings unless admin
    if (booking.user_id != current_user['user_id'] and
            current_user['role'] not in ['admin', 'facility_manager']):
        return forbidden_response("You can only update your own bookings")

    # Cannot update cancelled bookings
    if booking.status == 'cancelled':
        return conflict_response("Cannot update cancelled booking")

    data = request.get_json()

    # Update title
    if 'title' in data:
        booking.title = sanitize_string(data['title'], max_length=200)

    # Update description
    if 'description' in data:
        booking.description = sanitize_string(data['description'], max_length=2000)

    # Update times
    if 'start_time' in data or 'end_time' in data:
        start_time = booking.start_time
        end_time = booking.end_time

        if 'start_time' in data:
            start_time = validate_date_format(data['start_time'])

        if 'end_time' in data:
            end_time = validate_date_format(data['end_time'])

        validate_booking_times(start_time, end_time)

        # Check for conflicts (excluding current booking)
        conflict = Booking.query.filter(
            Booking.room_id == booking.room_id,
            Booking.id != booking_id,
            Booking.status.in_(['pending', 'confirmed']),
            or_(
                and_(Booking.start_time <= start_time, Booking.end_time > start_time),
                and_(Booking.start_time < end_time, Booking.end_time >= end_time),
                and_(Booking.start_time >= start_time, Booking.end_time <= end_time)
            )
        ).first()

        if conflict:
            return conflict_response(f"Time slot conflicts with existing booking (ID: {conflict.id})")

        booking.start_time = start_time
        booking.end_time = end_time

    # Update attendees
    if 'attendees' in data:
        attendees = data['attendees']
        room = Room.query.get(booking.room_id)
        if attendees > room.capacity:
            return error_response(f"Number of attendees ({attendees}) exceeds room capacity ({room.capacity})")
        booking.attendees = attendees

    # Update status
    if 'status' in data:
        validate_booking_status(data['status'])
        booking.status = data['status']

    db.session.commit()

    # Invalidate caches
    invalidate_cache(f'user_bookings:{booking.user_id}')
    invalidate_cache(f'room_bookings:{booking.room_id}')

    logger.info(f"Booking updated: {booking.title} (ID: {booking_id})")

    return success_response({
        'id': booking.id,
        'title': booking.title,
        'start_time': booking.start_time.isoformat(),
        'end_time': booking.end_time.isoformat(),
        'status': booking.status
    }, message="Booking updated successfully")


@app.route('/api/bookings/<int:booking_id>', methods=['DELETE'])
@jwt_required()
@handle_errors
@audit_log('cancel_booking', 'booking')
def cancel_booking(booking_id):
    """
    Cancel a booking.

    Request Body (optional):
        cancellation_reason: Reason for cancellation

    Returns:
        200: Booking cancelled successfully
        403: Forbidden (can only cancel own bookings)
        404: Booking not found
        409: Booking already cancelled
    """
    current_user = get_current_user()

    booking = Booking.query.get(booking_id)
    if not booking:
        return not_found_response("Booking not found")

    # Users can only cancel their own bookings unless admin
    if (booking.user_id != current_user['user_id'] and
            current_user['role'] not in ['admin', 'facility_manager']):
        return forbidden_response("You can only cancel your own bookings")

    if booking.status == 'cancelled':
        return conflict_response("Booking is already cancelled")

    # Get cancellation reason if provided
    data = request.get_json() if request.is_json else {}
    cancellation_reason = sanitize_string(data.get('cancellation_reason', ''), max_length=500)

    # Update booking
    booking.status = 'cancelled'
    booking.cancellation_reason = cancellation_reason
    booking.cancelled_at = datetime.utcnow()
    booking.cancelled_by = current_user['user_id']

    db.session.commit()

    # Invalidate caches
    invalidate_cache(f'user_bookings:{booking.user_id}')
    invalidate_cache(f'room_bookings:{booking.room_id}')

    logger.info(f"Booking cancelled: {booking.title} (ID: {booking_id}) by {current_user['username']}")

    return success_response(message="Booking cancelled successfully")


@app.route('/api/bookings/check-availability', methods=['POST'])
@handle_errors
@validate_json
@rate_limit(limit=100, window=60)
def check_availability():
    """
    Check room availability for a time slot.

    Request Body:
        room_id: Room ID (optional, checks all rooms if not provided)
        start_time: Start time in ISO 8601 format (required)
        end_time: End time in ISO 8601 format (required)

    Returns:
        200: Availability information

    Example:
        POST /api/bookings/check-availability
        {
            "room_id": 1,
            "start_time": "2025-11-25T10:00:00Z",
            "end_time": "2025-11-25T11:00:00Z"
        }
    """
    data = request.get_json()

    validate_required_fields(data, ['start_time', 'end_time'])

    try:
        start_time = validate_date_format(data['start_time'])
        end_time = validate_date_format(data['end_time'])
        validate_booking_times(start_time, end_time)
    except ValidationError as e:
        return error_response(str(e))

    room_id = data.get('room_id')

    if room_id:
        # Check specific room
        room = Room.query.get(room_id)
        if not room:
            return not_found_response("Room not found")

        conflict = Booking.query.filter(
            Booking.room_id == room_id,
            Booking.status.in_(['pending', 'confirmed']),
            or_(
                and_(Booking.start_time <= start_time, Booking.end_time > start_time),
                and_(Booking.start_time < end_time, Booking.end_time >= end_time),
                and_(Booking.start_time >= start_time, Booking.end_time <= end_time)
            )
        ).first()

        is_available = conflict is None and room.status == 'available'

        return success_response({
            'room_id': room_id,
            'is_available': is_available,
            'conflict': {
                'booking_id': conflict.id,
                'start_time': conflict.start_time.isoformat(),
                'end_time': conflict.end_time.isoformat()
            } if conflict else None
        })
    else:
        # Check all available rooms
        available_rooms = Room.query.filter_by(status='available').all()

        # Get conflicting bookings
        conflicting_bookings = Booking.query.filter(
            Booking.status.in_(['pending', 'confirmed']),
            or_(
                and_(Booking.start_time <= start_time, Booking.end_time > start_time),
                and_(Booking.start_time < end_time, Booking.end_time >= end_time),
                and_(Booking.start_time >= start_time, Booking.end_time <= end_time)
            )
        ).all()

        booked_room_ids = {booking.room_id for booking in conflicting_bookings}

        results = [{
            'room_id': room.id,
            'room_name': room.name,
            'is_available': room.id not in booked_room_ids,
            'capacity': room.capacity,
            'location': room.location
        } for room in available_rooms]

        available_count = sum(1 for r in results if r['is_available'])

        return success_response({
            'available_rooms_count': available_count,
            'total_rooms': len(results),
            'rooms': results
        })


@app.route('/api/bookings/conflicts', methods=['GET'])
@jwt_required()
@admin_required
@handle_errors
def get_conflicts():
    """
    Get all booking conflicts (Admin only).

    Returns:
        200: List of conflicting bookings
    """
    # Find overlapping bookings
    bookings = Booking.query.filter(
        Booking.status.in_(['pending', 'confirmed'])
    ).order_by(Booking.start_time).all()

    conflicts = []
    for i, booking1 in enumerate(bookings):
        for booking2 in bookings[i+1:]:
            if booking1.room_id == booking2.room_id:
                # Check if they overlap
                if (booking1.start_time < booking2.end_time and
                        booking1.end_time > booking2.start_time):
                    conflicts.append({
                        'booking1': {
                            'id': booking1.id,
                            'title': booking1.title,
                            'start_time': booking1.start_time.isoformat(),
                            'end_time': booking1.end_time.isoformat()
                        },
                        'booking2': {
                            'id': booking2.id,
                            'title': booking2.title,
                            'start_time': booking2.start_time.isoformat(),
                            'end_time': booking2.end_time.isoformat()
                        },
                        'room_id': booking1.room_id
                    })

    return success_response({
        'conflicts_count': len(conflicts),
        'conflicts': conflicts
    })


if __name__ == '__main__':
    port = int(os.getenv('BOOKING_SERVICE_PORT', 5003))
    app.run(host='0.0.0.0', port=port, debug=config.DEBUG)
