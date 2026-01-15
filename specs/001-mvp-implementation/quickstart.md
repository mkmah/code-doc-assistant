# Quick Start Guide: Code Documentation Assistant MVP

**Feature**: 001-mvp-implementation
**Last Updated**: 2026-01-15

---

## Prerequisites

Ensure you have the following installed:

- **Docker** 20.10+ and Docker Compose 2.0+
- **Python** 3.11+ (for local development without Docker)
- **Bun** 1.0+ (for frontend development)
- **uv** 0.1+ (for Python package management)
- **git**

### Required API Keys

You'll need API keys for:
- **Anthropic Claude**: [Get API Key](https://console.anthropic.com/)
- **Jina AI** (primary): [Get API Key](https://jina.ai/) - OR
- **OpenAI** (fallback): [Get API Key](https://platform.openai.com/)

---

## 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd code-doc-assistant

# Checkout the feature branch
git checkout 001-mvp-implementation
```

---

## 2. Environment Configuration

Create a `.env` file in the project root:

```bash
# .env
# API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key_here
JINA_API_KEY=your_jina_api_key_here
OPENAI_API_KEY=your_openai_api_key_here  # Optional fallback

# Backend
BACKEND_PORT=8000
BACKEND_HOST=0.0.0.0
LOG_LEVEL=info

# Frontend
VITE_API_URL=http://localhost:8000
VITE_FRONTEND_PORT=3000

# ChromaDB
CHROMADB_HOST=chromadb
CHROMADB_PORT=8000
CHROMADB_PERSIST_DIRECTORY=/chroma/chroma

# Temporal
TEMPORAL_HOST=temporal
TEMPORAL_PORT=7233

# PostgreSQL (for Temporal)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=temporal
POSTGRES_PASSWORD=temporal
POSTGRES_DB=temporal

# Optional: Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001
```

---

## 3. Start Services (Docker Compose)

### Start All Services

```bash
# Start all services in detached mode
docker-compose -f infrastructure/docker/docker-compose.yml up -d

# View logs
docker-compose -f infrastructure/docker/docker-compose.yml logs -f
```

### Start Individual Services

```bash
# Start core services only (backend, frontend, chromadb, temporal)
docker-compose -f infrastructure/docker/docker-compose.yml up -d chromadb temporal postgres backend frontend

# Start monitoring (optional)
docker-compose -f infrastructure/docker/docker-compose.yml up -d prometheus grafana
```

### Stop Services

```bash
# Stop all services
docker-compose -f infrastructure/docker/docker-compose.yml down

# Stop and remove volumes (cleans all data)
docker-compose -f infrastructure/docker/docker-compose.yml down -v
```

---

## 4. Start Services (Local Development)

### Backend

```bash
cd backend

# Install dependencies with uv
uv sync

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies with bun
bun install

# Start development server
bun run dev
```

### Temporal Worker

```bash
cd temporal

# Install dependencies
uv sync

# Start worker
python worker.py
```

### ChromaDB (Local)

```bash
# Using Docker
docker run -p 8000:8000 \
  -v chromadb_data:/chroma/chroma \
  chromadb/chroma:latest
```

---

## 5. Start Services (Tilt)

For automated local development with hot reload:

```bash
# Install Tilt (macOS)
brew install tilt

# Start Tilt
tilt up

# Tilt will:
# - Build and start all services
# - Watch for file changes
# - Live update containers
# - Provide a web UI at http://localhost:10350
```

---

## 6. Verify Services

Once services are running, verify they're healthy:

```bash
# Backend health
curl http://localhost:8000/health

# Backend readiness (checks dependencies)
curl http://localhost:8000/health/ready

# Expected response:
# {"status":"healthy","version":"1.0.0"}
```

### Service URLs

| Service | URL | Notes |
|---------|-----|-------|
| Frontend | http://localhost:3000 | TanStack Start app |
| Backend API | http://localhost:8000 | FastAPI with `/docs` |
| API Documentation | http://localhost:8000/docs | Interactive Swagger UI |
| Temporal UI | http://localhost:8088 | Workflow history |
| ChromaDB | http://localhost:8001 | Vector store |
| Grafana | http://localhost:3001 | Monitoring (admin/admin) |
| Prometheus | http://localhost:9090 | Metrics |

---

## 7. First Usage

### Option A: Web UI

1. Open http://localhost:3000
2. Click "Upload Codebase"
3. Either:
   - Upload a ZIP file of your code
   - Or enter a GitHub repository URL
4. Wait for processing to complete (check status)
5. Start asking questions!

### Option B: API

```bash
# 1. Upload a codebase
curl -X POST http://localhost:8000/api/v1/codebase/upload \
  -F "name=my-project" \
  -F "repository_url=https://github.com/username/repo"

# Response: {"codebase_id":"...","status":"queued","workflow_id":"..."}

# 2. Check ingestion status
curl http://localhost:8000/api/v1/codebase/{codebase_id}/status

# 3. Query the codebase
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "codebase_id": "...",
    "query": "How does authentication work?"
  }'
```

---

## 8. Development Workflow

### Backend Development

```bash
cd backend

# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Format code
ruff format .
ruff check --fix .

# Run specific test file
pytest tests/unit/test_code_parser.py
```

### Frontend Development

```bash
cd frontend

# Run tests
bun test

# Type check
bun run type-check

# Format code
bun run format
bun run lint
```

### Temporal Workflow Development

```bash
cd temporal

# Run workflow tests
pytest tests/workflows/test_ingestion_workflow.py

# Develop workflow with Temporal dev server
temporal server start-dev --db-filename temporal.db
```

---

## 9. Troubleshooting

### Backend Won't Start

```bash
# Check if port 8000 is in use
lsof -i :8000

# Check logs
docker-compose logs backend

# Common issues:
# - ANTHROPIC_API_KEY not set
# - ChromaDB not reachable
# - PostgreSQL not ready
```

### Frontend Can't Connect to Backend

```bash
# Check VITE_API_URL in .env
# Should be: VITE_API_URL=http://localhost:8000

# Verify backend is running
curl http://localhost:8000/health
```

### Temporal Workflow Fails

```bash
# Check Temporal UI
open http://localhost:8088

# View workflow history
# Check for activity failures
# Verify worker is running
```

### ChromaDB Issues

```bash
# Reset ChromaDB data (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d chromadb
```

---

## 10. Useful Commands

### Docker

```bash
# View logs for a service
docker-compose logs -f backend

# Restart a service
docker-compose restart backend

# Execute command in container
docker-compose exec backend bash

# Check resource usage
docker stats
```

### Database / Storage

```bash
# Access PostgreSQL
docker-compose exec postgres psql -U temporal -d temporal

# Backup ChromaDB data
docker cp chromadb:/chroma/chroma ./chromadb_backup

# Restore ChromaDB data
docker cp ./chromadb_backup chromadb:/chroma/chroma
```

### Monitoring

```bash
# View metrics in Prometheus
open http://localhost:9090

# View dashboards in Grafana
open http://localhost:3001
# Default login: admin / admin
```

---

## 11. Production Deployment

### Kubernetes

```bash
# Set kubectl context
kubectl config use-context your-cluster

# Create namespace
kubectl apply -f infrastructure/k8s/base/namespace.yaml

# Deploy to staging
kubectl apply -k infrastructure/k8s/overlays/staging/

# Deploy to production
kubectl apply -k infrastructure/k8s/overlays/production/
```

### CI/CD

```bash
# Trigger CI/CD by pushing to main
git push origin main

# Or manually via GitHub Actions
# Navigate to: https://github.com/username/repo/actions
```

---

## 12. Next Steps

1. **Explore the API**: Visit http://localhost:8000/docs for interactive API documentation
2. **Upload a codebase**: Try uploading a small project (e.g., <100 files)
3. **Ask questions**: Query the codebase to test retrieval quality
4. **Monitor workflows**: Check Temporal UI to see ingestion progress
5. **Review metrics**: Open Grafana dashboards to view performance

---

## 13. Additional Resources

- **Full API Documentation**: `/contracts/openapi.yaml`
- **Data Model**: `/specs/001-mvp-implementation/data-model.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Development Guide**: `docs/DEVELOPMENT.md`
- **PRD**: `prd.md`

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review service logs: `docker-compose logs -f [service]`
3. Check Temporal workflow history in the UI
4. Open an issue in the repository

---

**Happy coding! 🚀**
