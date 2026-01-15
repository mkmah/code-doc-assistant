# Feature Specification: MVP Implementation - Code Documentation Assistant

**Feature Branch**: `001-mvp-implementation`
**Created**: 2025-01-14
**Status**: Draft
**Input**: User description: "help me building this project mentioned in @prd.md strictly follow tool usage (like uv for python and backend, bun for frontend)"

## Clarifications

### Session 2025-01-14

- Q: User Authentication for MVP → A: No authentication for MVP (self-hosted, single user instance)

### Session 2026-01-15

- Q: When system detects potential secrets (API keys, passwords, tokens) in uploaded code, should it reject upload or strip secrets? → A: Strip secrets from processed chunks before indexing, store redacted versions, and warn user which files contained secrets
- Q: Should MVP support concurrent multi-user access or single sequential user? → A: Support 100 concurrent users with full multi-user architecture from MVP (requires session management)
- Q: What is the recovery SLO for failed codebase ingestion? → A: 30 minutes maximum with exponential backoff before marking as failed
- Q: When embedding service (Jina AI/OpenAI) is unavailable or rate-limited, what should the system do? → A: Queue the ingestion, return "queued" status, retry embedding generation when service available (up to 30 min retry window)
- Q: What secret detection patterns should MVP support? → A: Common patterns: API keys (AWS, GCP, Azure, GitHub, Slack), JWT tokens, basic auth strings, password= assignments
- Q: What format should be used for redacting detected secrets in processed code chunks? → A: Replace with typed placeholder `[REDACTED_SECRET_TYPE]` (e.g., `[REDACTED_API_KEY]`) and log detection count per file for audit trail
- Q: What are the specific exponential backoff parameters for retrying failed ingestion? → A: Start at 2s, double each retry (2s, 4s, 8s, 16s...), cap at 60s max interval, continue until 30min total elapsed time
- Q: How should the system handle unsupported or binary file formats during codebase ingestion? → A: Skip unsupported files with warning, log them, continue processing supported files (best effort, complete logging of skipped files in status)
- Q: What session isolation guarantees are required for concurrent multi-user access? → A: Session-based isolation via session_id parameter, each session maintains independent conversation context and query history with no cross-session leakage
- Q: How should the system handle malformed or syntactically invalid code during parsing? → A: Parse with Tree-sitter in error-tolerant mode, skip only invalid chunks/AST nodes with warning, continue processing valid parts (best effort, complete logging of skipped chunks)

### Session 2026-01-15 (Backend TODO Items)

- Q: What file storage mechanism should be used for uploaded codebase files? → A: Use local filesystem storage for MVP (configured path from settings), store files with codebase_id as identifier, implement cleanup on codebase deletion
- Q: How should the backend trigger Temporal workflows from FastAPI endpoints? → A: Initialize Temporal client in API endpoint, use client.start_workflow() to trigger IngestionWorkflow with proper input parameters, handle workflow_id for tracking
- Q: How should secret detection results be tracked and reported in the status API? → A: Store secret detection results in codebase_store metadata, include secrets_detected count and secrets_summary in IngestionStatus response, expose this information via /status endpoint
- Q: How should vector store cleanup be implemented when deleting a codebase? → A: Call vector_store.delete_codebase(codebase_id) before removing from codebase_store, ensure all chunks are removed from ChromaDB collection
- Q: How should session cleanup be handled when deleting a codebase? → A: Delete all query sessions associated with the codebase_id from session_store, cascade delete all messages in those sessions
- Q: How should session history be loaded and passed to the LLM service? → A: Query session_store.get_messages(session_id, limit=5) in response_generation_node, format messages for LLM API, pass as session_history parameter to maintain conversation context

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload and Ingest Codebase (Priority: P1)

A developer wants to understand an unfamiliar codebase. They navigate to the application, provide a codebase either by uploading a ZIP file or specifying a GitHub repository URL, and the system processes the code by parsing it, breaking it into meaningful chunks, generating embeddings, and storing it for retrieval.

**Why this priority**: This is the foundational functionality without which no other features can work. Users must be able to ingest codebases before they can query them.

**Independent Test**: Can be fully tested by uploading a sample codebase (e.g., a small Python project) and verifying that the system completes ingestion, returns a codebase ID, and stores the processed code chunks successfully.

**Acceptance Scenarios**:

1. **Given** no codebases exist in the system, **When** a user uploads a valid ZIP file containing Python code, **Then** the system accepts the upload, initiates processing, and returns a codebase ID and workflow ID
2. **Given** a user provides a valid GitHub repository URL, **When** they submit the URL, **Then** the system clones the repository, parses the code, and begins indexing
3. **Given** a user uploads a file larger than 100MB, **When** the system validates the file size, **Then** the upload is rejected with a clear error message explaining the size limit
4. **Given** a user uploads a file containing potential secrets (e.g., API keys in code), **When** the system scans the content, **Then** the system strips secrets from processed chunks, stores redacted versions, and warns the user which files contained detected secrets
5. **Given** a codebase is being processed, **When** the user checks the status, **Then** they see progress information (files processed, total files, current step)
6. **Given** processing completes successfully, **When** the user checks the status, **Then** the status shows "completed" with total files processed and no errors

---

### User Story 2 - Query Codebase (Priority: P1)

A developer has an ingested codebase and wants to understand how a specific feature works. They ask a natural language question (e.g., "How does authentication work?"), and the system retrieves relevant code snippets, generates an answer citing specific files and line numbers, and streams the response in real-time.

**Why this priority**: This is the core value proposition of the system. Without query functionality, users cannot derive value from ingested codebases.

**Independent Test**: Can be fully tested by ingesting a sample codebase with known structure, asking specific questions about it, and verifying that the system returns accurate answers with correct citations.

**Acceptance Scenarios**:

1. **Given** a codebase has been successfully ingested, **When** a user asks "How does authentication work?", **Then** the system retrieves relevant code chunks and returns a natural language answer with file paths and line numbers
2. **Given** a user asks a question about code that doesn't exist, **When** the system searches, **Then** the response states that the requested information was not found in the provided code
3. **Given** a user asks a question, **When** the system generates the answer, **Then** the response is streamed in real-time (not waiting for complete generation before showing content)
4. **Given** the answer includes code references, **When** the user views the response, **Then** all cited files and line numbers are accurate and can be verified in the codebase
5. **Given** a user submits a follow-up question in the same session, **When** the system processes it, **Then** it maintains context from previous questions if relevant
6. **Given** multiple codebases exist, **When** a user asks a question, **Then** the system only searches the specified codebase (not all codebases)

---

### User Story 3 - Track Ingestion Status (Priority: P2)

A developer uploads a large codebase that takes several minutes to process. They want to monitor progress to know when processing completes or if any errors occur.

**Why this priority**: Provides visibility and better UX, especially for larger codebases that take time to process. Users need feedback on long-running operations.

**Independent Test**: Can be fully tested by uploading a codebase and checking the status endpoint at regular intervals, verifying that progress updates correctly and transitions to completion or error states.

**Acceptance Scenarios**:

1. **Given** a codebase upload is in progress, **When** the user queries the status endpoint, **Then** they see current status (queued/processing/failed/completed), percentage complete, files processed, and total files
2. **Given** the embedding service is unavailable when upload is submitted, **When** the user queries the status endpoint, **Then** they see status "queued" and the system automatically retries when service becomes available
3. **Given** processing fails due to an error after exhausting retries (up to 30 minutes with exponential backoff), **When** the user checks status, **Then** the status shows "failed" with an error message explaining what went wrong
4. **Given** processing completes successfully, **When** the user queries status, **Then** the status shows "completed" with total files processed and timestamp of completion
5. **Given** a user queries status for an invalid codebase ID, **When** the request is made, **Then** the system returns a 404 error indicating the codebase was not found

---

### User Story 4 - List and Manage Codebases (Priority: P3)

A developer has uploaded multiple codebases over time and wants to see a list of all uploaded codebases, their sizes, languages, and creation dates to select one for querying.

**Why this priority**: Convenience feature that improves UX for users working with multiple codebases. Not essential for MVP but useful for regular users.

**Independent Test**: Can be fully tested by uploading multiple codebases and verifying that the list endpoint returns all codebases with correct metadata.

**Acceptance Scenarios**:

1. **Given** multiple codebases have been uploaded, **When** the user requests a list of codebases, **Then** they see all codebases with name, language, file count, and creation date
2. **Given** the list exceeds the page size, **When** the user requests the list, **Then** they see pagination controls and can navigate through all codebases
3. **Given** no codebases exist, **When** the user requests the list, **Then** they see an empty list with appropriate messaging

---

### Edge Cases

- How does the system redact detected secrets? → Replace with typed placeholders `[REDACTED_SECRET_TYPE]` (e.g., `[REDACTED_API_KEY]`, `[REDACTED_JWT_TOKEN]`) and log detection count per file; preserves code structure and enables audit verification
- What happens when a user uploads a codebase with unsupported file formats (e.g., binary files, images)? → Skip unsupported files with warning in status response, log skipped file paths, continue processing supported files
- How does the system handle a codebase with circular dependencies or extremely complex imports?
- What happens when the embedding service (Jina AI or OpenAI) is temporarily unavailable or rate-limited? → Queue ingestion, return "queued" status, retry when service available (up to 30 min retry window)
- How does the system handle a query that returns no relevant code chunks (retrieval failure)?
- What happens when ChromaDB storage becomes full or corrupted?
- How does the system handle concurrent uploads from multiple users? → Support up to 100 concurrent users with session-based isolation via session_id; each session maintains independent conversation context and query history with no cross-session leakage
- What is the recovery timeout for failed ingestion (retry duration, backoff strategy)? → 30 minutes maximum, exponential backoff starting at 2s, doubling each retry (2s, 4s, 8s, 16s...), capped at 60s max interval
- What happens when a user asks a question in a language different from the codebase's primary language?
- How does the system handle malformed or syntactically invalid code during parsing? → Parse with Tree-sitter in error-tolerant mode, skip only invalid chunks/AST nodes with warning, continue processing valid parts; log skipped chunks in status response
- What happens when the LLM service (Claude) is unavailable or exceeds token limits?
- How does the system handle a network timeout during codebase cloning from GitHub?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept codebase uploads via archive file (ZIP or tar.gz) with maximum size of 100MB
- **FR-002**: System MUST accept code repository URLs for automatic download and processing
- **FR-003**: System MUST validate uploaded files for size limits and supported file extensions
- **FR-004**: System MUST scan uploaded code for potential secrets using common patterns: API keys (AWS AKIA*, GCP, Azure, GitHub, Slack), JWT tokens, basic auth strings, password= assignments; strip them from processed chunks by replacing with typed placeholders `[REDACTED_SECRET_TYPE]` (e.g., `[REDACTED_API_KEY]`), store redacted versions in vector store, log detection count per file for audit trail, and warn user which files contained detected secrets
- **FR-005**: System MUST parse code for supported programming languages (Python, JavaScript, TypeScript, Java, Go, Rust, etc.)
- **FR-006**: System MUST extract functions, classes, methods, imports, and other code constructs during parsing
- **FR-007**: System MUST create semantically meaningful code chunks at function/method level where possible
- **FR-008**: System MUST enrich each code chunk with metadata (file path, line numbers, language, dependencies, docstrings)
- **FR-009**: System MUST generate vector embeddings for each code chunk using a code-optimized embedding model; if embedding service is unavailable or rate-limited, queue the ingestion, return "queued" status, and retry when service available (up to 30 min retry window)
- **FR-010**: System MUST store code chunks and embeddings in a vector database for retrieval
- **FR-011**: System MUST process uploaded codebases asynchronously with progress tracking and retry failures using exponential backoff starting at 2s, doubling each retry (2s, 4s, 8s, 16s...), capped at 60s max interval, for up to 30 minutes total elapsed time before marking as failed
- **FR-012**: System MUST provide a status endpoint to query ingestion progress
- **FR-013**: System MUST accept natural language queries from users via chat interface
- **FR-014**: System MUST perform semantic search on code chunks using vector embeddings
- **FR-015**: System MUST re-rank retrieved results using hybrid search (semantic similarity combined with keyword matching)
- **FR-016**: System MUST generate natural language answers using a large language model based on retrieved code
- **FR-017**: System MUST cite specific files and line numbers in generated answers
- **FR-018**: System MUST stream responses to the user in real-time
- **FR-019**: System MUST maintain conversation context within a session for follow-up questions
- **FR-020**: System MUST handle cases where no relevant code is found by stating "I don't see this in the provided code"
- **FR-021**: System MUST limit responses to information contained in the uploaded codebase (no hallucinations)
- **FR-022**: System MUST support multiple programming languages in the same codebase
- **FR-023**: System MUST handle codebases with up to 10,000 files and 100MB total size
- **FR-024**: System MUST allow multiple users to list all uploaded codebases with metadata (no authentication required for MVP, but session-based via session_id)
- **FR-024a**: System MUST support up to 100 concurrent users with independent query sessions via session_id parameter; each session maintains isolated conversation context and query history with no cross-session leakage (no authentication required for MVP)
- **FR-025**: System MUST provide pagination for codebase lists
- **FR-026**: System MUST use appropriate dependency managers for backend and frontend as specified in PRD
- **FR-027**: System MUST provide health check endpoints for monitoring service status
- **FR-028**: System MUST store uploaded codebase files to local filesystem storage configured via settings, using codebase_id as file identifier
- **FR-029**: System MUST trigger Temporal IngestionWorkflow from upload endpoint using Temporal client with proper workflow input parameters
- **FR-030**: System MUST track and report secret detection results (secrets_detected count and secrets_summary) in codebase status endpoint
- **FR-031**: System MUST clean up vector store data when deleting a codebase by calling vector_store.delete_codebase() before removing from codebase_store
- **FR-032**: System MUST clean up all associated query sessions and messages when deleting a codebase via cascade delete from session_store
- **FR-033**: System MUST load and pass session history (last 5 messages) to LLM service in response generation node for conversation context

### Key Entities

- **Codebase**: Represents a complete software project uploaded by a user. Attributes: unique identifier, name, description, upload source (ZIP/GitHub URL), total file count, processed file count, primary language(s), all languages, upload timestamp, ingestion status (queued/processing/completed/failed), size in bytes, workflow_id, file storage path, secrets_detected count, secrets_summary (dict mapping file paths to secret type counts), error_message.

- **Code Chunk**: Represents a semantically meaningful unit of code extracted from a codebase. Attributes: unique identifier, codebase ID, source file path, line start/end numbers, code content, language, chunk type (function/class/module), name, metadata (dependencies, docstring, complexity), embedding vector.

- **Query Session**: Represents a conversation between a user and the system about a specific codebase. Attributes: unique session ID, codebase ID, user-provided identifier, creation timestamp, list of messages exchanged. Multiple concurrent sessions supported (up to 100 concurrent users).

- **Query Message**: Represents a single question or answer in a conversation. Attributes: message ID, session ID, role (user/assistant), content, timestamp, citations (for assistant messages), retrieved chunks (for context).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 90% of queries return responses within 3 seconds of submission
- **SC-002**: 85% of queries retrieve relevant code chunks in the top 5 results (measured by human evaluation)
- **SC-003**: System can process and index a codebase with 1,000 files within 10 minutes
- **SC-004**: 95% of source citations in generated answers are accurate (correct file and line numbers)
- **SC-005**: System supports at least 5 major programming languages (Python, JavaScript/TypeScript, Java, Go, Rust) with successful parsing and chunking
- **SC-006**: Users can successfully upload and query a codebase end-to-end without errors in under 5 minutes
- **SC-006a**: System supports 100 concurrent users with independent sessions without degradation in response time beyond the 3-second target
- **SC-007**: System maintains 99% uptime during continuous operation over a 24-hour period
- **SC-008**: 90% of users can complete their primary task (upload codebase + ask question) on their first attempt without needing assistance

### User Satisfaction Outcomes

- **SC-009**: Users rate the relevance of query answers as 4 out of 5 or higher on average
- **SC-010**: Users report that the system helps them understand unfamiliar codebases faster than manual code review
- **SC-011**: Users find the streaming response experience feels responsive and not sluggish

### Business Outcomes

- **SC-012**: Development teams using the system reduce onboarding time for new members by at least 30%
- **SC-013**: Code review efficiency improves by 25% as measured by time to review PRs
