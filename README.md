# Smart Meeting Room Management System

**Software Tools Lab - Fall 2025-2026 Final Project**

A comprehensive microservices-based backend system for managing meeting room bookings, reviews, and resource allocation.

## Team Members

- **Ahmad Yateem** - Users Service & Bookings Service
- **Hassan Fouani** - Rooms Service & Reviews Service

## Project Overview

The Smart Meeting Room Management System is a distributed microservices architecture built with Flask, providing complete meeting room management capabilities with advanced features including:

- User authentication and RBAC (Role-Based Access Control)
- Meeting room inventory management
- Intelligent booking system with conflict detection
- Review and rating system with moderation
- Asynchronous messaging with RabbitMQ
- Redis caching for performance optimization
- Circuit breaker pattern for fault tolerance
- Real-time monitoring with Prometheus and Grafana

## Technology Stack

- **Backend Framework**: Flask 3.0
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy 2.0
- **Authentication**: JWT (Flask-JWT-Extended)
- **Caching**: Redis 7
- **Message Queue**: RabbitMQ 3
- **Monitoring**: Prometheus + Grafana
- **Containerization**: Docker & Docker Compose
- **Testing**: Pytest with coverage
- **Documentation**: Sphinx
- **API Testing**: Postman

## Architecture

### Microservices

1. **Users Service** (Port 5001)
   - User registration and authentication
   - Profile management
   - Role-based access control
   - Booking history tracking

2. **Rooms Service** (Port 5002)
   - Room inventory management
   - Availability checking
   - Equipment and amenities tracking
   - Advanced search and filtering

3. **Bookings Service** (Port 5003)
   - Booking creation and management
   - Conflict detection and resolution
   - Recurring bookings support
   - Availability matrix generation

4. **Reviews Service** (Port 5004)
   - Review submission and management
   - Rating aggregation
   - Moderation and flagging system
   - Helpful/unhelpful voting

### Supporting Services

- **PostgreSQL**: Centralized database
- **Redis**: Caching layer
- **RabbitMQ**: Async message queue
- **Prometheus**: Metrics collection
- **Grafana**: Monitoring dashboards

## User Roles & Permissions

### Admin
- Full system access
- User management
- Room CRUD operations
- Booking override/cancellation
- Complete review moderation

### Regular User
- Profile management
- Room browsing
- Create/update/cancel own bookings
- Submit/update/delete own reviews

### Facility Manager
- Room management (CRUD)
- Equipment/amenities updates
- View all bookings
- Cannot manage users

### Moderator
- Review moderation only
- Flag/hide/approve reviews
- View moderation queue

### Auditor
- Read-only access to all data
- Access to audit logs
- No write permissions

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.10+
- Make (optional, for using Makefile commands)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd smartmeetingroom_AhmadYateem_HassanFouani
   ```

2. **Configure environment**
   ```bash
   cp configs/.env.template configs/.env
   # Edit configs/.env with your settings
   ```

3. **Start all services**
   ```bash
   make up
   # OR
   docker-compose up -d
   ```

4. **Verify services are running**
   ```bash
   make health
   ```

### Accessing Services

- **Users Service**: http://localhost:5001
- **Rooms Service**: http://localhost:5002
- **Bookings Service**: http://localhost:5003
- **Reviews Service**: http://localhost:5004
- **Grafana Dashboard**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **RabbitMQ Management**: http://localhost:15672 (admin/admin)

## API Documentation

### Authentication

All protected endpoints require a JWT token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

### Users Service Endpoints

#### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login
- `POST /api/auth/refresh` - Refresh access token

#### User Management
- `GET /api/users` - Get all users (Admin only)
- `GET /api/users/<id>` - Get user by ID
- `GET /api/users/profile` - Get current user profile
- `PUT /api/users/profile` - Update profile
- `DELETE /api/users/<id>` - Delete user (Admin only)
- `GET /api/users/<id>/bookings` - Get user booking history

### Rooms Service Endpoints

- `GET /api/rooms` - List all rooms (with filtering)
- `GET /api/rooms/<id>` - Get room details
- `POST /api/rooms` - Create room (Facility Manager/Admin)
- `PUT /api/rooms/<id>` - Update room (Facility Manager/Admin)
- `DELETE /api/rooms/<id>` - Delete room (Admin only)
- `GET /api/rooms/available` - Get available rooms
- `POST /api/rooms/search` - Advanced room search

### Bookings Service Endpoints

- `GET /api/bookings` - Get all bookings
- `GET /api/bookings/<id>` - Get booking details
- `POST /api/bookings` - Create booking
- `PUT /api/bookings/<id>` - Update booking
- `DELETE /api/bookings/<id>` - Cancel booking
- `POST /api/bookings/check-availability` - Check availability
- `GET /api/bookings/conflicts` - Get conflicts (Admin only)

### Reviews Service Endpoints

- `POST /api/reviews` - Submit review
- `GET /api/reviews/<id>` - Get review details
- `PUT /api/reviews/<id>` - Update review
- `DELETE /api/reviews/<id>` - Delete review
- `GET /api/reviews/room/<room_id>` - Get room reviews
- `POST /api/reviews/<id>/flag` - Flag review
- `GET /api/reviews/flagged` - Get flagged reviews (Moderator)
- `PUT /api/reviews/<id>/moderate` - Moderate review (Moderator)
- `POST /api/reviews/<id>/helpful` - Mark helpful
- `POST /api/reviews/<id>/unhelpful` - Mark unhelpful

## Part II Enhancements

### 1. Circuit Breaker Pattern (Ahmad Yateem)
**Category**: Enhanced Inter-Service Communication

Implements fault-tolerant inter-service communication with automatic failure detection and recovery:
- Monitors service health and failure rates
- Opens circuit after threshold failures
- Prevents cascading failures
- Automatic recovery attempts
- Located in `utils/circuit_breaker.py`

### 2. Asynchronous Messaging with RabbitMQ (Ahmad Yateem)
**Category**: Scalability and Reliability

Asynchronous event processing for:
- Booking confirmations
- Cancellation notifications
- Review alerts
- System monitoring
- Located in `messaging/` directory

### 3. Redis Caching (Hassan Fouani)
**Category**: Performance Optimization

High-performance caching layer:
- User profile caching
- Room availability caching
- Review aggregation caching
- Configurable TTL
- Cache invalidation strategies
- Located in `utils/cache.py`

### 4. Prometheus + Grafana Monitoring (Hassan Fouani)
**Category**: Analytics and Insights

Real-time monitoring and visualization:
- Request metrics per service
- Response times and latency
- Error rates and patterns
- System resource usage
- Custom business metrics
- Configured in `docker/prometheus/` and `docker/grafana/`

## Development

### Running Tests

```bash
# All tests with coverage
make test

# Unit tests only
make test-unit

# Integration tests
make test-integration
```

### Code Quality

```bash
# Run linters
make lint

# Format code
make format

# Run all checks
make check
```

### Generate Documentation

```bash
# Generate Sphinx documentation
make docs

# Serve documentation locally
make docs-serve
```

### Performance Profiling

```bash
# Run performance profiling
make profile

# Memory profiling
make profile-memory
```

## Database Schema

### Users Table
- id, username, email, password_hash
- full_name, role, is_active
- last_login, failed_login_attempts, locked_until
- created_at, updated_at

### Rooms Table
- id, name, capacity, floor, building, location
- equipment (array), amenities (array)
- status, hourly_rate, image_url
- created_at, updated_at

### Bookings Table
- id, user_id, room_id, title, description
- start_time, end_time, status, attendees
- is_recurring, recurrence_pattern, recurrence_end_date
- cancellation_reason, cancelled_at, cancelled_by
- created_at, updated_at

### Reviews Table
- id, user_id, room_id, booking_id
- rating, title, comment, pros, cons
- is_flagged, flag_reason, flagged_by, flagged_at
- is_hidden, hidden_reason
- helpful_count, unhelpful_count
- created_at, updated_at, edited_at

### Audit Logs Table
- id, user_id, service, action
- resource_type, resource_id
- old_values, new_values (JSONB)
- ip_address, user_agent
- success, error_message
- created_at

## Security Features

1. **Authentication & Authorization**
   - JWT-based authentication
   - Role-based access control (RBAC)
   - Password hashing with bcrypt
   - Account lockout after failed attempts

2. **Input Validation & Sanitization**
   - SQL injection prevention
   - XSS protection
   - Input validation on all endpoints
   - Sanitization of user-generated content

3. **Rate Limiting**
   - Per-user and per-IP rate limiting
   - Configurable limits per endpoint
   - Protection against brute force attacks

4. **Audit Logging**
   - Complete audit trail
   - User action tracking
   - IP address and user agent logging
   - Error tracking

## Makefile Commands

```bash
make help          # Show all available commands
make install       # Install dependencies
make build         # Build Docker images
make up           # Start all services
make down         # Stop all services
make logs         # Show logs from all services
make test         # Run tests with coverage
make docs         # Generate documentation
make profile      # Run performance profiling
make clean        # Clean up containers and caches
make health       # Check service health
make backup-db    # Backup database
```

## Monitoring & Observability

### Prometheus Metrics

Access at http://localhost:9090

- Request count and rate
- Response time percentiles
- Error rates
- Custom business metrics

### Grafana Dashboards

Access at http://localhost:3000 (admin/admin)

- Service performance overview
- Error rate monitoring
- Resource utilization
- Business metrics visualization

### Application Logs

Structured JSON logging for all services:
- Request/response logging
- Error tracking
- Audit trail
- Performance metrics

## Troubleshooting

### Services won't start

```bash
# Check Docker is running
docker ps

# Check logs for errors
make logs

# Rebuild containers
make rebuild
```

### Database connection issues

```bash
# Reset database
make db-reset

# Check database is running
docker-compose ps postgres
```

### Port conflicts

Edit `docker-compose.yml` to change port mappings if needed.

### RabbitMQ connection issues

```bash
# Check RabbitMQ is running
docker-compose ps rabbitmq

# Access RabbitMQ management UI
# http://localhost:15672 (admin/admin)
```

## Testing with Postman

Postman collections are available in the `postman/` directory:

1. Import the collections into Postman
2. Set up environment variables
3. Run the authentication requests first to get JWT tokens
4. Use the tokens in subsequent requests

## Project Structure

```
smartmeetingroom_AhmadYateem_HassanFouani/
├── configs/                 # Configuration files
├── database/               # Database models and migrations
├── docker/                 # Docker configurations
├── docs/                   # Sphinx documentation
├── messaging/              # RabbitMQ publisher/consumer
├── profiling/             # Performance profiling scripts
├── postman/               # Postman collections
├── services/              # Microservices
│   ├── users/            # Users service
│   ├── rooms/            # Rooms service
│   ├── bookings/         # Bookings service
│   └── reviews/          # Reviews service
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   └── integration/       # Integration tests
├── utils/                 # Shared utilities
├── docker-compose.yml     # Docker Compose configuration
├── Makefile              # Build automation
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Contributing

This is an academic project for EECE435L Software Tools Lab.

## License

This project is submitted as part of the EECE435L course requirements.

## Acknowledgments

- Faculty of Engineering and Architecture
- Software Tools Lab - Fall 2025-2026
- Course Instructor and Teaching Assistants
