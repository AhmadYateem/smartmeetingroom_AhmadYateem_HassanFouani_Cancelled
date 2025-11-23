"""
Reviews Service - Room Review and Rating Management
Port: 5004

Handles:
- Submitting and managing room reviews
- Review moderation and flagging
- Rating aggregation
- Review visibility management

Team Member: Hassan Fouani
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required
from prometheus_flask_exporter import PrometheusMetrics
from sqlalchemy import func

from configs.config import get_config
from database.models import db, Review, Room, Booking, User, init_db
from utils.auth import get_current_user, admin_required, moderator_required
from utils.validators import (
    validate_required_fields,
    validate_rating,
    validate_review_comment,
    ValidationError
)
from utils.sanitizers import sanitize_comment, sanitize_string, has_xss_pattern
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
logger = setup_logger('reviews-service')

# Database initialization
with app.app_context():
    db.create_all()
    logger.info("Reviews Service database initialized")


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.

    Returns:
        200: Service is healthy
    """
    return success_response({'status': 'healthy', 'service': 'reviews'})


@app.route('/api/reviews', methods=['POST'])
@jwt_required()
@handle_errors
@validate_json
@audit_log('submit_review', 'review')
@rate_limit(limit=10, window=3600)  # 10 reviews per hour
def submit_review():
    """
    Submit a review for a room.

    Request Body:
        room_id: Room ID (required)
        booking_id: Booking ID (optional, recommended)
        rating: Rating 1-5 (required)
        title: Review title (optional)
        comment: Review comment (optional)
        pros: Positive aspects (optional)
        cons: Negative aspects (optional)

    Returns:
        201: Review created successfully
        400: Validation error or XSS detected
        404: Room or booking not found
        409: Review already exists for this booking

    Example:
        POST /api/reviews
        {
            "room_id": 1,
            "booking_id": 5,
            "rating": 5,
            "title": "Great meeting room!",
            "comment": "Perfect for team meetings with excellent equipment.",
            "pros": "Good lighting, comfortable chairs, reliable AV equipment",
            "cons": "Could use better climate control"
        }
    """
    current_user = get_current_user()
    data = request.get_json()

    # Validate required fields
    validate_required_fields(data, ['room_id', 'rating'])

    room_id = data['room_id']
    booking_id = data.get('booking_id')
    rating = data['rating']

    # Validate rating
    validate_rating(rating)

    # Check if room exists
    room = Room.query.get(room_id)
    if not room:
        return not_found_response("Room not found")

    # If booking_id provided, validate it
    if booking_id:
        booking = Booking.query.get(booking_id)
        if not booking:
            return not_found_response("Booking not found")

        # Verify booking belongs to user and is for this room
        if booking.user_id != current_user['user_id']:
            return forbidden_response("You can only review your own bookings")

        if booking.room_id != room_id:
            return error_response("Booking is not for this room")

        # Check if review already exists for this booking
        existing_review = Review.query.filter_by(
            user_id=current_user['user_id'],
            booking_id=booking_id
        ).first()

        if existing_review:
            return conflict_response("You have already reviewed this booking")

    # Sanitize and validate text inputs
    title = sanitize_comment(data.get('title', ''))
    comment = sanitize_comment(data.get('comment', ''))
    pros = sanitize_comment(data.get('pros', ''))
    cons = sanitize_comment(data.get('cons', ''))

    validate_review_comment(comment)

    # Check for XSS patterns
    if any(has_xss_pattern(text) for text in [title, comment, pros, cons]):
        logger.warning(f"XSS pattern detected in review from user {current_user['user_id']}")
        return error_response("Invalid content detected. Please remove any HTML or script tags.")

    # Create review
    review = Review(
        user_id=current_user['user_id'],
        room_id=room_id,
        booking_id=booking_id,
        rating=rating,
        title=title,
        comment=comment,
        pros=pros,
        cons=cons
    )

    db.session.add(review)
    db.session.commit()

    # Invalidate caches
    invalidate_cache(f'room_reviews:{room_id}')
    invalidate_cache(f'user_reviews:{current_user["user_id"]}')

    logger.info(f"Review submitted for room {room_id} by user {current_user['username']}")

    return created_response({
        'id': review.id,
        'room_id': review.room_id,
        'rating': review.rating,
        'title': review.title
    }, message="Review submitted successfully")


@app.route('/api/reviews/<int:review_id>', methods=['GET'])
@handle_errors
def get_review(review_id):
    """
    Get review details by ID.

    Returns:
        200: Review details
        404: Review not found
    """
    review = Review.query.get(review_id)
    if not review:
        return not_found_response("Review not found")

    # Don't show hidden reviews to non-moderators
    current_user = get_current_user()
    if review.is_hidden and (not current_user or current_user['role'] not in ['admin', 'moderator']):
        return not_found_response("Review not found")

    # Get user info
    user = User.query.get(review.user_id)

    return success_response({
        'id': review.id,
        'room_id': review.room_id,
        'user': {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name
        },
        'rating': review.rating,
        'title': review.title,
        'comment': review.comment,
        'pros': review.pros,
        'cons': review.cons,
        'helpful_count': review.helpful_count,
        'unhelpful_count': review.unhelpful_count,
        'is_flagged': review.is_flagged,
        'is_hidden': review.is_hidden,
        'created_at': review.created_at.isoformat(),
        'edited_at': review.edited_at.isoformat() if review.edited_at else None
    })


@app.route('/api/reviews/<int:review_id>', methods=['PUT'])
@jwt_required()
@handle_errors
@validate_json
@audit_log('update_review', 'review')
def update_review(review_id):
    """
    Update a review (owner only).

    Request Body:
        rating: New rating (optional)
        title: New title (optional)
        comment: New comment (optional)
        pros: New pros (optional)
        cons: New cons (optional)

    Returns:
        200: Review updated successfully
        403: Forbidden (can only update own reviews)
        404: Review not found
    """
    current_user = get_current_user()

    review = Review.query.get(review_id)
    if not review:
        return not_found_response("Review not found")

    # Users can only update their own reviews
    if review.user_id != current_user['user_id']:
        return forbidden_response("You can only update your own reviews")

    data = request.get_json()

    # Update rating
    if 'rating' in data:
        validate_rating(data['rating'])
        review.rating = data['rating']

    # Update text fields
    if 'title' in data:
        title = sanitize_comment(data['title'])
        if has_xss_pattern(title):
            return error_response("Invalid content detected in title")
        review.title = title

    if 'comment' in data:
        comment = sanitize_comment(data['comment'])
        validate_review_comment(comment)
        if has_xss_pattern(comment):
            return error_response("Invalid content detected in comment")
        review.comment = comment

    if 'pros' in data:
        pros = sanitize_comment(data['pros'])
        if has_xss_pattern(pros):
            return error_response("Invalid content detected in pros")
        review.pros = pros

    if 'cons' in data:
        cons = sanitize_comment(data['cons'])
        if has_xss_pattern(cons):
            return error_response("Invalid content detected in cons")
        review.cons = cons

    review.edited_at = datetime.utcnow()
    db.session.commit()

    # Invalidate caches
    invalidate_cache(f'room_reviews:{review.room_id}')

    logger.info(f"Review {review_id} updated by user {current_user['username']}")

    return success_response({
        'id': review.id,
        'rating': review.rating,
        'title': review.title
    }, message="Review updated successfully")


@app.route('/api/reviews/<int:review_id>', methods=['DELETE'])
@jwt_required()
@handle_errors
@audit_log('delete_review', 'review')
def delete_review(review_id):
    """
    Delete a review.

    Returns:
        200: Review deleted successfully
        403: Forbidden (can only delete own reviews unless admin)
        404: Review not found
    """
    current_user = get_current_user()

    review = Review.query.get(review_id)
    if not review:
        return not_found_response("Review not found")

    # Users can only delete their own reviews unless admin/moderator
    if (review.user_id != current_user['user_id'] and
            current_user['role'] not in ['admin', 'moderator']):
        return forbidden_response("You can only delete your own reviews")

    room_id = review.room_id
    db.session.delete(review)
    db.session.commit()

    # Invalidate caches
    invalidate_cache(f'room_reviews:{room_id}')
    invalidate_cache(f'user_reviews:{review.user_id}')

    logger.info(f"Review {review_id} deleted by user {current_user['username']}")

    return success_response(message="Review deleted successfully")


@app.route('/api/reviews/room/<int:room_id>', methods=['GET'])
@handle_errors
@rate_limit(limit=100, window=60)
@cached(key_prefix='room_reviews', ttl=300)
def get_room_reviews(room_id):
    """
    Get all reviews for a specific room.

    Query Parameters:
        page: Page number (default: 1)
        per_page: Items per page (default: 20, max: 100)
        min_rating: Filter by minimum rating
        max_rating: Filter by maximum rating
        sort: Sort by (newest, oldest, rating_high, rating_low, helpful)

    Returns:
        200: List of reviews with room rating statistics
        404: Room not found
    """
    # Check if room exists
    room = Room.query.get(room_id)
    if not room:
        return not_found_response("Room not found")

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    query = Review.query.filter_by(room_id=room_id, is_hidden=False)

    # Apply filters
    min_rating = request.args.get('min_rating', type=int)
    if min_rating:
        query = query.filter(Review.rating >= min_rating)

    max_rating = request.args.get('max_rating', type=int)
    if max_rating:
        query = query.filter(Review.rating <= max_rating)

    # Apply sorting
    sort = request.args.get('sort', 'newest')
    if sort == 'oldest':
        query = query.order_by(Review.created_at.asc())
    elif sort == 'rating_high':
        query = query.order_by(Review.rating.desc())
    elif sort == 'rating_low':
        query = query.order_by(Review.rating.asc())
    elif sort == 'helpful':
        query = query.order_by(Review.helpful_count.desc())
    else:  # newest (default)
        query = query.order_by(Review.created_at.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    reviews = []
    for review in pagination.items:
        user = User.query.get(review.user_id)
        reviews.append({
            'id': review.id,
            'user': {
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name
            },
            'rating': review.rating,
            'title': review.title,
            'comment': review.comment,
            'pros': review.pros,
            'cons': review.cons,
            'helpful_count': review.helpful_count,
            'unhelpful_count': review.unhelpful_count,
            'created_at': review.created_at.isoformat()
        })

    # Calculate statistics
    all_reviews = Review.query.filter_by(room_id=room_id, is_hidden=False).all()
    total_reviews = len(all_reviews)

    if total_reviews > 0:
        avg_rating = sum(r.rating for r in all_reviews) / total_reviews
        rating_distribution = {i: sum(1 for r in all_reviews if r.rating == i) for i in range(1, 6)}
    else:
        avg_rating = 0
        rating_distribution = {i: 0 for i in range(1, 6)}

    return success_response({
        'reviews': reviews,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_items': pagination.total,
            'total_pages': (pagination.total + per_page - 1) // per_page
        },
        'statistics': {
            'total_reviews': total_reviews,
            'average_rating': round(avg_rating, 2),
            'rating_distribution': rating_distribution
        }
    })


@app.route('/api/reviews/<int:review_id>/flag', methods=['POST'])
@jwt_required()
@handle_errors
@validate_json
@audit_log('flag_review', 'review')
@rate_limit(limit=20, window=3600)
def flag_review(review_id):
    """
    Flag a review as inappropriate.

    Request Body:
        reason: Reason for flagging (required)

    Returns:
        200: Review flagged successfully
        404: Review not found
        409: Already flagged by this user
    """
    current_user = get_current_user()

    review = Review.query.get(review_id)
    if not review:
        return not_found_response("Review not found")

    data = request.get_json()
    validate_required_fields(data, ['reason'])

    reason = sanitize_string(data['reason'], max_length=200)

    # Update review
    review.is_flagged = True
    review.flag_reason = reason
    review.flagged_by = current_user['user_id']
    review.flagged_at = datetime.utcnow()

    db.session.commit()

    # Invalidate caches
    invalidate_cache(f'room_reviews:{review.room_id}')

    logger.info(f"Review {review_id} flagged by user {current_user['username']}: {reason}")

    return success_response(message="Review flagged for moderation")


@app.route('/api/reviews/flagged', methods=['GET'])
@jwt_required()
@moderator_required
@handle_errors
def get_flagged_reviews():
    """
    Get all flagged reviews (Moderator/Admin only).

    Query Parameters:
        page: Page number (default: 1)
        per_page: Items per page (default: 20, max: 100)

    Returns:
        200: List of flagged reviews
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    query = Review.query.filter_by(is_flagged=True).order_by(Review.flagged_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    reviews = []
    for review in pagination.items:
        user = User.query.get(review.user_id)
        flagger = User.query.get(review.flagged_by) if review.flagged_by else None

        reviews.append({
            'id': review.id,
            'room_id': review.room_id,
            'user': {
                'id': user.id,
                'username': user.username
            },
            'rating': review.rating,
            'comment': review.comment,
            'flag_reason': review.flag_reason,
            'flagged_by': {
                'id': flagger.id,
                'username': flagger.username
            } if flagger else None,
            'flagged_at': review.flagged_at.isoformat(),
            'is_hidden': review.is_hidden
        })

    return paginated_response(reviews, page, per_page, pagination.total)


@app.route('/api/reviews/<int:review_id>/moderate', methods=['PUT'])
@jwt_required()
@moderator_required
@handle_errors
@validate_json
@audit_log('moderate_review', 'review')
def moderate_review(review_id):
    """
    Moderate a review (Moderator/Admin only).

    Request Body:
        action: Action to take (approve, hide, delete) (required)
        reason: Reason for action (optional)

    Returns:
        200: Review moderated successfully
        404: Review not found
    """
    current_user = get_current_user()

    review = Review.query.get(review_id)
    if not review:
        return not_found_response("Review not found")

    data = request.get_json()
    validate_required_fields(data, ['action'])

    action = data['action']
    reason = sanitize_string(data.get('reason', ''), max_length=200)

    if action == 'approve':
        review.is_flagged = False
        review.flag_reason = None
        review.is_hidden = False
        message = "Review approved"

    elif action == 'hide':
        review.is_hidden = True
        review.hidden_reason = reason
        message = "Review hidden"

    elif action == 'delete':
        room_id = review.room_id
        user_id = review.user_id
        db.session.delete(review)
        db.session.commit()

        invalidate_cache(f'room_reviews:{room_id}')
        invalidate_cache(f'user_reviews:{user_id}')

        logger.info(f"Review {review_id} deleted by moderator {current_user['username']}")
        return success_response(message="Review deleted")

    else:
        return error_response("Invalid action. Must be: approve, hide, or delete")

    db.session.commit()

    # Invalidate caches
    invalidate_cache(f'room_reviews:{review.room_id}')

    logger.info(f"Review {review_id} moderated ({action}) by {current_user['username']}")

    return success_response(message=message)


@app.route('/api/reviews/<int:review_id>/helpful', methods=['POST'])
@jwt_required()
@handle_errors
@rate_limit(limit=50, window=3600)
def mark_helpful(review_id):
    """
    Mark a review as helpful.

    Returns:
        200: Review marked as helpful
        404: Review not found
    """
    review = Review.query.get(review_id)
    if not review:
        return not_found_response("Review not found")

    review.helpful_count += 1
    db.session.commit()

    # Invalidate caches
    invalidate_cache(f'room_reviews:{review.room_id}')

    return success_response({'helpful_count': review.helpful_count}, message="Marked as helpful")


@app.route('/api/reviews/<int:review_id>/unhelpful', methods=['POST'])
@jwt_required()
@handle_errors
@rate_limit(limit=50, window=3600)
def mark_unhelpful(review_id):
    """
    Mark a review as unhelpful.

    Returns:
        200: Review marked as unhelpful
        404: Review not found
    """
    review = Review.query.get(review_id)
    if not review:
        return not_found_response("Review not found")

    review.unhelpful_count += 1
    db.session.commit()

    # Invalidate caches
    invalidate_cache(f'room_reviews:{review.room_id}')

    return success_response({'unhelpful_count': review.unhelpful_count}, message="Marked as unhelpful")


if __name__ == '__main__':
    port = int(os.getenv('REVIEW_SERVICE_PORT', 5004))
    app.run(host='0.0.0.0', port=port, debug=config.DEBUG)
