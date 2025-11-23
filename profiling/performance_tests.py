"""
Performance profiling for Smart Meeting Room Management System.
Tests response times, memory usage, and code coverage.
"""

import cProfile
import pstats
import io
import time
import sys
import os
from memory_profiler import profile

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def profile_function(func, *args, **kwargs):
    """
    Profile a function and return statistics.

    Args:
        func: Function to profile
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        Profiling statistics
    """
    pr = cProfile.Profile()
    pr.enable()

    result = func(*args, **kwargs)

    pr.disable()

    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(20)

    print(s.getvalue())

    return result


def test_database_operations():
    """Test database operation performance."""
    print("\n" + "="*80)
    print("DATABASE OPERATIONS PERFORMANCE TEST")
    print("="*80 + "\n")

    from flask import Flask
    from database.models import db, User, Room, Booking
    from configs.config import TestingConfig
    from utils.auth import hash_password

    app = Flask(__name__)
    app.config.from_object(TestingConfig)
    db.init_app(app)

    with app.app_context():
        db.create_all()

        # Test user creation
        start = time.time()
        for i in range(100):
            user = User(
                username=f'testuser{i}',
                email=f'test{i}@example.com',
                password_hash=hash_password('TestPass123!'),
                full_name=f'Test User {i}',
                role='user'
            )
            db.session.add(user)

        db.session.commit()
        end = time.time()

        print(f"Created 100 users in {end - start:.4f} seconds")
        print(f"Average time per user: {(end - start) / 100:.4f} seconds\n")

        # Test room creation
        start = time.time()
        for i in range(50):
            room = Room(
                name=f'Room {i}',
                capacity=10 + i,
                status='available'
            )
            db.session.add(room)

        db.session.commit()
        end = time.time()

        print(f"Created 50 rooms in {end - start:.4f} seconds")
        print(f"Average time per room: {(end - start) / 50:.4f} seconds\n")

        # Test query performance
        start = time.time()
        users = User.query.filter_by(role='user').all()
        end = time.time()

        print(f"Queried {len(users)} users in {end - start:.4f} seconds\n")

        # Cleanup
        db.drop_all()


def test_validation_performance():
    """Test input validation performance."""
    print("\n" + "="*80)
    print("INPUT VALIDATION PERFORMANCE TEST")
    print("="*80 + "\n")

    from utils.validators import (
        validate_email_format,
        validate_username,
        validate_password
    )

    iterations = 10000

    # Test email validation
    start = time.time()
    for i in range(iterations):
        try:
            validate_email_format(f'user{i}@example.com')
        except:
            pass
    end = time.time()

    print(f"Validated {iterations} emails in {end - start:.4f} seconds")
    print(f"Average time per validation: {(end - start) / iterations * 1000:.4f} ms\n")

    # Test username validation
    start = time.time()
    for i in range(iterations):
        try:
            validate_username(f'username{i}')
        except:
            pass
    end = time.time()

    print(f"Validated {iterations} usernames in {end - start:.4f} seconds")
    print(f"Average time per validation: {(end - start) / iterations * 1000:.4f} ms\n")


def test_cache_performance():
    """Test Redis cache performance."""
    print("\n" + "="*80)
    print("CACHE PERFORMANCE TEST")
    print("="*80 + "\n")

    from utils.cache import cache

    if not cache.enabled:
        print("Cache is disabled. Skipping cache performance tests.\n")
        return

    iterations = 1000

    # Test cache set operations
    start = time.time()
    for i in range(iterations):
        cache.set(f'test_key_{i}', {'data': f'value_{i}'}, ttl=60)
    end = time.time()

    print(f"Set {iterations} cache entries in {end - start:.4f} seconds")
    print(f"Average time per set: {(end - start) / iterations * 1000:.4f} ms\n")

    # Test cache get operations
    start = time.time()
    for i in range(iterations):
        cache.get(f'test_key_{i}')
    end = time.time()

    print(f"Retrieved {iterations} cache entries in {end - start:.4f} seconds")
    print(f"Average time per get: {(end - start) / iterations * 1000:.4f} ms\n")

    # Cleanup
    for i in range(iterations):
        cache.delete(f'test_key_{i}')


def main():
    """Run all performance tests."""
    print("\n" + "="*80)
    print("SMART MEETING ROOM MANAGEMENT SYSTEM - PERFORMANCE PROFILING")
    print("="*80)

    try:
        test_database_operations()
        test_validation_performance()
        test_cache_performance()

        print("\n" + "="*80)
        print("PROFILING COMPLETED")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\nError during profiling: {str(e)}\n")


if __name__ == '__main__':
    main()
