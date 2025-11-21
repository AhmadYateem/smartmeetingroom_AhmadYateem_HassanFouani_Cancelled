"""
Rooms Service - Meeting Room Management
Port: 5002

Handles:
- Adding and managing meeting rooms
- Room availability checking
- Room details and equipment management
- Room search and filtering

Team Member: Hassan Fouani
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required
from prometheus_flask_exporter import PrometheusMetrics
from sqlalchemy import or_, and_

from configs.config import get_config
from database.models import db, Room, Booking, init_db
from utils.auth import get_current_user, admin_required, facility_manager_required
from utils.validators import (
    validate_required_fields,
    validate_room_capacity,
    validate_room_status,
    ValidationError
)
from utils.sanitizers import sanitize_string, sanitize_url
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
logger = setup_logger('rooms-service')

# Database initialization
with app.app_context():
    db.create_all()
    logger.info("Rooms Service database initialized")


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.

    Returns:
        200: Service is healthy
    """
    return success_response({'status': 'healthy', 'service': 'rooms'})


@app.route('/api/rooms', methods=['GET'])
@handle_errors
@rate_limit(limit=100, window=60)
@cached(key_prefix='rooms_list', ttl=300)
def get_all_rooms():
    """
    Get all meeting rooms with optional filtering.

    Query Parameters:
        page: Page number (default: 1)
        per_page: Items per page (default: 20, max: 100)
        capacity_min: Minimum capacity
        capacity_max: Maximum capacity
        location: Filter by location
        building: Filter by building
        floor: Filter by floor
        status: Filter by status
        equipment: Comma-separated list of required equipment

    Returns:
        200: List of rooms with pagination

    Example:
        GET /api/rooms?capacity_min=10&location=Main%20Building
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    query = Room.query

    # Apply filters
    capacity_min = request.args.get('capacity_min', type=int)
    if capacity_min:
        query = query.filter(Room.capacity >= capacity_min)

    capacity_max = request.args.get('capacity_max', type=int)
    if capacity_max:
        query = query.filter(Room.capacity <= capacity_max)

    location = request.args.get('location')
    if location:
        query = query.filter(Room.location.ilike(f'%{location}%'))

    building = request.args.get('building')
    if building:
        query = query.filter(Room.building.ilike(f'%{building}%'))

    floor = request.args.get('floor', type=int)
    if floor is not None:
        query = query.filter(Room.floor == floor)

    status = request.args.get('status')
    if status:
        query = query.filter(Room.status == status)

    equipment = request.args.get('equipment')
    if equipment:
        equipment_list = [e.strip() for e in equipment.split(',')]
        for eq in equipment_list:
            query = query.filter(Room.equipment.contains([eq]))

    # Order by name
    query = query.order_by(Room.name)

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    rooms = [{
        'id': room.id,
        'name': room.name,
        'capacity': room.capacity,
        'floor': room.floor,
        'building': room.building,
        'location': room.location,
        'equipment': room.equipment,
        'amenities': room.amenities,
        'status': room.status,
        'hourly_rate': float(room.hourly_rate) if room.hourly_rate else None,
        'image_url': room.image_url,
        'created_at': room.created_at.isoformat()
    } for room in pagination.items]

    return paginated_response(rooms, page, per_page, pagination.total)


@app.route('/api/rooms/<int:room_id>', methods=['GET'])
@handle_errors
@rate_limit(limit=100, window=60)
@cached(key_prefix='room_detail', ttl=300)
def get_room(room_id):
    """
    Get room details by ID.

    Returns:
        200: Room details
        404: Room not found
    """
    room = Room.query.get(room_id)
    if not room:
        return not_found_response("Room not found")

    return success_response({
        'id': room.id,
        'name': room.name,
        'capacity': room.capacity,
        'floor': room.floor,
        'building': room.building,
        'location': room.location,
        'equipment': room.equipment,
        'amenities': room.amenities,
        'status': room.status,
        'hourly_rate': float(room.hourly_rate) if room.hourly_rate else None,
        'image_url': room.image_url,
        'created_at': room.created_at.isoformat(),
        'updated_at': room.updated_at.isoformat()
    })


@app.route('/api/rooms', methods=['POST'])
@jwt_required()
@facility_manager_required
@handle_errors
@validate_json
@audit_log('create_room', 'room')
@rate_limit(limit=50, window=3600)
def create_room():
    """
    Create a new meeting room (Facility Manager or Admin only).

    Request Body:
        name: Room name (required, unique)
        capacity: Maximum capacity (required, > 0)
        floor: Floor number (optional)
        building: Building name (optional)
        location: Location description (optional)
        equipment: List of equipment (optional)
        amenities: List of amenities (optional)
        hourly_rate: Hourly rate (optional)
        image_url: Image URL (optional)

    Returns:
        201: Room created successfully
        400: Validation error
        409: Room name already exists

    Example:
        POST /api/rooms
        {
            "name": "Conference Room A",
            "capacity": 20,
            "floor": 3,
            "building": "Main Building",
            "location": "East Wing, 3rd Floor",
            "equipment": ["projector", "whiteboard", "video_conference"],
            "amenities": ["wifi", "coffee_machine", "air_conditioning"]
        }
    """
    data = request.get_json()

    # Validate required fields
    validate_required_fields(data, ['name', 'capacity'])

    # Sanitize and validate
    name = sanitize_string(data['name'], max_length=100)
    capacity = data['capacity']

    validate_room_capacity(capacity)

    # Check if room name already exists
    if Room.query.filter_by(name=name).first():
        return conflict_response(f"Room '{name}' already exists")

    # Create room
    room = Room(
        name=name,
        capacity=capacity,
        floor=data.get('floor'),
        building=sanitize_string(data.get('building', ''), max_length=50),
        location=sanitize_string(data.get('location', ''), max_length=200),
        equipment=data.get('equipment', []),
        amenities=data.get('amenities', []),
        status='available',
        hourly_rate=data.get('hourly_rate'),
        image_url=sanitize_url(data.get('image_url', ''))
    )

    db.session.add(room)
    db.session.commit()

    # Invalidate cache
    invalidate_cache('rooms_list')

    logger.info(f"Room created: {name} (ID: {room.id})")

    return created_response({
        'id': room.id,
        'name': room.name,
        'capacity': room.capacity,
        'location': room.location,
        'status': room.status
    }, message="Room created successfully")


@app.route('/api/rooms/<int:room_id>', methods=['PUT'])
@jwt_required()
@facility_manager_required
@handle_errors
@validate_json
@audit_log('update_room', 'room')
def update_room(room_id):
    """
    Update room details (Facility Manager or Admin only).

    Request Body:
        name: Room name (optional)
        capacity: Maximum capacity (optional)
        floor: Floor number (optional)
        building: Building name (optional)
        location: Location description (optional)
        equipment: List of equipment (optional)
        amenities: List of amenities (optional)
        status: Room status (optional)
        hourly_rate: Hourly rate (optional)
        image_url: Image URL (optional)

    Returns:
        200: Room updated successfully
        400: Validation error
        404: Room not found
        409: Room name already exists
    """
    room = Room.query.get(room_id)
    if not room:
        return not_found_response("Room not found")

    data = request.get_json()

    # Update name
    if 'name' in data:
        new_name = sanitize_string(data['name'], max_length=100)
        existing_room = Room.query.filter_by(name=new_name).first()
        if existing_room and existing_room.id != room_id:
            return conflict_response(f"Room '{new_name}' already exists")
        room.name = new_name

    # Update capacity
    if 'capacity' in data:
        validate_room_capacity(data['capacity'])
        room.capacity = data['capacity']

    # Update other fields
    if 'floor' in data:
        room.floor = data['floor']

    if 'building' in data:
        room.building = sanitize_string(data['building'], max_length=50)

    if 'location' in data:
        room.location = sanitize_string(data['location'], max_length=200)

    if 'equipment' in data:
        room.equipment = data['equipment']

    if 'amenities' in data:
        room.amenities = data['amenities']

    if 'status' in data:
        validate_room_status(data['status'])
        room.status = data['status']

    if 'hourly_rate' in data:
        room.hourly_rate = data['hourly_rate']

    if 'image_url' in data:
        room.image_url = sanitize_url(data['image_url'])

    db.session.commit()

    # Invalidate cache
    invalidate_cache('rooms_list')
    invalidate_cache(f'room_detail:{room_id}')

    logger.info(f"Room updated: {room.name} (ID: {room_id})")

    return success_response({
        'id': room.id,
        'name': room.name,
        'capacity': room.capacity,
        'location': room.location,
        'status': room.status
    }, message="Room updated successfully")


@app.route('/api/rooms/<int:room_id>', methods=['DELETE'])
@jwt_required()
@admin_required
@handle_errors
@audit_log('delete_room', 'room')
def delete_room(room_id):
    """
    Delete a room (Admin only).

    Returns:
        200: Room deleted successfully
        404: Room not found
        409: Cannot delete room with active bookings
    """
    room = Room.query.get(room_id)
    if not room:
        return not_found_response("Room not found")

    # Check for active bookings
    active_bookings = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.status.in_(['pending', 'confirmed'])
    ).count()

    if active_bookings > 0:
        return conflict_response(
            f"Cannot delete room with {active_bookings} active booking(s). "
            "Please cancel or complete all bookings first."
        )

    room_name = room.name
    db.session.delete(room)
    db.session.commit()

    # Invalidate cache
    invalidate_cache('rooms_list')
    invalidate_cache(f'room_detail:{room_id}')

    logger.info(f"Room deleted: {room_name} (ID: {room_id})")

    return success_response(message=f"Room '{room_name}' deleted successfully")


@app.route('/api/rooms/available', methods=['GET'])
@handle_errors
@rate_limit(limit=100, window=60)
def get_available_rooms():
    """
    Get available rooms with optional filtering.

    Query Parameters:
        start_time: Start time (ISO 8601 format)
        end_time: End time (ISO 8601 format)
        capacity_min: Minimum capacity
        location: Filter by location
        equipment: Comma-separated list of required equipment

    Returns:
        200: List of available rooms

    Example:
        GET /api/rooms/available?capacity_min=10&equipment=projector,whiteboard
    """
    from datetime import datetime

    query = Room.query.filter_by(status='available')

    # Apply capacity filter
    capacity_min = request.args.get('capacity_min', type=int)
    if capacity_min:
        query = query.filter(Room.capacity >= capacity_min)

    # Apply location filter
    location = request.args.get('location')
    if location:
        query = query.filter(Room.location.ilike(f'%{location}%'))

    # Apply equipment filter
    equipment = request.args.get('equipment')
    if equipment:
        equipment_list = [e.strip() for e in equipment.split(',')]
        for eq in equipment_list:
            query = query.filter(Room.equipment.contains([eq]))

    # Check time availability if provided
    start_time_str = request.args.get('start_time')
    end_time_str = request.args.get('end_time')

    if start_time_str and end_time_str:
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))

            # Get rooms with conflicting bookings
            conflicting_bookings = Booking.query.filter(
                Booking.status.in_(['pending', 'confirmed']),
                or_(
                    and_(Booking.start_time <= start_time, Booking.end_time > start_time),
                    and_(Booking.start_time < end_time, Booking.end_time >= end_time),
                    and_(Booking.start_time >= start_time, Booking.end_time <= end_time)
                )
            ).all()

            booked_room_ids = {booking.room_id for booking in conflicting_bookings}

            if booked_room_ids:
                query = query.filter(Room.id.notin_(booked_room_ids))

        except ValueError:
            return error_response("Invalid date format. Use ISO 8601 format.")

    rooms = query.order_by(Room.name).all()

    result = [{
        'id': room.id,
        'name': room.name,
        'capacity': room.capacity,
        'floor': room.floor,
        'building': room.building,
        'location': room.location,
        'equipment': room.equipment,
        'amenities': room.amenities,
        'hourly_rate': float(room.hourly_rate) if room.hourly_rate else None,
        'image_url': room.image_url
    } for room in rooms]

    return success_response(result, message=f"Found {len(result)} available rooms")


@app.route('/api/rooms/search', methods=['POST'])
@handle_errors
@validate_json
@rate_limit(limit=100, window=60)
def search_rooms():
    """
    Advanced room search.

    Request Body:
        query: Search query (searches name, location, building)
        capacity_min: Minimum capacity
        capacity_max: Maximum capacity
        equipment: List of required equipment
        amenities: List of required amenities
        floor: Floor number
        building: Building name

    Returns:
        200: List of matching rooms

    Example:
        POST /api/rooms/search
        {
            "query": "conference",
            "capacity_min": 10,
            "equipment": ["projector"],
            "building": "Main Building"
        }
    """
    data = request.get_json()

    query = Room.query

    # Text search
    search_query = data.get('query', '').strip()
    if search_query:
        search_pattern = f'%{search_query}%'
        query = query.filter(
            or_(
                Room.name.ilike(search_pattern),
                Room.location.ilike(search_pattern),
                Room.building.ilike(search_pattern)
            )
        )

    # Capacity range
    if 'capacity_min' in data:
        query = query.filter(Room.capacity >= data['capacity_min'])

    if 'capacity_max' in data:
        query = query.filter(Room.capacity <= data['capacity_max'])

    # Equipment requirements
    if 'equipment' in data and data['equipment']:
        for eq in data['equipment']:
            query = query.filter(Room.equipment.contains([eq]))

    # Amenities requirements
    if 'amenities' in data and data['amenities']:
        for amenity in data['amenities']:
            query = query.filter(Room.amenities.contains([amenity]))

    # Floor
    if 'floor' in data:
        query = query.filter(Room.floor == data['floor'])

    # Building
    if 'building' in data:
        query = query.filter(Room.building.ilike(f"%{data['building']}%"))

    rooms = query.order_by(Room.name).all()

    result = [{
        'id': room.id,
        'name': room.name,
        'capacity': room.capacity,
        'floor': room.floor,
        'building': room.building,
        'location': room.location,
        'equipment': room.equipment,
        'amenities': room.amenities,
        'status': room.status,
        'hourly_rate': float(room.hourly_rate) if room.hourly_rate else None,
        'image_url': room.image_url
    } for room in rooms]

    return success_response(result, message=f"Found {len(result)} matching rooms")


if __name__ == '__main__':
    port = int(os.getenv('ROOM_SERVICE_PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=config.DEBUG)
