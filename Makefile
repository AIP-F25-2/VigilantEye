# VigilantEye API Makefile

.PHONY: help build up down logs restart clean dev

# Default target
help:
	@echo "VigilantEye API - Available Commands:"
	@echo ""
	@echo "  make build     - Build Docker images"
	@echo "  make up        - Start all services"
	@echo "  make down      - Stop all services"
	@echo "  make logs      - View logs from all services"
	@echo "  make restart   - Restart all services"
	@echo "  make clean     - Stop services and remove volumes"
	@echo "  make dev       - Start in development mode"
	@echo "  make shell     - Open shell in API container"
	@echo "  make db-shell  - Open MySQL shell"
	@echo ""

# Build Docker images
build:
	docker-compose build

# Start all services
up:
	docker-compose up -d

# Stop all services
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

# Restart services
restart:
	docker-compose restart

# Clean up (remove volumes)
clean:
	docker-compose down -v
	docker system prune -f

# Development mode
dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Open shell in API container
shell:
	docker-compose exec api bash

# Open MySQL shell
db-shell:
	docker-compose exec mysql mysql -u vigilanteye_user -p vigilanteye_db

# Show status
status:
	docker-compose ps
