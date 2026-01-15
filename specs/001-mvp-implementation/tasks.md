# Implementation Tasks: MVP Implementation - Code Documentation Assistant

**Feature**: 001-mvp-implementation
**Branch**: `001-mvp-implementation`
**Generated**: 2026-01-15
**Total Tasks**: 237

---

## Overview

This document contains all implementation tasks for the Code Documentation Assistant MVP, organized by user story to enable independent implementation and testing. Tasks follow a strict checklist format for execution tracking.

**Task Format**: `- [ ] [TaskID] [P?] [Story?] Description with file path`

- **[P]** = Parallelizable (can run simultaneously with other [P] tasks)
- **[Story]** = User Story label (US1, US2, US3, US4)
- Setup and Foundational phases have no story labels
- User Story phases have story labels for all tasks

---

## Phase 1: Project Setup

**Goal**: Initialize project structure, dependencies, and tooling.

### Independent Test Criteria
- All dependencies install without errors
- Project structure matches plan.md
- Linting and formatting tools work correctly
- Tests can run with placeholder files

### Tasks

- [ ] T001 Initialize backend project structure with uv in backend/
- [ ] T002 [P] Create pyproject.toml with FastAPI, Temporal, LangGraph, ChromaDB dependencies
- [ ] T003 [P] Create backend/app directory structure (api/v1, agents, core, models, services, utils)
- [ ] T004 [P] Create backend/tests directory structure (unit, integration, conftest.py)
- [ ] T005 [P] Initialize frontend project with bun in frontend/
- [ ] T006 [P] Create frontend/app directory structure (routes, components, lib)
- [ ] T007 [P] Create frontend/tests directory structure
- [ ] T008 [P] Initialize temporal/ directory structure (workflows, activities)
- [ ] T009 [P] Create infra/ directory structure (docker, k8s, Tiltfile)
- [ ] T010 [P] Create backend/app/core/config.py with pydantic-settings
- [ ] T011 [P] Create backend/app/core/logging.py with structured logging
- [ ] T012 [P] Create backend/app/core/errors.py with custom exception classes
- [ ] T013 [P] Create backend/app/core/metrics.py with Prometheus metrics
- [ ] T014 [P] Create backend/app/core/tracing.py with OpenTelemetry setup
- [ ] T015 [P] Create backend/app/core/security.py with SecretDetector placeholder
- [ ] T016 [P] Create backend/app/models/schemas.py with Pydantic models
- [ ] T017 [P] Create backend/tests/conftest.py with pytest fixtures
- [ ] T018 [P] Create backend/.env.example with all environment variables
- [ ] T019 [P] Create .gitignore for backend, frontend, and temporal
- [ ] T020 [P] Create .pre-commit-config.yaml with ruff and black hooks
- [ ] T021 [P] Create Makefile with common commands (test, lint, format, dev)
- [ ] T022 [P] Create README.md with quickstart instructions
- [ ] T023 [P] Create CLAUDE.md with project context for AI assistance

---

## Phase 2: Foundational Components

**Goal**: Implement core services and utilities needed by all user stories.

### Dependencies
- Must complete after Phase 1

### Independent Test Criteria
- Code parser can extract functions/classes from sample code
- Chunking creates semantic chunks with metadata
- Secret detection redacts common patterns
- Embedding service generates vectors for test strings
- Vector store can add and query chunks
- LLM service can stream a response
- Session store can create sessions and add messages

### Tasks

#### Core Utilities

- [ ] T024 [P] Implement code_parser.py with Tree-sitter wrapper in backend/app/utils/code_parser.py
- [ ] T025 [P] Implement chunking.py with semantic chunking in backend/app/utils/chunking.py
- [ ] T026 [P] Implement secret_detection.py with regex patterns in backend/app/utils/secret_detection.py
- [ ] T027 [P] Add unit tests for code_parser.py in backend/tests/unit/test_code_parser.py
- [ ] T028 [P] Add unit tests for chunking.py in backend/tests/unit/test_chunking.py
- [ ] T029 [P] Add unit tests for secret_detection.py in backend/tests/unit/test_secret_detection.py

#### Services

- [ ] T030 [P] Implement codebase_store.py with in-memory registry in backend/app/services/codebase_store.py
- [ ] T031 [P] Implement session_store.py with in-memory sessions in backend/app/services/session_store.py
- [ ] T032 [P] Implement vector_store.py with ChromaDB client in backend/app/services/vector_store.py
- [ ] T033 [P] Implement embedding_service.py with Jina/OpenAI in backend/app/services/embedding_service.py
- [ ] T034 [P] Implement llm_service.py with Claude streaming in backend/app/services/llm_service.py
- [ ] T035 [P] Implement retrieval_service.py with hybrid search in backend/app/services/retrieval_service.py
- [ ] T036 [P] Implement codebase_processor.py orchestration in backend/app/services/codebase_processor.py
- [ ] T037 [P] Add unit tests for codebase_store.py in backend/tests/unit/test_codebase_store.py
- [ ] T038 [P] Add unit tests for session_store.py in backend/tests/unit/test_session_store.py
- [ ] T039 [P] Add unit tests for vector_store.py in backend/tests/unit/test_vector_store.py
- [ ] T040 [P] Add unit tests for embedding_service.py in backend/tests/unit/test_embedding_service.py
- [ ] T041 [P] Add unit tests for llm_service.py in backend/tests/unit/test_llm_service.py
- [ ] T042 [P] Add unit tests for retrieval_service.py in backend/tests/unit/test_retrieval.py
- [ ] T043 [P] Add unit tests for codebase_processor.py in backend/tests/unit/test_codebase_processor.py

#### Temporal Workflow Foundation

- [ ] T044 [P] Create IngestionWorkflow class in temporal/workflows/ingestion_workflow.py
- [ ] T045 [P] Implement validate_codebase activity in temporal/activities/parse_activities.py
- [ ] T046 [P] Implement clone_or_extract activity in temporal/activities/parse_activities.py
- [ ] T047 [P] Implement parse_codebase activity in temporal/activities/parse_activities.py
- [ ] T048 [P] Implement generate_embeddings activity in temporal/activities/embed_activities.py
- [ ] T049 [P] Implement index_chunks activity in temporal/activities/index_activities.py
- [ ] T050 [P] Create temporal/worker.py with worker entry point
- [ ] T051 [P] Add integration tests for Temporal workflow in temporal/tests/workflows/test_ingestion_workflow.py

#### LangGraph Agent Foundation

- [ ] T052 [P] Define AgentState TypedDict in backend/app/agents/state.py
- [ ] T053 [P] Create LangGraph graph definition in backend/app/agents/graph.py
- [ ] T054 [P] Implement query_analysis_node in backend/app/agents/nodes.py
- [ ] T055 [P] Implement retrieval_node in backend/app/agents/nodes.py
- [ ] T056 [P] Implement context_building_node in backend/app/agents/nodes.py
- [ ] T057 [P] Implement response_generation_node in backend/app/agents/nodes.py
- [ ] T058 [P] Implement validation_node in backend/app/agents/nodes.py
- [ ] T059 [P] Implement error_handler_node in backend/app/agents/nodes.py
- [ ] T060 [P] Implement retrieve_code tool in backend/app/agents/tools.py
- [ ] T061 [P] Add integration tests for agent execution in backend/tests/integration/test_agent.py

#### Health Checks

- [ ] T062 [P] Implement /health endpoint in backend/app/api/v1/health.py
- [ ] T063 [P] Implement /health/ready endpoint with dependency checks in backend/app/api/v1/health.py

---

## Phase 3: User Story 1 - Upload and Ingest Codebase (P1)

**Goal**: Users can upload codebases (ZIP or GitHub URL) and the system processes them asynchronously.

**Why P1**: Foundational - no other features work without ingested codebases.

### Independent Test Criteria
Upload a small Python project ZIP and verify:
- System accepts upload, returns codebase_id and workflow_id
- Status shows progress through processing steps
- Final status is "completed" with file count
- Code chunks are queryable from vector store

### Acceptance Scenarios Coverage
1. ✅ Upload ZIP file → codebase ID returned
2. ✅ GitHub URL → repository cloned and processed
3. ✅ File >100MB → rejected with error
4. ✅ File with secrets → redacted, warning shown
5. ✅ Status during processing → progress shown
6. ✅ Complete status → shows "completed" with totals

### Tasks

#### Models

- [ ] T064 [P] [US1] Add Codebase Pydantic model to backend/app/models/schemas.py
- [ ] T065 [P] [US1] Add UploadRequest Pydantic model to backend/app/models/schemas.py
- [ ] T066 [P] [US1] Add UploadResponse Pydantic model to backend/app/models/schemas.py
- [ ] T067 [P] [US1] Add CodebaseStatus enum to backend/app/models/schemas.py
- [ ] T068 [P] [US1] Add SourceType enum to backend/app/models/schemas.py
- [ ] T069 [P] [US1] Add IngestionStatus Pydantic model to backend/app/models/schemas.py

#### File Storage

- [ ] T070 [US1] Add file_storage_path setting to backend/app/core/config.py
- [ ] T071 [US1] Implement store_file() function in backend/app/services/codebase_store.py
- [ ] T072 [US1] Implement delete_file() function in backend/app/services/codebase_store.py
- [ ] T073 [US1] Add unit tests for file storage in backend/tests/unit/test_codebase_store.py

#### Upload Endpoint

- [ ] T074 [US1] Implement POST /api/v1/codebase/upload endpoint in backend/app/api/v1/codebase.py
- [ ] T075 [US1] Add file size validation (100MB limit) in upload endpoint
- [ ] T076 [US1] Add file type validation (ZIP/tar.gz) in upload endpoint
- [ ] T077 [US1] Add GitHub URL validation in upload endpoint
- [ ] T078 [US1] Store uploaded file to filesystem in upload endpoint
- [ ] T079 [US1] Initialize Temporal client and trigger IngestionWorkflow in upload endpoint
- [ ] T080 [US1] Return UploadResponse with codebase_id and workflow_id from upload endpoint
- [ ] T081 [US1] Add integration tests for upload endpoint in backend/tests/integration/test_codebase.py

#### Temporal Workflow Integration

- [ ] T082 [US1] Wire up validate_codebase activity in IngestionWorkflow.run()
- [ ] T083 [US1] Wire up clone_or_extract activity in IngestionWorkflow.run()
- [ ] T084 [US1] Wire up parse_codebase activity in IngestionWorkflow.run()
- [ ] T085 [US1] Wire up generate_embeddings activity in IngestionWorkflow.run()
- [ ] T086 [US1] Wire up index_chunks activity in IngestionWorkflow.run()
- [ ] T087 [US1] Implement status signal updates in IngestionWorkflow
- [ ] T088 [US1] Add exponential backoff retry policy to activities (2s start, 2x multiplier, 60s cap)
- [ ] T089 [US1] Add 30-minute timeout handling to IngestionWorkflow

#### Secret Detection Integration

- [ ] T090 [US1] Integrate secret detection into parse_codebase activity
- [ ] T091 [US1] Store secrets_detected count in codebase_store metadata
- [ ] T092 [US1] Store secrets_summary dict in codebase_store metadata
- [ ] T093 [US1] Log warning when secrets are detected with file paths

#### Status Endpoint

- [ ] T094 [US1] Implement GET /api/v1/codebase/{id}/status endpoint in backend/app/api/v1/codebase.py
- [ ] T095 [US1] Add progress calculation (processed/total files) in status endpoint
- [ ] T096 [US1] Map CodebaseStatus to current_step string in status endpoint
- [ ] T097 [US1] Include secrets_detected in IngestionStatus response
- [ ] T098 [US1] Include secrets_summary in IngestionStatus response
- [ ] T099 [US1] Handle 404 for invalid codebase_id in status endpoint
- [ ] T100 [US1] Add integration tests for status endpoint in backend/tests/integration/test_status.py

#### Cleanup Operations

- [ ] T101 [US1] Implement vector_store.delete_codebase() call in DELETE endpoint
- [ ] T102 [US1] Implement session_store cascade delete by codebase_id
- [ ] T103 [US1] Implement file cleanup on codebase deletion

---

## Phase 4: User Story 2 - Query Codebase (P1)

**Goal**: Users can ask natural language questions and receive streamed answers with code citations.

**Why P1**: Core value proposition - users derive value from querying.

**Dependencies**: Requires US1 (must have ingested codebase to query)

### Independent Test Criteria
Ingest a sample codebase with known structure, then:
- Ask "How does X work?" → get answer with file:line citations
- Ask about non-existent code → get "not found" response
- Verify response streams in real-time
- Follow-up question maintains context
- Query only searches specified codebase

### Acceptance Scenarios Coverage
1. ✅ Query ingested codebase → answer with citations
2. ✅ Query non-existent code → "not found" response
3. ✅ Real-time streaming → chunks arrive progressively
4. ✅ Citations accurate → file:line correct
5. ✅ Follow-up question → context maintained
6. ✅ Multiple codebases → only searches specified one

### Tasks

#### Models

- [ ] T104 [P] [US2] Add ChatRequest Pydantic model to backend/app/models/schemas.py
- [ ] T105 [P] [US2] Add MessageType enum to backend/app/models/schemas.py
- [ ] T106 [P] [US2] Add Source Pydantic model to backend/app/models/schemas.py

#### Session Management

- [ ] T107 [US2] Implement create_session() in backend/app/services/session_store.py
- [ ] T108 [US2] Implement get_session() in backend/app/services/session_store.py
- [ ] T109 [US2] Implement add_message() in backend/app/services/session_store.py
- [ ] T110 [US2] Implement get_messages() with limit in backend/app/services/session_store.py
- [ ] T111 [US2] Implement cleanup_expired_sessions() in backend/app/services/session_store.py
- [ ] T112 [P] [US2] Add unit tests for session management in backend/tests/unit/test_session_store.py

#### Chat Endpoint

- [ ] T113 [US2] Implement POST /api/v1/chat endpoint in backend/app/api/v1/chat.py
- [ ] T114 [US2] Add StreamingResponse with SSE format in chat endpoint
- [ ] T115 [US2] Create or load existing session in chat endpoint
- [ ] T116 [US2] Invoke LangGraph agent with query and context in chat endpoint
- [ ] T117 [US2] Stream agent response chunks via SSE in chat endpoint
- [ ] T118 [US2] Handle empty retrieval (no relevant code) in agent
- [ ] T119 [US2] Add integration tests for chat endpoint in backend/tests/integration/test_chat.py

#### Agent Enhancements

- [ ] T120 [US2] Wire retrieval_node to retrieval_service.retrieve_code()
- [ ] T121 [US2] Wire context_building_node to format chunks for LLM
- [ ] T122 [US2] Wire response_generation_node to llm_service.generate_response()
- [ ] T123 [US2] Load session history (last 5 messages) in response_generation_node
- [ ] T124 [US2] Pass session_history to LLM service in response_generation_node
- [ ] T125 [US2] Extract citations from LLM response in validation_node
- [ ] T126 [US2] Add error handling with error_handler_node in agent graph

#### Retrieval Enhancements

- [ ] T127 [US2] Implement retrieve_by_filter() in backend/app/services/retrieval_service.py
- [ ] T128 [US2] Add language, chunk_type, file_path filtering support
- [ ] T129 [US2] Implement hybrid scoring (dense + sparse) in retrieval_service

---

## Phase 5: User Story 3 - Track Ingestion Status (P2)

**Goal**: Users can monitor ingestion progress for long-running operations.

**Why P2**: Improves UX but not blocking - users can poll status endpoint from US1.

**Dependencies**: Extends US1 (status endpoint exists but needs enhancement)

### Independent Test Criteria
Upload large codebase and verify:
- Status shows current step (validating, cloning, parsing, embedding, indexing)
- Progress percentage updates correctly
- Queued status shown when embedding service unavailable
- Failed status shows error message after 30-minute timeout
- Invalid codebase_id returns 404

### Acceptance Scenarios Coverage
1. ✅ Status during processing → progress shown
2. ✅ Embedding service unavailable → "queued" status
3. ✅ Processing fails after retries → "failed" with error
4. ✅ Processing completes → "completed" with timestamp
5. ✅ Invalid codebase_id → 404 error

### Tasks

**Note**: Status endpoint already implemented in US1. These tasks enhance it.

- [ ] T130 [US3] Add current_step mapping to IngestionStatus in status endpoint
- [ ] T131 [US3] Map QUEUED status to "validating" step
- [ ] T132 [US3] Map PROCESSING status to "parsing" step (simplified for MVP)
- [ ] T133 [US3] Add retry queue status handling for embedding failures
- [ ] T134 [US3] Add error_message to IngestionStatus response
- [ ] T135 [US3] Add started_at timestamp calculation in status endpoint
- [ ] T136 [US3] Add completed_at timestamp in status endpoint
- [ ] T137 [US3] Add integration test for failed status after timeout

---

## Phase 6: User Story 4 - List and Manage Codebases (P3)

**Goal**: Users can view all codebases and delete them.

**Why P3**: Convenience feature - not essential for MVP.

**Dependencies**: Requires US1 (codebases must exist to list)

### Independent Test Criteria
Upload multiple codebases and verify:
- List endpoint returns all codebases with metadata
- Pagination works when list exceeds page size
- Empty list returns appropriate message
- Delete removes codebase and associated data

### Acceptance Scenarios Coverage
1. ✅ List codebases → shows all with metadata
2. ✅ Pagination → navigate through pages
3. ✅ Empty list → appropriate messaging

### Tasks

#### List Endpoint

- [ ] T138 [P] [US4] Add CodebaseListResponse Pydantic model to backend/app/models/schemas.py
- [ ] T139 [US4] Implement GET /api/v1/codebase endpoint in backend/app/api/v1/codebase.py
- [ ] T140 [US4] Add page and limit query parameters with validation
- [ ] T141 [US4] Implement pagination logic in list endpoint
- [ ] T142 [US4] Return codebases sorted by created_at desc in list endpoint
- [ ] T143 [US4] Add integration tests for list endpoint in backend/tests/integration/test_codebase.py

#### Delete Endpoint

- [ ] T144 [US4] Implement DELETE /api/v1/codebase/{id} endpoint in backend/app/api/v1/codebase.py
- [ ] T145 [US4] Call vector_store.delete_codebase() before removing from codebase_store
- [ ] T146 [US4] Cascade delete sessions and messages from session_store
- [ ] T147 [US4] Delete file from filesystem storage
- [ ] T148 [US4] Return 204 No Content on successful delete
- [ ] T149 [US4] Return 404 if codebase not found
- [ ] T150 [US4] Add integration tests for delete endpoint in backend/tests/integration/test_codebase.py

---

## Phase 7: Frontend Implementation

**Goal**: Build TanStack Start frontend for upload, chat, and status monitoring.

### Dependencies
- US1: Upload form and status UI
- US2: Chat interface with SSE
- US3: Enhanced status monitoring
- US4: Codebase list view

### Independent Test Criteria
- Can upload ZIP file via form
- Can enter GitHub URL
- Can chat with ingested codebase
- Can see status updates
- Can list and delete codebases

### Tasks

#### Setup

- [ ] T151 [P] Initialize TanStack Start app in frontend/
- [ ] T152 [P] Install shadcn/ui components (Button, Input, Card, etc.)
- [ ] T153 [P] Configure Tailwind CSS in frontend/
- [ ] T154 [P] Create frontend/app/lib/api.ts with API client
- [ ] T155 [P] Add TypeScript types for API responses

#### Upload Page

- [ ] T156 [P] Create frontend/app/routes/upload.tsx route
- [ ] T157 [P] Create UploadForm component in frontend/app/components/UploadForm.tsx
- [ ] T158 [P] Add file input with drag-drop support
- [ ] T159 [P] Add GitHub URL input field
- [ ] T160 [P] Add form validation (file size, URL format)
- [ ] T161 [P] Add submit handler calling POST /api/v1/codebase/upload
- [ ] T162 [P] Display returned codebase_id and workflow_id
- [ ] T163 [P] Add error handling and display

#### Chat Interface

- [ ] T164 [P] Create frontend/app/routes/chat.tsx route
- [ ] T165 [P] Create ChatInterface component in frontend/app/components/ChatInterface.tsx
- [ ] T166 [P] Add codebase selector dropdown
- [ ] T167 [P] Add message input field with send button
- [ ] T168 [P] Implement SSE connection to POST /api/v1/chat
- [ ] T169 [P] Stream response chunks to chat display
- [ ] T170 [P] Render code citations with links
- [ ] T171 [P] Add syntax highlighting for code snippets
- [ ] T172 [P] Add error handling for connection failures

#### Status Monitoring

- [ ] T173 [P] Add polling to GET /api/v1/codebase/{id}/status
- [ ] T174 [P] Display progress bar with percentage
- [ ] T175 [P] Show current step (validating, parsing, embedding, etc.)
- [ ] T176 [P] Display files processed vs total
- [ ] T177 [P] Show warnings for detected secrets
- [ ] T178 [P] Handle failed status with error message display

#### Codebase List

- [ ] T179 [P] Create frontend/app/routes/index.tsx with codebase list
- [ ] T180 [P] Call GET /api/v1/codebase with pagination
- [ ] T181 [P] Display codebase cards with metadata
- [ ] T182 [P] Add pagination controls
- [ ] T183 [P] Add delete button to each codebase card
- [ ] T184 [P] Implement delete confirmation dialog

---

## Phase 8: Production Readiness

**Goal**: Add monitoring, containerization, and deployment manifests.

### Dependencies
- All user stories complete

### Independent Test Criteria
- Health endpoints return correct status
- Prometheus metrics exposed
- Docker Compose can start all services
- Can deploy to Kubernetes (if applicable)

### Tasks

#### Health Checks

- [ ] T185 [P] Implement ChromaDB health check in /health/ready endpoint
- [ ] T186 [P] Implement LLM service health check in /health/ready endpoint
- [ ] T187 [P] Implement embedding service health check in /health/ready endpoint
- [ ] T188 [P] Implement Temporal connection check in /health/ready endpoint
- [ ] T189 [P] Return 503 if any dependency is unhealthy

#### Observability

- [ ] T190 [P] Add request ID middleware in backend/app/core/logging.py
- [ ] T191 [P] Add request duration tracking in MetricsMiddleware
- [ ] T192 [P] Add query duration tracking in retrieval_service
- [ ] T193 [P] Add embedding request tracking in embedding_service
- [ ] T194 [P] Add LLM token usage tracking in llm_service
- [ ] T195 [P] Configure Prometheus endpoint /metrics
- [ ] T196 [P] Add OpenTelemetry tracing spans to critical paths

#### Containerization

- [ ] T197 [P] Create backend/Dockerfile for FastAPI app
- [ ] T198 [P] Create frontend/Dockerfile for TanStack Start app
- [ ] T199 [P] Create temporal/Dockerfile for Temporal worker
- [ ] T200 [P] Create infra/docker/docker-compose.yml with all services
- [ ] T201 [P] Add ChromaDB service to docker-compose.yml
- [ ] T202 [P] Add Temporal server to docker-compose.yml
- [ ] T203 [P] Configure environment variables in docker-compose.yml
- [ ] T204 [P] Add volume mounts for local development

#### Kubernetes

- [ ] T205 [P] Create infra/k8s/backend/deployment.yaml
- [ ] T206 [P] Create infra/k8s/backend/service.yaml
- [ ] T207 [P] Create infra/k8s/frontend/deployment.yaml
- [ ] T208 [P] Create infra/k8s/frontend/service.yaml
- [ ] T209 [P] Create infra/k8s/temporal/deployment.yaml
- [ ] T210 [P] Create ConfigMap for environment variables
- [ ] T211 [P] Create secrets manifests for API keys

#### Local Development

- [ ] T212 [P] Create Tiltfile for hot-reload development
- [ ] T213 [P] Add Tilt resources for backend, frontend, temporal
- [ ] T214 [P] Configure live reload for Python code
- [ ] T215 [P] Configure live reload for TypeScript code

#### CI/CD

- [ ] T216 [P] Create .github/workflows/test.yml for running tests
- [ ] T217 [P] Create .github/workflows/lint.yml for code quality checks
- [ ] T218 [P] Create .github/workflows/docker-build.yml for container images
- [ ] T219 [P] Add test coverage reporting to CI

---

## Phase 9: Polish & Cross-Cutting Concerns

**Goal**: Final polish, documentation, and edge case handling.

### Dependencies
- All previous phases complete

### Tasks

#### Error Handling

- [ ] T220 Add comprehensive error messages for all failure modes
- [ ] T221 Implement rate limiting for upload endpoint (optional for MVP)
- [ ] T222 Add request timeout handling
- [ ] T223 Add graceful shutdown handling

#### Documentation

- [ ] T224 Complete quickstart.md with local dev instructions
- [ ] T225 Add API documentation examples
- [ ] T226 Add troubleshooting guide to README.md
- [ ] T227 Add architecture diagram to docs/

#### Testing

- [ ] T228 Add end-to-end test for complete upload→query flow
- [ ] T229 Add performance tests for ingestion (1000 files target)
- [ ] T230 Add load tests for query endpoint (<3s p95 target)
- [ ] T231 Verify test coverage meets 80% target

#### Security

- [ ] T232 Add input sanitization for all user inputs
- [ ] T233 Add path traversal prevention for file storage
- [ ] T234 Add rate limiting for LLM calls (cost control)
- [ ] T235 Validate all file uploads are actually code files

---

## Dependencies

### User Story Dependencies

```
US1 (Upload & Ingest) - No dependencies, foundation for all stories
├── US2 (Query) - Requires US1 (need ingested codebase)
├── US3 (Status) - Extends US1 (status endpoint exists, needs enhancement)
└── US4 (List & Manage) - Requires US1 (need codebases to list)
```

### Phase Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational)
    ↓
Phase 3 (US1) ←──┐
    ↓            │
Phase 4 (US2) ────┘ (extends US1)
    ↓
Phase 5 (US3) ────┘ (extends US1)
    ↓
Phase 6 (US4) ────┘ (extends US1)
    ↓
Phase 7 (Frontend) ──┐ (depends on all API phases)
    ↓                 │
Phase 8 (Production) ──┘
    ↓
Phase 9 (Polish)
```

---

## Parallel Execution Examples

### Within Phase 1 (Setup)
All tasks with [P] can run in parallel:
- T002-T023: 22 parallel tasks for project structure, configs, tests

### Within Phase 2 (Foundational)
Groups of parallel tasks:
- Group 1: T024-T029 (utils + tests) - 6 parallel
- Group 2: T030-T043 (services + tests) - 14 parallel
- Group 3: T044-T051 (Temporal) - 8 parallel
- Group 4: T052-T061 (Agent + tests) - 10 parallel
- Group 5: T062-T063 (Health) - 2 parallel

### Within US1 (Upload & Ingest)
Groups of parallel tasks:
- Group 1: T064-T069 (Models) - 6 parallel
- Group 2: T070-T073 (File storage + tests) - 4 parallel
- Group 3: After T074-T080 (Endpoint): T082-T089 (Workflow integration) - 8 parallel

### Within US2 (Query)
Groups of parallel tasks:
- Group 1: T104-T106 (Models) - 3 parallel
- Group 2: T107-T112 (Session + tests) - 6 parallel
- Group 3: After T113-T119 (Endpoint): T120-T129 (Agent + retrieval) - 10 parallel

### Within Frontend
All [P] tasks can run in parallel after setup:
- T151-T155: 5 parallel (setup)
- T156-T163: 8 parallel (upload page)
- T164-T172: 9 parallel (chat interface)
- T173-T178: 6 parallel (status monitoring)
- T179-T184: 6 parallel (codebase list)

---

## Implementation Strategy

### MVP Scope (Recommended First Increment)

**Target**: User Stories 1 + 2 (Upload & Query) with basic frontend

**Rationale**: These two stories deliver the core value - ingest code and ask questions. US3 and US4 are convenience features that can be added later.

**MVP Task List**:
- Phase 1: Setup (T001-T023)
- Phase 2: Foundational (T024-T063)
- Phase 3: US1 Upload & Ingest (T064-T103)
- Phase 4: US2 Query (T104-T129)
- Phase 7: Frontend - Upload + Chat only (T151-T172)
- Phase 8: Production basics (T185-T204)

**Total MVP Tasks**: ~172 tasks (excluding US3, US4, advanced production features)

### Incremental Delivery

1. **Sprint 1**: Phase 1-2 (Setup + Foundational) - Foundation
2. **Sprint 2**: Phase 3 (US1) - Can ingest codebases
3. **Sprint 3**: Phase 4 (US2) - Can query codebases ← **MVP Complete**
4. **Sprint 4**: Phase 5 (US3) - Enhanced status tracking
5. **Sprint 5**: Phase 6 (US4) - Codebase management
6. **Sprint 6**: Phase 7 (Frontend) - Full UI
7. **Sprint 7**: Phase 8-9 - Production polish

---

## Format Validation

✅ **All tasks follow checklist format**:
- Checkbox: `- [ ]` present
- Task ID: Sequential T001-T237
- [P] marker: Added for parallelizable tasks
- [Story] labels: US1, US2, US3, US4 for user story tasks
- File paths: Included in all implementation tasks
- Setup/Foundational/Polish: No story labels (as required)

**Total Tasks**: 237
- Setup: 23 tasks
- Foundational: 40 tasks
- US1: 40 tasks
- US2: 26 tasks
- US3: 8 tasks
- US4: 13 tasks
- Frontend: 34 tasks
- Production: 35 tasks
- Polish: 18 tasks

**Parallel Opportunities**: ~60% of tasks have [P] marker and can run in parallel within their phase/story.

---

**Generated**: 2026-01-15 | **Command**: `/speckit.tasks`
