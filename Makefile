.PHONY: help dev test lint format build clean install-backend install-frontend install-temporal

help:  ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development
dev:  ## Start all services in development mode
	docker-compose -f infra/docker/docker-compose.yml up --build

dev-detach:  ## Start all services in background
	docker-compose -f infra/docker/docker-compose.yml up --build -d

dev-backend:  ## Start backend service only
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:  ## Start frontend service only
	cd frontend && bun run dev

dev-worker:  ## Start temporal worker only
	cd temporal && python worker.py

logs:  ## View logs from all services
	docker-compose -f infra/docker/docker-compose.yml logs -f

logs-backend:  ## View backend logs
	docker-compose -f infra/docker/docker-compose.yml logs -f backend

stop:  ## Stop all services
	docker-compose -f infra/docker/docker-compose.yml down

clean:  ## Stop and remove all containers and volumes
	docker-compose -f infra/docker/docker-compose.yml down -v

##@ Testing
test:  ## Run all tests
	@echo "Running backend tests..."
	cd backend && pytest
	@echo "Running frontend tests..."
	cd frontend && bun test

test-backend:  ## Run backend tests
	cd backend && pytest

test-backend-coverage:  ## Run backend tests with coverage
	cd backend && pytest --cov=app --cov-report=html

test-frontend:  ## Run frontend tests
	cd frontend && bun test

test-frontend-coverage:  ## Run frontend tests with coverage
	cd frontend && bun test --coverage

##@ Linting & Formatting
lint:  ## Run all linters
	cd backend && ruff check .
	cd frontend && bun run lint

lint-backend:  ## Run backend linter
	cd backend && ruff check .

lint-frontend:  ## Run frontend linter
	cd frontend && bun run lint

format:  ## Format all code
	cd backend && ruff format .
	cd frontend && bun run format

format-backend:  ## Format backend code
	cd backend && ruff format .

format-frontend:  ## Format frontend code
	cd frontend && bun run format

format-check:  ## Check formatting without changing files
	cd backend && ruff format --check .
	cd frontend && bun run format:check

##@ Installation
install: install-backend install-frontend install-temporal  ## Install all dependencies

install-backend:  ## Install backend dependencies
	cd backend && uv pip install -e .

install-backend-dev:  ## Install backend dev dependencies
	cd backend && uv pip install -e ".[dev]"

install-frontend:  ## Install frontend dependencies
	cd frontend && bun install

install-temporal:  ## Install temporal worker dependencies
	cd temporal && uv pip install -e .

##@ Build
build:  ## Build all Docker images
	docker-compose -f infra/docker/docker-compose.yml build

build-backend:  ## Build backend Docker image
	docker build -t code-doc-backend ./backend

build-frontend:  ## Build frontend Docker image
	docker build -t code-doc-frontend ./frontend

build-worker:  ## Build temporal worker Docker image
	docker build -t code-doc-worker ./temporal

##@ Database & Storage
db-reset:  ## Reset ChromaDB data (WARNING: deletes all data)
	docker-compose -f infra/docker/docker-compose.yml down -v
	docker-compose -f infra/docker/docker-compose.yml up -d chromadb

db-backup:  ## Backup ChromaDB data
	docker cp code-doc-chromadb:/chroma/chroma ./chromadb_backup

db-restore:  ## Restore ChromaDB data
	docker cp ./chromadb_backup code-doc-chromadb:/chroma/chroma

##@ Utilities
shell-backend:  ## Open shell in backend container
	docker-compose -f infra/docker/docker-compose.yml exec backend bash

shell-postgres:  ## Open PostgreSQL shell
	docker-compose -f infra/docker/docker-compose.yml exec postgres psql -U temporal -d temporal

health:  ## Check health of all services
	@echo "Checking backend health..."
	@curl -s http://localhost:8000/health || echo "Backend unhealthy"
	@echo "Checking frontend health..."
	@curl -s http://localhost:3000/ || echo "Frontend unhealthy"
	@echo "Checking ChromaDB health..."
	@curl -s http://localhost:8001/api/v1/heartbeat || echo "ChromaDB unhealthy"

setup:  ## Initial setup (install pre-commit hooks)
	pre-commit install
	@echo "Setup complete! Run 'make dev' to start development."
