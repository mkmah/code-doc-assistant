# Architecture Documentation

## System Overview

The Code Documentation Assistant is a RAG-based system that ingests codebases and provides natural language query capabilities. The architecture follows a microservices pattern with clear separation between ingestion, query processing, and frontend concerns.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Frontend (React)                                │
│                         TanStack Start + shadcn/ui                           │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ HTTP/SSE
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Backend (FastAPI)                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Upload     │  │     Chat     │  │   Status     │  │   Health     │   │
│  │   Endpoint   │  │   Endpoint   │  │   Endpoint   │  │   Endpoint   │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │                 │           │
│  ┌──────▼─────────────────▼─────────────────▼─────────────────▼───────┐   │
│  │                        Services Layer                               │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐   │   │
│  │  │ Codebase   │  │ Embedding  │  │ Retrieval  │  │    LLM     │   │   │
│  │  │ Processor  │  │  Service   │  │  Service   │  │  Service   │   │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Agent Layer (LangGraph)                      │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │   Query  │ │Retrieval│ │ Context │ │Response │ │Validation│  │   │
│  │  │ Analysis │ │   Node   │ │Building│ │Generation│ │   Node   │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │   Temporal   │  │  ChromaDB    │  │   External   │
            │   Workflows  │  │ Vector Store │  │    APIs      │
            └──────────────┘  └──────────────┘  └──────────────┘
                                                   │
                              ┌────────────────────┼────────────────────┐
                              ▼                    ▼                    ▼
                        ┌──────────┐         ┌──────────┐         ┌──────────┐
                        │  Claude  │         │  Jina AI │         │  OpenAI  │
                        │    LLM   │         │Embeddings│         │(fallback)│
                        └──────────┘         └──────────┘         └──────────┘
```

## Components

### 1. Frontend Layer

**Technology**: TanStack Start (React), TypeScript, shadcn/ui, Tailwind CSS

**Components**:
- `UploadForm`: Handles ZIP file and GitHub URL uploads
- `StatusTracker`: Real-time ingestion progress monitoring
- `ChatInterface`: Streaming chat interface with SSE
- `CodeViewer`: Syntax-highlighted code display

**State Management**: TanStack Query (React Query) for server state

**Routing**: File-based routing via TanStack Router

### 2. API Layer

**Technology**: FastAPI, Python 3.11+

**Endpoints**:
- `/api/v1/codebase/upload` - Upload codebase (ZIP or GitHub)
- `/api/v1/codebase` - List all codebases (paginated)
- `/api/v1/codebase/{id}` - Get codebase details
- `/api/v1/codebase/{id}/status` - Get ingestion status
- `/api/v1/codebase/{id}` - Delete codebase
- `/api/v1/chat` - Query codebase (SSE streaming)
- `/health` - Health check
- `/metrics` - Prometheus metrics

**Middleware**:
- CORS for cross-origin requests
- Metrics collection (request counts, latency, errors)
- Error handling with custom exception types
- Request ID tracking

### 3. Services Layer

#### Codebase Processor
Orchestrates the ingestion pipeline:
1. Input validation
2. File extraction/cloning
3. Code parsing
4. Chunking
5. Embedding generation
6. Vector indexing

**Features**:
- Multi-language support (Python, JS/TS, Java, Go, Rust)
- Secret detection and redaction
- Error-tolerant parsing (continues on invalid files)
- Progress tracking

#### Embedding Service
Generates vector embeddings with fallback:
- Primary: Jina AI jina-embeddings-v4
- Fallback: OpenAI text-embedding-3-small

**Features**:
- Batch processing for efficiency
- Automatic retry with exponential backoff
- Graceful fallback on failure

#### Retrieval Service
Performs hybrid search:
- Dense retrieval (semantic similarity)
- Sparse retrieval (keyword matching)
- Result fusion and ranking

**Features**:
- Configurable top-k results
- Citation extraction (file paths, line numbers)
- Relevance scoring

#### LLM Service
Manages Claude API interactions:
- Streaming responses
- Session history management
- Token counting and limits

**Features**:
- Async streaming for low latency
- Automatic token tracking
- Error handling with retry

### 4. Agent Layer (LangGraph)

**Technology**: LangGraph, LangChain

**Graph Structure**:
```
┌────────────┐
│ Query      │
│ Analysis   │
└─────┬──────┘
      │
      ▼
┌────────────┐
│ Retrieval  │
└─────┬──────┘
      │
      ▼
┌────────────┐
│ Context    │
│ Building   │
└─────┬──────┘
      │
      ▼
┌────────────┐
│ Response   │
│ Generation │
└─────┬──────┘
      │
      ▼
┌────────────┐
│ Validation │
└─────┬──────┘
      │
      ▼
   [END]
```

**Nodes**:

1. **Query Analysis**
   - Identifies query intent
   - Extracts key terms
   - Determines query type

2. **Retrieval**
   - Performs hybrid search
   - Retrieves top-k chunks
   - Extracts citations

3. **Context Building**
   - Formats retrieved chunks
   - Adds metadata
   - Constructs prompt context

4. **Response Generation**
   - Calls Claude API
   - Streams response
   - Formats output

5. **Validation**
   - Checks response quality
   - Validates citations
   - Handles edge cases

### 5. Workflow Layer (Temporal)

**Technology**: Temporal.io

**Workflows**:

#### Ingestion Workflow
```python
def ingestion_workflow(codebase_id: str, source: Source):
    # 1. Clone/extract files
    files = clone_or_extract_activity(source)

    # 2. Parse code
    parsed = parse_code_activity(files)

    # 3. Create chunks
    chunks = chunk_code_activity(parsed)

    # 4. Detect and redact secrets
    chunks = redact_secrets_activity(chunks)

    # 5. Generate embeddings
    embeddings = generate_embeddings_activity(chunks)

    # 6. Index in vector store
    index_vectors_activity(codebase_id, embeddings)
```

**Activities**:
- `CloneActivity`: Git clone or ZIP extraction
- `ParseActivity`: Tree-sitter parsing
- `ChunkActivity`: Semantic chunking
- `EmbedActivity`: Embedding generation
- `IndexActivity`: Vector store insertion

**Retry Policy**:
- Initial interval: 2s
- Multiplier: 2x
- Maximum interval: 60s
- Total timeout: 30 minutes

### 6. Storage Layer

#### ChromaDB (Vector Store)
- Local development: Embedded ChromaDB
- Production: Pinecone migration path
- Collections: One per codebase
- Embedding dimension: 768 (Jina AI)

#### In-Memory Stores (MVP)
- `CodebaseStore`: Codebase metadata
- `SessionStore`: Query session history

**Production Migration**:
- PostgreSQL for metadata
- Redis for caching
- Pinecone for vectors

### 7. External APIs

#### Claude (Anthropic)
- Model: claude-3-5-sonnet-20241022
- Max tokens: 4096
- Streaming: Enabled
- Purpose: Response generation

#### Jina AI
- Model: jina-embeddings-v4
- Dimension: 768
- Batch size: 100
- Purpose: Embeddings (primary)

#### OpenAI (Fallback)
- Model: text-embedding-3-small
- Dimension: 1536
- Purpose: Embeddings (fallback)

## Data Flow

### Ingestion Flow

```
┌──────────┐
│  Upload  │
│  Request │
└────┬─────┘
     │
     ▼
┌────────────────┐
│ Validate Input │
└────┬───────────┘
     │
     ▼
┌────────────────┐
│ Create Codebase│
│    Record      │
└────┬───────────┘
     │
     ▼
┌────────────────┐
│ Start Temporal │
│   Workflow     │
└────┬───────────┘
     │
     ▼
┌────────────────┐
│ Return 202     │
│  with codebase │
│      ID        │
└────────────────┘
     │
     │ (async processing)
     ▼
┌────────────────┐
│ Clone/Extract  │
└────┬───────────┘
     │
     ▼
┌────────────────┐
│ Parse with     │
│ Tree-sitter    │
└────┬───────────┘
     │
     ▼
┌────────────────┐
│ Create Chunks  │
└────┬───────────┘
     │
     ▼
┌────────────────┐
│ Detect Secrets │
└────┬───────────┘
     │
     ▼
┌────────────────┐
│ Generate       │
│ Embeddings     │
└────┬───────────┘
     │
     ▼
┌────────────────┐
│ Index Vectors  │
└────┬───────────┘
     │
     ▼
┌────────────────┐
│ Update Status  │
│ to COMPLETED   │
└────────────────┘
```

### Query Flow

```
┌──────────┐
│   Query  │
│  Request │
└────┬─────┘
     │
     ▼
┌────────────────┐
│ Validate Input │
└────┬───────────┘
     │
     ▼
┌────────────────┐
│  Create Query  │
│    Agent       │
└────┬───────────┘
     │
     ▼
┌────────────────┐
│ Query Analysis │
│    Node        │
└────┬───────────┘
     │
     ▼
┌────────────────┐
│  Retrieval     │
│    Node        │
└────┬───────────┘
     │
     ▼
┌────────────────┐
│   Context      │
│   Building     │
└────┬───────────┘
     │
     ▼
┌────────────────┐
│   Response     │
│  Generation    │
└────┬───────────┘
     │
     ▼
┌────────────────┐
│   Validation   │
└────┬───────────┘
     │
     ▼
┌────────────────┐
│ Stream via SSE │
└────────────────┘
```

## Security

### Secret Detection

**Patterns Detected**:
- AWS API Keys: `AKIA[0-9A-Z]{16}`
- GitHub Tokens: `ghp_[a-zA-Z0-9]{36}`
- JWT Tokens: `eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*`
- API Keys: `api[_-]?key\s*=\s*['"][^'"]{10,}['"]`
- Passwords: `password\s*=\s*['"][^'"]+['"]`

**Redaction**:
- Format: `[REDACTED_TYPE]`
- Logged to ingestion status
- Original content never stored

### API Key Management

- Stored in environment variables
- Never logged or exposed
- Rotation supported via restart

## Performance

### Targets

| Metric | Target |
|--------|--------|
| Query latency (p95) | <3s |
| Ingestion time | 1,000 files in 10min |
| Retrieval accuracy | >85% relevant in top-5 |
| Citation accuracy | >95% correct references |
| Concurrent users | 100 (MVP) |

### Optimization Strategies

1. **Batch Processing**: Embeddings generated in batches of 100
2. **Async I/O**: All external calls are async
3. **Connection Pooling**: Reused HTTP connections
4. **Vector Indexing**: Optimized ChromaDB configuration
5. **Streaming**: Real-time response delivery

## Monitoring

### Metrics (Prometheus)

- HTTP request count, latency, errors
- Codebase uploads, processing time
- Query count, duration, chunks retrieved
- LLM requests, tokens used
- Embedding requests, chunks embedded
- Vector store operations
- Temporal workflow executions

### Logging (structlog)

Structured JSON logs with:
- Request ID for tracing
- Error context
- Performance metrics
- Debug information

### Health Checks

- `/health`: Basic health
- `/health/ready`: Readiness probe
- Checks: Database, Temporal, external APIs

## Deployment

### Local Development

- Docker Compose for all services
- Hot reload via Tilt
- Local ChromaDB

### Production

- Kubernetes deployment
- Managed services (Pinecone, Temporal Cloud)
- Horizontal pod autoscaling
- Monitoring via Prometheus + Grafana

## Scalability

### Horizontal Scaling

- API servers: Stateless, multiple instances
- Temporal workers: Auto-scaling based on queue depth
- Frontend: Static asset delivery via CDN

### Vertical Scaling

- Embedding service: Batch size tuning
- LLM service: Connection pool sizing
- Vector store: Memory and storage optimization

### Bottlenecks

1. **Embedding Generation**: Rate limits, batch processing
2. **LLM API**: Token limits, rate limits
3. **Vector Search**: Large codebases, query optimization
4. **File I/O**: Cloning and extraction speed

## Future Enhancements

1. **Multi-user Support**: Authentication and authorization
2. **Persistent Storage**: PostgreSQL, Redis migration
3. **Advanced Search**: Hybrid search optimization
4. **Code Visualization**: Dependency graphs, call trees
5. **CI/CD Integration**: Automated documentation updates
6. **Multi-model Support**: GPT-4, Gemini, etc.
7. **Code Execution**: Sandboxed code execution for demos
