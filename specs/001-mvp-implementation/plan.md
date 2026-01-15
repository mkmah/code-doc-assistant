# Implementation Plan: MVP Implementation - Code Documentation Assistant

**Branch**: `001-mvp-implementation` | **Date**: 2026-01-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-mvp-implementation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a conversational AI assistant that ingests codebases (ZIP files or GitHub URLs) and answers natural language questions using RAG (Retrieval Augmented Generation). The system parses code with Tree-sitter, generates semantic embeddings, stores chunks in ChromaDB, and queries with Claude Sonnet 4 via LangGraph agents. Async processing managed by Temporal workflows with exponential backoff retry. Target: 100 concurrent users, <3s query response time, support for Python/JS/TS/Java/Go/Rust.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript 5+ (frontend)
**Primary Dependencies**: FastAPI, Temporal, LangGraph, ChromaDB, Anthropic Claude, TanStack Start, shadcn/ui
**Storage**: Local filesystem (codebase files), ChromaDB (vectors), in-memory session store (MVP)
**Testing**: pytest (backend), vitest (frontend), 80% coverage target
**Target Platform**: Linux/macOS containers, Docker Compose local, Kubernetes production
**Project Type**: web (backend + frontend architecture)
**Performance Goals**: <3s p95 query latency, 1000 files within 10min ingestion, 100 concurrent users
**Constraints**: 100MB max upload size, 30min retry timeout, 60s max backoff interval
**Scale/Scope**: 10,000 files, 100MB codebase, 100 concurrent users, 5+ languages

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution is not yet defined. Using default engineering best practices:

- [x] **Test-First Development**: TDD approach for all critical paths (upload, ingestion, query)
- [x] **Integration Testing**: Temporal workflow integration, vector store operations, LLM service calls
- [x] **Observability**: Structured logging, Prometheus metrics, OpenTelemetry tracing
- [x] **Error Handling**: Explicit error types, retry policies with exponential backoff
- [x] **Documentation**: API contracts (OpenAPI), data model docs, quickstart guide

**Gates Status**: PASSED - No violations detected. Follows established patterns from PRD.

## Project Structure

### Documentation (this feature)

```text
specs/001-mvp-implementation/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/                        # FastAPI services
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── chat.py        # Query endpoint (SSE streaming)
│   │       ├── codebase.py    # Upload, status, list, delete
│   │       └── health.py      # Health checks
│   ├── agents/
│   │   ├── graph.py           # LangGraph agent definition
│   │   ├── nodes.py           # Agent execution nodes
│   │   ├── state.py           # Agent state model
│   │   └── tools.py           # Agent tools
│   ├── core/
│   │   ├── config.py          # Settings, environment vars
│   │   ├── logging.py         # Structured logging
│   │   ├── security.py        # Secret detection
│   │   ├── metrics.py         # Prometheus metrics
│   │   ├── tracing.py         # OpenTelemetry
│   │   └── errors.py          # Error models
│   ├── models/
│   │   └── schemas.py         # Pydantic models
│   ├── services/
│   │   ├── codebase_store.py  # In-memory codebase registry
│   │   ├── codebase_processor.py  # Processing orchestration
│   │   ├── embedding_service.py   # Jina/OpenAI embeddings
│   │   ├── vector_store.py        # ChromaDB operations
│   │   ├── llm_service.py         # Claude API
│   │   ├── retrieval_service.py   # Hybrid search
│   │   └── session_store.py       # Session management
│   └── utils/
│       ├── code_parser.py     # Tree-sitter wrapper
│       ├── chunking.py        # Semantic chunking
│       └── secret_detection.py # Pattern-based secret scanning
└── tests/
    ├── unit/
    ├── integration/
    └── conftest.py

frontend/                       # TanStack Start application
├── app/
│   ├── routes/
│   │   ├── index.tsx          # Home page
│   │   ├── chat.tsx           # Chat interface
│   │   └── upload.tsx         # Codebase upload
│   ├── components/
│   │   ├── ChatInterface.tsx  # Chat UI with SSE
│   │   ├── CodeViewer.tsx     # Code display
│   │   └── UploadForm.tsx     # Upload form
│   └── lib/
│       └── api.ts             # API client
└── tests/

temporal/                       # Temporal workflows
├── workflows/
│   └── ingestion_workflow.py  # Codebase ingestion workflow
├── activities/
│   ├── parse_activities.py    # Validation, cloning, parsing
│   ├── embed_activities.py    # Embedding generation
│   └── index_activities.py    # Vector store indexing
└── worker.py                   # Temporal worker entrypoint

infra/
├── docker/
│   └── docker-compose.yml
├── k8s/
│   ├── backend/
│   ├── frontend/
│   └── temporal/
└── Tiltfile                   # Local dev orchestration
```

**Structure Decision**: Web application with separate backend (FastAPI) and frontend (TanStack Start). Backend services organized by layer (api/services/core). Temporal workflows in separate top-level directory for clear orchestration boundaries. Infrastructure directory for deployment manifests.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | No violations | N/A |

## Phase 0: Research & Technical Decisions

**Status**: COMPLETE

### Research Tasks

1. **Temporal Workflow Integration Patterns**
   - Decision: Use Temporal Python SDK with async/await, define activities with @activity.defn decorator
   - Rationale: Native Python async support, automatic retry with exponential backoff, built-in observability
   - Alternatives considered: Celery (less durable), custom asyncio loop (no observability)

2. **Tree-sitter Language Parser Setup**
   - Decision: Use tree-sitter-languages package with pre-compiled grammars, error-tolerant parsing mode
   - Rationale: Supports 10+ languages out of box, battle-tested, fast parsing
   - Alternatives considered: AST module (Python only), jedi (Python only)

3. **ChromaDB Collection Strategy**
   - Decision: Single collection with metadata filtering (codebase_id, language, chunk_type)
   - Rationale: Simpler management, allows cross-codebase queries if needed later
   - Alternatives considered: Per-codebase collections (too many collections), Pinecone (external dependency)

4. **LangGraph Agent Architecture**
   - Decision: State graph with nodes: query_analysis → retrieval → context_building → response_generation → validation
   - Rationale: Clear separation of concerns, easy to add new nodes, built-in state management
   - Alternatives considered: LangChain Agent (less control), custom workflow (more boilerplate)

5. **SSE Streaming Implementation**
   - Decision: FastAPI StreamingResponse with yield from generator, LangGraph state streamed via custom callback
   - Rationale: Native FastAPI support, client-compatible, low latency
   - Alternatives considered: WebSocket (overkill), polling (poor UX)

6. **Secret Detection Patterns**
   - Decision: Regex patterns for common secrets (AWS AKIA*, GCP keys, JWT tokens, basic auth, password=)
   - Rationale: Fast, simple, covers 90% of cases, no ML dependency
   - Alternatives considered: truffleHog (too heavy), ML classifier (overkill for MVP)

7. **File Storage Backend**
   - Decision: Local filesystem with configurable base path, files named by codebase_id
   - Rationale: Simple for MVP, no external dependency, easy cleanup
   - Alternatives considered: S3 (overkill), database BLOB (performance issues)

8. **Session Store Implementation**
   - Decision: In-memory dict with UUID keys, session_timeout_seconds config
   - Rationale: Simple for MVP, no external dependency, sufficient for 100 concurrent users
   - Alternatives considered: Redis (overkill for single-instance), database (slow)

### Output

See [research.md](./research.md) for detailed findings.

## Phase 1: Design Artifacts

**Status**: COMPLETE

### Data Model

See [data-model.md](./data-model.md) for entity definitions, relationships, and validation rules.

### API Contracts

See [contracts/](./contracts/) directory for OpenAPI specifications:
- `openapi.yaml` - Complete API specification
- `temporal.yaml` - Temporal workflow interfaces

### Quickstart Guide

See [quickstart.md](./quickstart.md) for local development setup.

## Implementation Phases

**Note**: This section provides overview. Detailed tasks are in `tasks.md` (generated by `/speckit.tasks`).

### Phase 1: Core Ingestion (P1)
- File upload endpoint with validation
- Local filesystem storage
- Temporal workflow setup
- Tree-sitter parsing
- Secret detection and redaction
- Semantic chunking
- Embedding generation
- ChromaDB indexing

### Phase 2: Query Interface (P1)
- LangGraph agent setup
- Retrieval service (hybrid search)
- LLM service (Claude integration)
- SSE streaming endpoint
- Session management
- Citation extraction

### Phase 3: Status & Management (P2)
- Status endpoint with progress tracking
- Codebase list endpoint (paginated)
- Delete endpoint with cleanup
- Error handling and retries

### Phase 4: Frontend (P2)
- Upload form component
- Chat interface with SSE
- Code viewer with syntax highlighting
- Status monitoring UI

### Phase 5: Production Readiness (P3)
- Health check endpoints
- Prometheus metrics
- OpenTelemetry tracing
- Docker/Kubernetes manifests
- CI/CD pipelines

## Next Steps

1. ✅ Complete Phase 0 research (see research.md)
2. ✅ Complete Phase 1: Design & Contracts
3. ⏳ Run `/speckit.tasks` to generate detailed task breakdown
4. ⏳ Run `/speckit.implement` to execute implementation

---

**Generated**: 2026-01-15 | **Command**: `/speckit.plan`
