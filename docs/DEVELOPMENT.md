# Development Guide

This guide covers local development setup, workflows, and best practices for the Code Documentation Assistant project.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Services](#services)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

- **Python 3.12+** - Backend runtime
- **Bun** - Frontend package manager and runtime
- **Docker** - Containerization (for local services)
- **Docker Compose** - Orchestrate local services
- **Git** - Version control

### Optional Tools

- **uv** - Fast Python package manager (recommended)
- **Tilt** - Local development orchestration (optional)
- **pre-commit** - Git hooks for code quality

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd code-doc-assistant

# Run initial setup
make setup
# or
./scripts/setup.sh
```

This will:
- Install all dependencies (backend, frontend, temporal)
- Create environment configuration files
- Start background services (ChromaDB, Temporal)

### 2. Configure Environment

Edit `backend/.env` with your API keys:

```bash
cd backend
cp .env.example .env
# Edit .env with your API keys:
# - ANTHROPIC_API_KEY
# - JINA_API_KEY
# - OPENAI_API_KEY
```

### 3. Start Development Services

```bash
# Option 1: Start everything with Docker
make dev

# Option 2: Start services individually
make dev-backend    # Terminal 1: Backend API on :8000
make dev-frontend   # Terminal 2: Frontend on :3000
make dev-worker     # Terminal 3: Temporal worker
```

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Temporal UI**: http://localhost:7233

## Development Workflow

### Daily Development

1. **Start services**:
   ```bash
   make start-services  # ChromaDB, Temporal
   make dev-backend     # Terminal 1
   make dev-frontend    # Terminal 2
   ```

2. **Make changes** and see hot-reload in action

3. **Run tests**:
   ```bash
   make test           # All tests
   make test-backend   # Backend only
   make test-frontend  # Frontend only
   ```

4. **Format and lint**:
   ```bash
   make format    # Format all code
   make lint      # Check for issues
   ```

### Backend Development

```bash
cd backend

# Install dependencies
uv sync --all-extras

# Run development server
uvicorn app.main:app --reload

# Run tests
pytest
pytest tests/unit/test_secret_detection.py -v

# Run with coverage
pytest --cov=app --cov-report=html

# Type checking
mypy app
```

### Frontend Development

```bash
cd frontend

# Install dependencies
bun install

# Run development server
bun run dev

# Run tests
bun test

# Type checking
bun run type-check

# Build for production
bun run build
```

### Temporal Worker Development

```bash
cd temporal

# Install dependencies
uv sync --all-extras

# Start worker
python worker.py

# Run workflow tests
pytest tests/workflows/
```

## Testing

### Backend Tests

```bash
# Run all backend tests
make test-backend

# Run specific test file
cd backend && pytest tests/unit/test_secret_detection.py -v

# Run with coverage
make test-backend-coverage

# Run only unit tests
make test-unit

# Run integration tests
make test-integration
```

### Frontend Tests

```bash
# Run all frontend tests
make test-frontend

# Run with coverage
make test-frontend-coverage

# Watch mode
cd frontend && bun test --watch
```

### Test Coverage Goals

- **Backend**: 80% minimum coverage
- **Frontend**: 70% minimum coverage

## Project Structure

```
code-doc-assistant/
├── backend/                   # FastAPI application
│   ├── app/
│   │   ├── api/v1/           # REST endpoints
│   │   ├── agents/           # LangGraph agent
│   │   ├── core/             # Config, logging, security
│   │   ├── models/           # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   └── utils/            # Utilities (chunking, parsing, secrets)
│   ├── tests/                # Backend tests
│   └── pyproject.toml        # Python dependencies
│
├── frontend/                  # TanStack Start application
│   ├── app/
│   │   ├── components/       # React components
│   │   ├── lib/              # Utilities and API client
│   │   └── routes/           # File-based routing
│   ├── tests/                # Frontend tests
│   └── package.json          # Node dependencies
│
├── temporal/                  # Temporal workflows
│   ├── workflows/            # Workflow definitions
│   ├── activities/           # Activity implementations
│   └── worker.py             # Worker entry point
│
├── infra/                    # Infrastructure code
│   ├── docker/               # Docker Compose configuration
│   ├── k8s/                  # Kubernetes manifests
│   ├── monitoring/           # Prometheus, Grafana configs
│   └── Tiltfile             # Tilt configuration
│
├── scripts/                   # Utility scripts
│   └── setup.sh              # Environment setup
│
├── docs/                      # Documentation
│   └── DEVELOPMENT.md        # This file
│
└── Makefile                   # Common development commands
```

## Services

### Backend API (FastAPI)

- **Port**: 8000
- **Entry point**: `backend/app/main.py`
- **Hot reload**: Enabled with `--reload` flag

Key endpoints:
- `POST /api/v1/codebase/upload` - Upload codebase
- `POST /api/v1/chat` - Query codebase (SSE stream)
- `GET /api/v1/codebase` - List codebases
- `GET /api/v1/health` - Health check

### Frontend (TanStack Start)

- **Port**: 3000
- **Framework**: React with SSR
- **UI Library**: shadcn/ui + Tailwind CSS

### ChromaDB (Vector Store)

- **Port**: 8000
- **Purpose**: Store and query code embeddings
- **Data**: Persisted to `data/chromadb/`

Start manually:
```bash
cd backend
uv run chroma-run --host localhost --port 8000 --path ../data/chromadb
```

### Temporal (Workflow Engine)

- **UI Port**: 7233
- **Purpose**: Orchestrate codebase ingestion
- **Data**: Persisted to `data/temporal/`

Start manually:
```bash
temporal server start-dev --db-filename data/temporal/temporal.db
```

## Troubleshooting

### Backend Issues

**Problem**: Import errors or missing dependencies
```bash
cd backend
uv sync --all-extras
```

**Problem**: Tests failing due to environment variables
```bash
# Ensure backend/.env exists with required keys
cat backend/.env
```

**Problem**: Tree-sitter parsing failures
- The code parser has known issues with tree-sitter v1 compatibility
- Tests may fail for actual parsing but language detection works

### Frontend Issues

**Problem**: Bun not found
```bash
# Install bun
curl -fsSL https://bun.sh/install | bash
```

**Problem**: Type errors
```bash
cd frontend
bun run type-check
```

### Service Issues

**Problem**: ChromaDB not connecting
```bash
# Check if ChromaDB is running
curl http://localhost:8000/api/v1/heartbeat

# Restart ChromaDB
make stop-services
make start-services
```

**Problem**: Temporal worker not processing
```bash
# Check Temporal UI at http://localhost:7233
# Look for:
# - Workflow executions
# - Task queue registrations
# - Worker availability
```

### Docker Issues

**Problem**: Container won't start
```bash
# Rebuild containers
make clean
docker-compose -f infra/docker/docker-compose.yml build

# Check container logs
docker-compose -f infra/docker/docker-compose.yml logs -f backend
```

## Code Quality

### Linting

```bash
# Check all code
make lint

# Auto-fix issues
make lint-fix

# Check formatting
make format-check
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
make setup

# Or manually
pre-commit install
```

## Performance Targets

- **Query latency**: <3s p95
- **Ingestion**: 1,000 files in 10 minutes
- **Retrieval accuracy**: >85% relevant in top-5
- **Concurrent users**: 100 (MVP)

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [TanStack Start Documentation](https://tanstack.com/start)
- [Temporal Documentation](https://docs.temporal.io/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Anthropic Claude API](https://docs.anthropic.com/)

## Contributing

1. Create a feature branch: `git checkout -b 001-feature-name`
2. Make your changes following the code style guide
3. Write/update tests
4. Run linting and formatting
5. Run tests and ensure coverage
6. Submit a PR with conventional commit message

## Questions?

- Check the [README.md](../README.md) for project overview
- Review [specs/](../specs/) for feature specifications
- Join the team chat for help
