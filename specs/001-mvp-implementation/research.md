# Research: MVP Implementation - Code Documentation Assistant

**Feature**: 001-mvp-implementation
**Date**: 2026-01-15
**Status**: Complete

## Overview

This document captures research findings and technical decisions for the Code Documentation Assistant MVP. All "NEEDS CLARIFICATION" items from the implementation plan have been resolved.

---

## 1. Temporal Workflow Integration

### Decision
Use Temporal Python SDK with async/await patterns. Define activities with `@activity.defn` decorator and workflows with `@workflow.defn` class decorator.

### Rationale
- **Native Python async support**: Full async/await compatibility with FastAPI and other async services
- **Built-in retry with exponential backoff**: configurable retry policies (2s start, 2x multiplier, 60s cap)
- **Observability**: Automatic tracing, metrics, and history for all workflow executions
- **Durable execution**: Workflows survive server restarts and network failures
- **Activity isolation**: Each processing step (validation, parsing, embedding) is a separate activity

### Implementation Pattern

```python
# Workflow Definition
@workflow.defn
class IngestionWorkflow:
    @workflow.run
    async def run(self, input: IngestionInput) -> IngestionResult:
        # Step 1: Validate
        validation = await workflow.execute_activity(
            validate_codebase,
            args=[input.codebase_id, input.source_type],
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=2),
                backoff_coefficient=2.0,
                maximum_interval=timedelta(seconds=60),
            ),
        )
        # ... more steps
        return result

# Activity Definition
@activity.defn
async def validate_codebase(codebase_id: UUID, source_type: str) -> dict:
    # Implementation
    return {"valid": True}

# Starting workflow from FastAPI
@router.post("/upload")
async def upload_codebase(file: UploadFile):
    client = await Client.connect(settings.temporal_url)
    workflow_id = await client.start_workflow(
        IngestionWorkflow.run,
        input,
        id=f"ingestion-{codebase_id}",
        task_queue="code-ingestion-task-queue",
    )
```

### Alternatives Considered
- **Celery**: Less durable, no built-in history/observability, requires Redis/RabbitMQ
- **Custom asyncio loop**: More boilerplate, no durability, requires custom retry logic
- **AWS Step Functions**: Cloud vendor lock-in, higher latency, cost overhead

---

## 2. Tree-sitter Language Parser Setup

### Decision
Use `tree-sitter-languages` package with pre-compiled grammars. Enable error-tolerant parsing mode to skip invalid nodes.

### Rationale
- **Multi-language support**: Python, JavaScript, TypeScript, Java, Go, Rust, C++, etc.
- **Battle-tested**: Used by GitHub Code Search, Neovim, VS Code
- **Fast parsing**: Incremental parsing, optimized for large files
- **Error-tolerant**: Continues parsing even with syntax errors
- **AST-based**: Provides accurate function/class boundaries vs regex

### Implementation Pattern

```python
import tree_sitter_languages as tsl
from tree_sitter import Language, Parser

class CodeParser:
    def __init__(self):
        self._parsers = {}
        self._languages = {
            "python": Language(tsl.python()),
            "javascript": Language(tsl.javascript()),
            "typescript": Language(tsl.typescript()),
            # ... more languages
        }

    def parse_file(self, file_path: str, content: str):
        language = self.detect_language(file_path)
        parser = Parser(self._languages[language])
        tree = parser.parse(content.encode())

        # Extract functions/classes
        root_node = tree.root_node
        for node in root_node.children:
            if node.type == "function_definition":
                # Extract metadata
                pass
```

### Alternatives Considered
- **AST module**: Python-only, different API per language
- **Jedi**: Python-only, slower, designed for autocomplete
- **Regex**: Inaccurate for nested structures, no AST understanding

---

## 3. ChromaDB Collection Strategy

### Decision
Use single collection (`code_chunks`) with metadata filtering by `codebase_id`, `language`, and `chunk_type`.

### Rationale
- **Simpler management**: One collection to maintain, backup, and monitor
- **Flexible querying**: Filter by codebase, search across codebases if needed
- **Better performance**: ChromaDB optimizes metadata filtering in single collection
- **Scalability**: Single collection can handle millions of chunks with proper indexing

### Schema

```python
collection.add(
    ids=["chunk-1", "chunk-2"],
    embeddings=[[0.1, ...], [0.2, ...]],
    documents=["def foo(): ...", "class Bar: ..."],
    metadatas=[
        {
            "codebase_id": "uuid-123",
            "file_path": "src/app.py",
            "line_start": 10,
            "line_end": 25,
            "language": "python",
            "chunk_type": "function",
            "name": "foo",
        },
        # ... more chunks
    ]
)
```

### Query Pattern

```python
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5,
    where={"codebase_id": "uuid-123"},  # Filter by codebase
    where_document={"language": "python"},  # Optional language filter
)
```

### Alternatives Considered
- **Per-codebase collections**: Too many collections (one per upload), management overhead
- **Pinecone**: External dependency, cost at scale, network latency
- **Weaviate**: More complex setup, heavier dependency for MVP

---

## 4. LangGraph Agent Architecture

### Decision
State graph with sequential nodes: `query_analysis → retrieval → context_building → response_generation → validation`.

### Rationale
- **Clear separation of concerns**: Each node has single responsibility
- **Built-in state management**: State object flows through nodes automatically
- **Easy to extend**: Add new nodes (e.g., re-ranking, caching) without breaking existing flow
- **Debuggable**: Each node logs inputs/outputs, can inspect intermediate state

### Graph Definition

```python
from langgraph.graph import StateGraph, END

graph = StateGraph(AgentState)

# Add nodes
graph.add_node("query_analysis", query_analysis_node)
graph.add_node("retrieval", retrieval_node)
graph.add_node("context_building", context_building_node)
graph.add_node("response_generation", response_generation_node)
graph.add_node("validation", validation_node)

# Define edges
graph.set_entry_point("query_analysis")
graph.add_edge("query_analysis", "retrieval")
graph.add_edge("retrieval", "context_building")
graph.add_edge("context_building", "response_generation")
graph.add_edge("response_generation", "validation")
graph.add_edge("validation", END)

# Compile with error handler
app = graph.compile()
```

### State Model

```python
class AgentState(TypedDict):
    query: str
    codebase_id: UUID
    session_id: UUID
    step: str
    retrieved_chunks: list[dict]
    context: str
    response: str
    sources: list[Source]
    error: str | None
```

### Alternatives Considered
- **LangChain Agent**: Less control over flow, harder to debug, abstracted away from state
- **Custom workflow**: More boilerplate, need to implement state passing, error handling
- **Direct API calls**: No agent benefits (can't add tools, multi-step reasoning)

---

## 5. SSE Streaming Implementation

### Decision
FastAPI `StreamingResponse` with async generator. LangGraph state streamed via custom callback handler.

### Rationale
- **Native FastAPI support**: Built-in `StreamingResponse` type
- **Client-compatible**: Works with browser EventSource, fetch, curl
- **Low latency**: Streams tokens as they arrive from LLM
- **Simple implementation**: Generator function yields chunks

### Implementation Pattern

```python
from fastapi.responses import StreamingResponse

@router.post("/chat")
async def chat(request: ChatRequest):
    async def generate():
        async for chunk in llm_service.generate_response(
            query=request.query,
            context=context,
        ):
            yield f"data: {json.dumps({'content': chunk})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
```

### Client Pattern

```typescript
const eventSource = new EventSource('/api/v1/chat');
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  appendToChat(data.content);
};
```

### Alternatives Considered
- **WebSocket**: Overkill for unidirectional streaming, more complex connection management
- **Polling**: Poor UX (delay between responses), unnecessary server load
- **gRPC streaming**: Requires protobuf, not browser-friendly

---

## 6. Secret Detection Patterns

### Decision
Regex-based detection for common secret patterns. Redact with typed placeholders `[REDACTED_TYPE]`.

### Rationale
- **Fast**: Regex matching is O(n) per file, no ML overhead
- **Simple**: Easy to add new patterns, understand what's detected
- **Covers 90% of cases**: AWS keys, JWT, basic auth, passwords common in code
- **No ML dependency**: No model loading, false positive training

### Patterns

```python
SECRET_PATTERNS = {
    "AWS_ACCESS_KEY": r"AKIA[0-9A-Z]{16}",
    "GCP_KEY": r'"type":\s*"service_account"',
    "JWT_TOKEN": r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+",
    "BASIC_AUTH": r"[a-zA-Z]:[a-zA-Z0-9_\-\.]+@[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}",
    "PASSWORD_ASSIGN": r"password\s*=\s*['\"]([^'\"]+)['\"]",
}
```

### Redaction Pattern

```python
def redact_secrets(content: str) -> tuple[str, SecretScanResult]:
    detected = []
    for secret_type, pattern in SECRET_PATTERNS.items():
        matches = re.finditer(pattern, content)
        for match in matches:
            detected.append({
                "type": secret_type,
                "start": match.start(),
                "end": match.end(),
            })
            content = content[:match.start()] + f"[REDACTED_{secret_type}]" + content[match.end():]

    return content, SecretScanResult(
        has_secrets=len(detected) > 0,
        secret_count=len(detected),
        secrets=detected,
    )
```

### Alternatives Considered
- **truffleHog**: Heavy dependency (Git parsing), slower, overkill for in-memory files
- **ML classifier**: Overkill for MVP, requires training data, false positives
- **No detection**: Security risk (users upload secrets to vector DB)

---

## 7. File Storage Backend

### Decision
Local filesystem with configurable base path. Files named by `codebase_id` (UUID).

### Rationale
- **Simple for MVP**: No external dependencies, works on local machine
- **Easy cleanup**: Delete file by codebase_id on codebase deletion
- **Sufficient performance**: Local filesystem I/O is fast enough for 100MB files
- **Observable**: File size, mtime, permissions visible via standard tools

### Implementation Pattern

```python
# Config
class Settings(BaseSettings):
    file_storage_path: str = "/tmp/codebase_files"

# Storage
async def store_file(codebase_id: UUID, content: bytes) -> str:
    file_path = Path(settings.file_storage_path) / str(codebase_id)
    file_path.write_bytes(content)
    return str(file_path)

async def delete_file(codebase_id: UUID):
    file_path = Path(settings.file_storage_path) / str(codebase_id)
    if file_path.exists():
        file_path.unlink()
```

### Alternatives Considered
- **S3**: Overkill for MVP, network latency, cost, AWS dependency
- **Database BLOB**: Performance issues (large objects slow queries), storage bloat
- **Memory-only**: Not durable across restarts, memory pressure

---

## 8. Session Store Implementation

### Decision
In-memory dict with UUID keys. Session timeout configured via `session_timeout_seconds`.

### Rationale
- **Simple for MVP**: No external dependencies, works on single instance
- **Sufficient for 100 concurrent users**: Memory usage ~1KB per session (100KB total)
- **Fast**: O(1) lookup by UUID
- **Easy cleanup**: Background task removes expired sessions

### Implementation Pattern

```python
class SessionStore:
    def __init__(self):
        self._sessions: dict[UUID, QuerySession] = {}
        self._messages: dict[UUID, list[QueryMessage]] = {}

    async def create_session(self, codebase_id: UUID) -> QuerySession:
        session_id = uuid4()
        session = QuerySession(
            session_id=session_id,
            codebase_id=codebase_id,
            created_at=datetime.utcnow(),
            last_active=datetime.utcnow(),
        )
        self._sessions[session_id] = session
        self._messages[session_id] = []
        return session

    async def cleanup_expired_sessions(self) -> int:
        now = datetime.utcnow()
        expired = [
            sid for sid, session in self._sessions.items()
            if (now - session.last_active).total_seconds() > settings.session_timeout_seconds
        ]
        for sid in expired:
            del self._sessions[sid]
            del self._messages[sid]
        return len(expired)
```

### Alternatives Considered
- **Redis**: Overkill for single-instance MVP, network latency, external dependency
- **Database**: Slower than memory (disk I/O), adds query complexity
- **JWT tokens**: Stateless, can't list sessions, can't delete on logout

---

## 9. Embedding Service Selection

### Decision
Jina AI `jina-embeddings-v4` as primary, OpenAI `text-embedding-3-small` as fallback.

### Rationale
- **Jina v4**: Optimized for code, 8192 context length (better than OpenAI's 8191), cheaper
- **Code-specific**: Trained on code corpus, better for semantic code search
- **Fallback strategy**: If Jina fails/rate-limits, fall back to OpenAI automatically
- **Cost**: Jina is $0.01/1M tokens (cheaper than OpenAI's $0.02/1M)

### Implementation Pattern

```python
class EmbeddingService:
    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        try:
            # Try Jina first
            return await self._generate_jina(texts)
        except Exception as e:
            logger.warning("jina_failed", error=str(e))
            # Fallback to OpenAI
            return await self._generate_openai(texts)
```

### Alternatives Considered
- **Only OpenAI**: More expensive, not code-optimized
- **Cohere**: Good for text, less proven for code
- **Local models**: Slower inference, GPU requirements, worse quality

---

## 10. Hybrid Search Strategy

### Decision
Dense retrieval (semantic) as primary, sparse retrieval (keyword) as re-ranking boost.

### Rationale
- **Dense (semantic)**: Good for conceptual queries ("how does auth work?")
- **Sparse (keyword)**: Good for specific queries ("function named 'authenticate'")
- **Hybrid**: Best of both, re-rank dense results with keyword similarity
- **Implementation**: ChromaDB for dense, BM25 for sparse, combine scores

### Scoring Formula

```python
final_score = 0.7 * dense_score + 0.3 * sparse_score
```

### Alternatives Considered
- **Dense only**: Misses exact matches (function names, specific strings)
- **Sparse only**: Misses conceptual queries (intent-based search)
- **Separate indices**: More complex, need to merge results manually

---

## Summary

All technical decisions resolved. No outstanding "NEEDS CLARIFICATION" items remain. Research phase complete, ready to proceed to Phase 1 (Design & Contracts).

### Key Decisions Recap

| Area | Decision | Primary Benefit |
|------|----------|-----------------|
| Workflow | Temporal async SDK | Durable, retryable, observable |
| Parsing | Tree-sitter multi-lang | Fast, accurate, error-tolerant |
| Vector DB | ChromaDB single collection | Simple, flexible, scalable |
| Agent | LangGraph state graph | Clear separation, debuggable |
| Streaming | FastAPI SSE | Native, simple, low-latency |
| Secrets | Regex-based | Fast, simple, covers 90% |
| Storage | Local filesystem | Simple, no dependencies |
| Sessions | In-memory dict | Fast, simple, sufficient |
| Embeddings | Jina v4 + OpenAI fallback | Code-optimized, cost-effective |
| Search | Hybrid dense+sparse | Best of both worlds |

---

**Generated**: 2026-01-15 | **Phase**: 0 (Research) | **Status**: Complete
