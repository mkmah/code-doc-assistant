# code-doc-assistant Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-16

## Project Overview

**Code Documentation Assistant** - A conversational AI assistant that ingests codebases and answers natural language questions using RAG (Retrieval Augmented Generation).

## Active Technologies
- Python 3.11+ (backend), TypeScript 5+ (frontend) + FastAPI, Temporal, LangGraph, ChromaDB, Anthropic Claude, TanStack Start, shadcn/ui (001-mvp-implementation)
- Local filesystem (codebase files), ChromaDB (vectors), in-memory session store (MVP) (001-mvp-implementation)
- ChromaDB (vectors), in-memory (codebases/sessions MVP), local filesystem (uploaded files) (001-complete-mvp-implementation)
- TypeScript 5.9 + TanStack Start (@tanstack/start), React 19, shadcn/ui, TanStack Query (@tanstack/react-query), TanStack Router (@tanstack/react-router) (001-complete-frontend)
- Backend API (already implemented) - no frontend storage required for MVP (001-complete-frontend)

### Backend (Python 3.11+)
- **Framework**: FastAPI (async, auto OpenAPI docs)
- **Orchestration**: Temporal (workflow management, durable execution)
- **Agent Framework**: LangGraph (stateful agent execution)
- **Code Parsing**: Tree-sitter (multi-language AST parsing)
- **Vector Store**: ChromaDB (local) with Pinecone migration path
- **LLM**: Anthropic Claude Sonnet 4
- **Embeddings**: Jina AI jina-embeddings-v4 (primary), OpenAI text-embedding-3-small (fallback)
- **Package Manager**: uv
- **Testing**: pytest with 80% coverage target
- **Linting/Formatting**: ruff, black

### Frontend (TypeScript 5+)
- **Framework**: TanStack Start (React with SSR)
- **UI Library**: shadcn/ui + Tailwind CSS
- **State Management**: TanStack Query (React Query)
- **Package Manager**: bun
- **Testing**: vitest
- **Linting/Formatting**: eslint, prettier

### Infrastructure
- **Containerization**: Docker + Docker Compose (local), Kubernetes (production)
- **Local Dev**: Tilt (hot reload, orchestration)
- **Monitoring**: Prometheus + Grafana, OpenTelemetry
- **CI/CD**: GitHub Actions

## Project Structure

```text
backend/                    # FastAPI services
├── app/
│   ├── api/v1/            # REST endpoints (chat, upload, health, codebase)
│   ├── core/              # config, logging, security, metrics
│   ├── services/          # codebase_processor, embedding_service, vector_store,
│   │                     # llm_service, session_store, secret_scanner
│   ├── agents/            # LangGraph agent (graph, nodes, tools)
│   ├── models/            # Pydantic schemas (SecretType, Session, etc.)
│   └── utils/             # code_parser, chunking
└── tests/                 # unit, integration tests

frontend/                   # TanStack Start application
├── app/
│   ├── routes/            # index, chat, upload
│   ├── components/        # ChatInterface, CodeViewer, UploadForm, StatusTracker
│   └── lib/               # api client, utils
└── tests/

infra/
├── docker/                # docker-compose.yml
├── monitoring/            # prometheus, grafana configs, dashboards
```

## Commands

### Backend
```bash
cd backend
uv sync                    # Install dependencies
uv run uvicorn app.main:app --reload           # Run dev server
pytest                                  # Run tests
pytest --cov=app --cov-report=html      # Test with coverage
ruff check .                            # Lint
ruff format .                           # Format
```

### Frontend
```bash
cd frontend
bun install                             # Install dependencies
bun run dev                             # Run dev server
bun test                                # Run tests
bun run type-check                      # Type check
bun run lint                            # Lint
bun run format                          # Format
```

### Temporal Worker
```bash
cd backend
uv run -m app.worker                       # Start worker
pytest tests/workflows/                  # Test workflows
```

### Docker
```bash
docker compose -f infra/docker/docker-compose.yml up -d
docker compose logs -f backend          # View logs
docker compose down -v                  # Stop and clean
```

## Code Style

### Python (Backend)
- **Type hints**: Required for all functions (Python 3.11+ syntax)
- **Docstrings**: Google style for all public functions/classes
- **Imports**: Group imports (stdlib, third-party, local)
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Max line length**: 100 (ruff default)
- **Async**: Use async/await for I/O operations

### TypeScript (Frontend)
- **Strict mode**: Enabled in tsconfig.json
- **Components**: Functional components with hooks
- **Type safety**: No `any` types without justification
- **Naming**: camelCase for variables/functions, PascalCase for components
- **File organization**: Co-locate components, styles, tests

### Git
- **Conventional commits**: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`
- **Feature branches**: `001-feature-name`
- **PR approval required** before merging to main

## Key Design Decisions

1. **Semantic chunking**: Use Tree-sitter AST nodes (functions/classes) vs fixed-size chunks
2. **Hybrid search**: Combine dense (semantic) + sparse (keyword) retrieval for better relevance
3. **Session-based isolation**: No auth for MVP, independent sessions via session_id with 7-day retention
4. **Error-tolerant parsing**: Skip invalid code chunks but continue processing
5. **Exponential backoff retry**: 2s start, 2x multiplier, 60s cap, 30min total timeout
6. **Secret redaction**: Replace detected secrets with `[REDACTED_TYPE]` placeholders (8 secret types)
7. **Thread-safe sessions**: asyncio.Lock for session operations with automatic cleanup via Temporal cron workflow (daily at 2 AM)
8. **Rate limiting**: IP-based limiting (100 req/hour) + concurrent query limiter (10 max concurrent)
9. **Batch embeddings**: Process embeddings in batches of 100 with 100ms delays for rate limit compliance
10. **Multi-environment K8s**: Kustomize overlays with environment-specific resource patches

## API Endpoints

- `POST /api/v1/codebase/upload` - Upload ZIP or GitHub URL (rate limited: 100/hour)
- `GET /api/v1/codebase` - List all codebases (paginated)
- `GET /api/v1/codebase/{id}/status` - Check ingestion progress
- `DELETE /api/v1/codebase/{id}` - Delete codebase with complete cleanup
- `POST /api/v1/chat` - Query codebase (SSE stream, rate limited: 100/hour)
- `GET /health` - Health check
- `GET /health/ready` - Readiness probe
- `GET /metrics/metrics` - Prometheus metrics

## Performance Targets

- Query latency: <3s p95 (90% of queries)
- Ingestion: 1,000 files within 10 minutes
- Retrieval accuracy: >85% relevant chunks in top-5
- Citation accuracy: >95% correct file/line references
- Concurrent users: 100 (MVP)

## Common Patterns

### Backend Service Pattern
```python
from typing import Optional
from app.core.config import settings

class MyService:
    def __init__(self, client: Optional[HttpClient] = None):
        self.client = client or HttpClient()

    async def process(self, input: str) -> Result:
        """Process input and return result."""
        # Implementation
        pass
```

### FastAPI Endpoint Pattern
```python
from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import RequestSchema, ResponseSchema

router = APIRouter()

@router.post("/endpoint", response_model=ResponseSchema)
async def endpoint_handler(request: RequestSchema) -> ResponseSchema:
    """Handle request."""
    try:
        result = await service.process(request.data)
        return ResponseSchema(result=result)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Temporal Activity Pattern
```python
from datetime import timedelta
from temporalio import activity

@activity.defn
async def my_activity(input: ActivityInput) -> ActivityOutput:
    """Activity with retry policy."""
    # Implementation
    return ActivityOutput(result=...)
```

### Rate Limiting Pattern
```python
from fastapi import Request
from app.core.security import limiter

@router.post("/chat")
@limiter.limit("100/hour")
async def chat_endpoint(request: ChatRequest, http_request: Request):
    """Rate-limited endpoint using slowapi."""
    # Implementation
    pass
```

### Secret Scanner Pattern
```python
from app.services.secret_scanner import get_secret_scanner

scanner = get_secret_scanner()
detections = scanner.scan_code(content, file_path)
summary = scanner.get_summary(detections)
```

### Temporal Cron Workflow Pattern
```python
from datetime import timedelta
from temporalio import workflow, client

# Define workflow
@workflow.defn
class CronWorkflow:
    @workflow.run
    async def run(self, input: Input) -> Result:
        result = await workflow.execute_activity(
            my_activity,
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=workflow.RetryPolicy(...),
        )
        return result

# Start cron workflow from temporal worker (not FastAPI)
async def run_worker() -> None:
    client = await Client.connect(settings.temporal_url)

    async with Worker(client, task_queue="task-queue", workflows=[CronWorkflow]):
        # Start cron workflow once - persists across worker restarts
        try:
            await client.start_workflow(
                CronWorkflow.run,
                Input(),
                id="cron-workflow-id",
                task_queue="task-queue",
                cron_schedule="0 2 * * *",  # Daily at 2 AM
            )
        except Exception:
            # Workflow already exists (worker restart)
            pass

        await asyncio.Future()  # Keep worker running
```

## Testing Guidelines

### Unit Tests
- Mock external dependencies (LLM, embedding services)
- Test edge cases (empty inputs, error responses)
- Use pytest fixtures for common setup

### Integration Tests
- Test API endpoints with test database
- Verify Temporal workflow execution
- Test ChromaDB operations with real data

### Coverage Target
- 80% minimum for backend services
- 70% minimum for frontend components

## Recent Changes
- 001-complete-frontend: Added TypeScript 5.9 + TanStack Start (@tanstack/start), React 19, shadcn/ui, TanStack Query (@tanstack/react-query), TanStack Router (@tanstack/react-router)
- 001-complete-mvp-implementation (2026-01-16): **COMPLETED** - Full MVP implementation with all 5 user stories
  - **User Story 1 (P1)**: Upload and Process Codebase - ZIP/GitHub ingestion, secret scanning, semantic indexing
  - **User Story 2 (P1)**: Query with Context - Multi-turn conversations with session persistence (7-day retention)
  - **User Story 3 (P2)**: Delete Codebase - Complete cleanup including ChromaDB, sessions, files, workflows
  - **User Story 4 (P3)**: Multi-Environment Deployment - Kustomize overlays for dev/staging/production
  - **User Story 5 (P1)**: Production Readiness - Rate limiting (100 req/hour), Prometheus metrics, monitoring dashboards
  - **New Services**: SecretScanner (8 secret types), enhanced SessionStore (thread-safe, async cleanup), ConcurrentQueryLimiter
  - **Infrastructure**: Kubernetes manifests with environment-specific patches, monitoring dashboards (query, ingestion, system health)
  - **Tests**: 147/263 tests passing (56% coverage)

- 001-mvp-implementation: Initial MVP implementation with Python 3.11+ backend, TypeScript 5+ frontend

<!-- MANUAL ADDITIONS START -->
<!-- Add custom notes below this line -->
<!-- MANUAL ADDITIONS END -->
