# LMS Backend Development Makefile
.PHONY: help install dev-install lint format test test-unit test-integration test-e2e clean docker-build docker-up docker-down docker-logs migrate db-seed api-docs check-env setup-hooks

# Default target
help: ## Show this help message
	@echo "LMS Backend Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install production dependencies
	pip install -r requirements.txt

dev-install: ## Install development dependencies
	pip install -r requirements-dev.txt
	pre-commit install

# Code Quality
lint: ## Run linting (flake8, mypy, black check)
	flake8 services/ shared/ --max-line-length=100 --extend-ignore=E203,W503
	mypy services/ shared/ --ignore-missing-imports
	black --check services/ shared/

format: ## Format code with black and isort
	black services/ shared/
	isort services/ shared/

type-check: ## Run type checking with mypy
	mypy services/ shared/ --ignore-missing-imports --show-error-codes

security-check: ## Run security checks with bandit
	bandit -r services/ shared/ -f json -o security-report.json

# Testing
test: ## Run all tests
	pytest tests/ -v --cov=services --cov=shared --cov-report=html --cov-report=term

test-unit: ## Run unit tests only
	pytest tests/unit/ -v --cov=services --cov=shared --cov-report=term

test-integration: ## Run integration tests
	pytest tests/integration/ -v --cov=services --cov=shared --cov-report=term

test-e2e: ## Run end-to-end tests
	pytest tests/e2e/ -v

test-load: ## Run load tests with Locust
	locust -f tests/load/locustfile.py --host=http://localhost:8000

# Database
db-health: ## Check database health
	python -c "import asyncio; from shared.common.database import health_check; print(asyncio.run(health_check()))"

db-migrate: ## Run database migrations
	alembic upgrade head

db-seed: ## Seed database with test data
	python scripts/seed_database.py

# Docker
docker-build: ## Build all Docker images
	docker-compose build

docker-up: ## Start all services with Docker
	docker-compose up -d

docker-down: ## Stop all services
	docker-compose down

docker-logs: ## Show logs from all services
	docker-compose logs -f

docker-clean: ## Remove all containers and volumes
	docker-compose down -v --remove-orphans

# Development
dev-server: ## Start development server with hot reload
	uvicorn services.api_gateway.main:app --reload --host 0.0.0.0 --port 8000

run-service: ## Run specific service (usage: make run-service SERVICE=auth)
	@if [ -z "$(SERVICE)" ]; then echo "Usage: make run-service SERVICE=<service-name>"; exit 1; fi
	uvicorn services.$(SERVICE).main:app --reload --host 0.0.0.0 --port 800$(shell echo $(SERVICE) | sed 's/.*-service//' | tr -d 'a-z')

# API Documentation
api-docs: ## Generate API documentation
	@echo "API Gateway: http://localhost:8000/docs"
	@echo "Auth Service: http://localhost:8001/docs"
	@echo "Course Service: http://localhost:8002/docs"
	@echo "User Service: http://localhost:8003/docs"
	@echo "AI Service: http://localhost:8004/docs"
	@echo "Assessment Service: http://localhost:8005/docs"
	@echo "Analytics Service: http://localhost:8006/docs"
	@echo "Notification Service: http://localhost:8007/docs"
	@echo "File Service: http://localhost:8008/docs"

api-collections: ## Generate Postman collections
	python scripts/generate_postman_collection.py

# Environment
check-env: ## Check environment configuration
	python scripts/check_environment.py

setup-hooks: ## Setup pre-commit hooks
	pre-commit install
	pre-commit install --hook-type commit-msg

# Cleanup
clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.log" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/

clean-all: clean ## Clean all including Docker
	docker system prune -f
	docker volume prune -f

# CI/CD
ci-test: ## Run CI test suite
	make lint
	make type-check
	make security-check
	make test-unit
	make test-integration

ci-build: ## Build for CI/CD
	docker build -t lms-backend:latest .

# Monitoring
health-check: ## Check health of all services
	curl -f http://localhost:8000/health/services

logs: ## Show application logs
	tail -f logs/app.log

# Utility
count-lines: ## Count lines of code
	find services/ shared/ -name "*.py" -exec wc -l {} + | tail -1

deps-update: ## Update dependencies
	pip-compile requirements.in
	pip-compile requirements-dev.in

# Quick development setup
setup-dev: dev-install setup-hooks check-env ## Setup complete development environment
	@echo "Development environment setup complete!"
	@echo "Run 'make docker-up' to start services"
	@echo "Run 'make dev-server' to start API gateway"