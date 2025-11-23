.PHONY: help install test build run stop clean docs profile lint format check

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
RESET := \033[0m

help: ## Show this help message
	@echo "$(BLUE)Smart Meeting Room Management System - Makefile$(RESET)"
	@echo "$(GREEN)Available commands:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BLUE)%-15s$(RESET) %s\n", $$1, $$2}'

install: ## Install dependencies
	@echo "$(GREEN)Installing dependencies...$(RESET)"
	python -m pip install --upgrade pip
	pip install -r requirements.txt

test: ## Run all tests with coverage
	@echo "$(GREEN)Running tests with coverage...$(RESET)"
	pytest tests/ -v --cov=services --cov=utils --cov=database \
		--cov-report=html --cov-report=term-missing \
		--cov-report=xml

test-unit: ## Run unit tests only
	@echo "$(GREEN)Running unit tests...$(RESET)"
	pytest tests/unit/ -v

test-integration: ## Run integration tests only
	@echo "$(GREEN)Running integration tests...$(RESET)"
	pytest tests/integration/ -v

build: ## Build Docker images
	@echo "$(GREEN)Building Docker images...$(RESET)"
	docker-compose build

up: ## Start all services
	@echo "$(GREEN)Starting all services...$(RESET)"
	docker-compose up -d
	@echo "$(BLUE)Services started:$(RESET)"
	@echo "  Users Service:    http://localhost:5001"
	@echo "  Rooms Service:    http://localhost:5002"
	@echo "  Bookings Service: http://localhost:5003"
	@echo "  Reviews Service:  http://localhost:5004"
	@echo "  Grafana:          http://localhost:3000 (admin/admin)"
	@echo "  Prometheus:       http://localhost:9090"
	@echo "  RabbitMQ:         http://localhost:15672 (admin/admin)"

run: up ## Alias for 'up'

down: ## Stop all services
	@echo "$(RED)Stopping all services...$(RESET)"
	docker-compose down

stop: down ## Alias for 'down'

logs: ## Show logs from all services
	docker-compose logs -f

logs-users: ## Show logs from users service
	docker-compose logs -f users-service

logs-rooms: ## Show logs from rooms service
	docker-compose logs -f rooms-service

logs-bookings: ## Show logs from bookings service
	docker-compose logs -f bookings-service

logs-reviews: ## Show logs from reviews service
	docker-compose logs -f reviews-service

restart: ## Restart all services
	@echo "$(GREEN)Restarting all services...$(RESET)"
	docker-compose restart

rebuild: ## Rebuild and restart all services
	@echo "$(GREEN)Rebuilding all services...$(RESET)"
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

clean: ## Clean up containers, volumes, and caches
	@echo "$(RED)Cleaning up...$(RESET)"
	docker-compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .coverage -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	find . -type f -name '.coverage' -delete
	rm -rf coverage_html_report htmlcov
	rm -rf docs/_build
	@echo "$(GREEN)Cleanup complete!$(RESET)"

docs: ## Generate Sphinx documentation
	@echo "$(GREEN)Generating documentation...$(RESET)"
	cd docs && make html
	@echo "$(BLUE)Documentation generated at: docs/_build/html/index.html$(RESET)"

docs-serve: docs ## Generate and serve documentation
	@echo "$(GREEN)Serving documentation at http://localhost:8000$(RESET)"
	cd docs/_build/html && python -m http.server 8000

profile: ## Run performance profiling
	@echo "$(GREEN)Running performance profiling...$(RESET)"
	python profiling/performance_tests.py
	@echo "$(BLUE)Profiling results saved to profiling/results/$(RESET)"

profile-memory: ## Run memory profiling
	@echo "$(GREEN)Running memory profiling...$(RESET)"
	python -m memory_profiler profiling/memory_tests.py

lint: ## Run code linting
	@echo "$(GREEN)Running linters...$(RESET)"
	flake8 services/ utils/ database/ --max-line-length=120 --exclude=__pycache__,venv
	pylint services/ utils/ database/ --max-line-length=120 || true

format: ## Format code with black
	@echo "$(GREEN)Formatting code...$(RESET)"
	black services/ utils/ database/ tests/ --line-length=120

check: lint test ## Run linting and tests

db-init: ## Initialize database
	@echo "$(GREEN)Initializing database...$(RESET)"
	python -c "from database.models import init_db; from flask import Flask; app = Flask(__name__); app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://admin:secure_password@localhost:5432/smartmeetingroom'; init_db(app)"

db-migrate: ## Run database migrations
	@echo "$(GREEN)Running database migrations...$(RESET)"
	alembic upgrade head

db-reset: ## Reset database (WARNING: deletes all data)
	@echo "$(RED)Resetting database...$(RESET)"
	docker-compose down postgres
	docker volume rm smartmeetingroom_ahmadyateem_hassanfouani_postgres_data || true
	docker-compose up -d postgres
	sleep 5
	make db-init

health: ## Check health of all services
	@echo "$(GREEN)Checking service health...$(RESET)"
	@curl -s http://localhost:5001/health || echo "$(RED)Users service is down$(RESET)"
	@curl -s http://localhost:5002/health || echo "$(RED)Rooms service is down$(RESET)"
	@curl -s http://localhost:5003/health || echo "$(RED)Bookings service is down$(RESET)"
	@curl -s http://localhost:5004/health || echo "$(RED)Reviews service is down$(RESET)"

ps: ## Show running containers
	docker-compose ps

stats: ## Show container stats
	docker stats

shell-users: ## Open shell in users service container
	docker-compose exec users-service /bin/sh

shell-rooms: ## Open shell in rooms service container
	docker-compose exec rooms-service /bin/sh

shell-bookings: ## Open shell in bookings service container
	docker-compose exec bookings-service /bin/sh

shell-reviews: ## Open shell in reviews service container
	docker-compose exec reviews-service /bin/sh

shell-db: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U admin -d smartmeetingroom

backup-db: ## Backup database
	@echo "$(GREEN)Backing up database...$(RESET)"
	docker-compose exec postgres pg_dump -U admin smartmeetingroom > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Database backed up!$(RESET)"

restore-db: ## Restore database from backup (usage: make restore-db FILE=backup.sql)
	@echo "$(GREEN)Restoring database from $(FILE)...$(RESET)"
	docker-compose exec -T postgres psql -U admin smartmeetingroom < $(FILE)
	@echo "$(GREEN)Database restored!$(RESET)"

consumer: ## Start message consumer
	@echo "$(GREEN)Starting RabbitMQ consumer...$(RESET)"
	python messaging/consumer.py

all: clean install build up docs ## Setup everything from scratch
	@echo "$(GREEN)All services are up and running!$(RESET)"
	@make health
