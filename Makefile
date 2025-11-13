# Makefile for VigilantEye Docker Compose operations

# Variables
DOCKER_COMPOSE = docker-compose
DOCKER_COMPOSE_TEST = docker-compose -f docker-compose.test.yml
BACKEND_CONTAINER = vigilanteye-backend
FRONTEND_CONTAINER = vigilanteye-frontend

.PHONY: help up down build rebuild logs logs-backend logs-db ps restart restart-backend clean test test-backend test-frontend shell-backend shell-db db-migrate db-seed db-reset pull-models prune

# Default target
help:
	@echo "VigilantEye Docker Commands"
	@echo "==========================="
	@echo ""
	@echo "Development:"
	@echo "  make up              - Start all services in detached mode"
	@echo "  make down            - Stop all services"
	@echo "  make logs            - View logs from all services"
	@echo "  make logs-backend    - View backend logs only"
	@echo "  make logs-db         - View database logs"
	@echo "  make restart         - Restart all services"
	@echo "  make restart-backend - Restart backend services only"
	@echo "  make ps              - List running containers"
	@echo ""
	@echo "Building:"
	@echo "  make build           - Build all images"
	@echo "  make rebuild         - Rebuild all images without cache"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate      - Run database migrations"
	@echo "  make db-seed         - Seed database with test data"
	@echo "  make db-reset        - Reset database to clean state"
	@echo "  make shell-db        - Open MySQL shell"
	@echo ""
	@echo "Testing:"
	@echo "  make test            - Run all tests (backend + frontend)"
	@echo "  make test-backend    - Run backend tests only"
	@echo "  make test-frontend   - Run frontend tests only"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean           - Remove all containers, volumes, and images (WARNING: data loss)"
	@echo "  make prune           - Remove unused Docker resources"
	@echo ""
	@echo "Debugging:"
	@echo "  make shell-backend   - Open shell in backend container"
	@echo "  make pull-models     - Pre-download AI models"

# Development commands
up:
	@echo "Starting all services..."
	$(DOCKER_COMPOSE) up -d

down:
	@echo "Stopping all services..."
	$(DOCKER_COMPOSE) down

build:
	@echo "Building Docker images..."
	$(DOCKER_COMPOSE) build

rebuild:
	@echo "Rebuilding Docker images without cache..."
	$(DOCKER_COMPOSE) build --no-cache

logs:
	@echo "Following logs from all services (Ctrl+C to exit)..."
	$(DOCKER_COMPOSE) logs -f

logs-backend:
	@echo "Following logs from backend services (Ctrl+C to exit)..."
	$(DOCKER_COMPOSE) logs -f backend celery-worker celery-beat

logs-db:
	@echo "Following logs from database services (Ctrl+C to exit)..."
	$(DOCKER_COMPOSE) logs -f mysql redis chromadb

ps:
	@echo "Container status:"
	$(DOCKER_COMPOSE) ps

restart:
	@echo "Restarting all services..."
	$(DOCKER_COMPOSE) restart

restart-backend:
	@echo "Restarting backend services..."
	$(DOCKER_COMPOSE) restart backend celery-worker celery-beat

# Cleanup commands
clean:
	@echo "WARNING: This will delete all containers, volumes, and images!"
	@echo "This includes all data (databases, storage, logs)."
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE) down -v --rmi all; \
		echo "Cleanup complete."; \
	else \
		echo "Cleanup cancelled."; \
	fi

# Testing commands
test:
	@echo "Running test suite..."
	$(DOCKER_COMPOSE_TEST) up --abort-on-container-exit --exit-code-from backend-test
	@echo "Cleaning up test containers..."
	$(DOCKER_COMPOSE_TEST) down -v

test-backend:
	@echo "Running backend tests..."
	$(DOCKER_COMPOSE_TEST) run --rm backend-test

test-frontend:
	@echo "Running frontend tests..."
	$(DOCKER_COMPOSE_TEST) run --rm frontend-test

# Database commands
shell-backend:
	@echo "Opening shell in backend container..."
	$(DOCKER_COMPOSE) exec backend /bin/bash

shell-db:
	@echo "Opening MySQL shell..."
	$(DOCKER_COMPOSE) exec mysql mysql -u root -proot vigilanteye

db-migrate:
	@echo "Running database migrations..."
	$(DOCKER_COMPOSE) exec backend alembic upgrade head

db-seed:
	@echo "Seeding database with test data..."
	$(DOCKER_COMPOSE) exec backend python scripts/seed_test_data.py

db-reset:
	@echo "Resetting database to clean state..."
	@echo "WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE) exec backend alembic downgrade base; \
		$(DOCKER_COMPOSE) exec backend alembic upgrade head; \
		echo "Database reset complete."; \
	else \
		echo "Database reset cancelled."; \
	fi

# Utility commands
pull-models:
	@echo "Pre-downloading AI models..."
	$(DOCKER_COMPOSE) exec backend python -c "from src.utils.model_manager import ModelManager; mm = ModelManager(); mm.download_yolov8_model(); mm.download_whisper_model(); mm.download_blip2_model(); mm.download_ollama_model();"

prune:
	@echo "WARNING: This will remove unused Docker resources!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker system prune -af --volumes; \
		echo "Prune complete."; \
	else \
		echo "Prune cancelled."; \
	fi

