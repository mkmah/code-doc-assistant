# Code Documentation Assistant

A conversational AI assistant that ingests codebases and answers natural language questions using RAG (Retrieval Augmented Generation).

## Features

- **Codebase Ingestion**: Upload codebases via ZIP file or GitHub URL
- **Intelligent Parsing**: Multi-language support (Python, JavaScript, TypeScript, Java, Go, Rust)
- **Semantic Search**: Vector-based retrieval with hybrid search capabilities
- **Conversational Interface**: Ask questions in natural language about your code
- **Citation Support**: All answers reference specific files and line numbers
- **Secret Detection**: Automatically detects and redacts secrets during ingestion
- **Real-time Progress**: Track ingestion status with live updates

## Architecture

- **Backend**: Python 3.11+, FastAPI, Temporal, LangGraph
- **Frontend**: TanStack Start (React), TypeScript, shadcn/ui
- **Code Parsing**: Tree-sitter for multi-language AST parsing
- **Vector Store**: ChromaDB (local) with Pinecone migration path
- **LLM**: Anthropic Claude Sonnet 4
- **Embeddings**: Jina AI jina-embeddings-v4 (primary), OpenAI (fallback)

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- bun (for frontend)

### Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/code-doc-assistant.git
   cd code-doc-assistant
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Start services with Docker Compose**:
   ```bash
   docker-compose -f infra/docker/docker-compose.yml up -d
   ```

4. **Run the Temporal worker** (in a separate terminal):
   ```bash
   cd temporal
   uv pip install -e .
   python worker.py
   ```

5. **Run the backend** (in a separate terminal):
   ```bash
   cd backend
   uv pip install -e .
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Run the frontend** (in a separate terminal):
   ```bash
   cd frontend
   bun install
   bun run dev
   ```

7. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Temporal UI: http://localhost:8080

## Usage

### 1. Upload a Codebase

Navigate to http://localhost:3000 and upload a codebase:
- **ZIP Upload**: Select a ZIP file containing your source code
- **GitHub URL**: Enter a public GitHub repository URL

### 2. Wait for Ingestion

The system will:
1. Clone/extract the codebase
2. Parse code using Tree-sitter
3. Create semantic chunks
4. Generate embeddings
5. Index in vector store

Track progress in real-time on the status page.

### 3. Ask Questions

Once ingestion is complete, ask questions like:
- "How does authentication work?"
- "What are the main API endpoints?"
- "Show me the error handling logic"
- "How is the database connection managed?"

## API Documentation

### Core Endpoints

#### Upload Codebase
```bash
POST /api/v1/codebase/upload
Content-Type: multipart/form-data

{
  "name": "my-codebase",
  "file": <zip file>,
  "github_url": "https://github.com/user/repo"  # optional
}
```

#### Query Codebase
```bash
POST /api/v1/chat
Content-Type: application/json

{
  "codebase_id": "uuid",
  "query": "How does authentication work?"
}
```

Returns a Server-Sent Events (SSE) stream with the response.

#### Get Status
```bash
GET /api/v1/codebase/{id}/status
```

Returns ingestion progress and status.

### Full API Documentation

Interactive API docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

### Backend Commands

```bash
cd backend

# Install dependencies
uv pip install -e .

# Run development server
uvicorn app.main:app --reload

# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html

# Lint code
ruff check .

# Format code
ruff format .
```

### Frontend Commands

```bash
cd frontend

# Install dependencies
bun install

# Run development server
bun run dev

# Run tests
bun test

# Type check
bun run type-check

# Lint
bun run lint

# Format
bun run format
```

### Temporal Worker Commands

```bash
cd temporal

# Install dependencies
uv pip install -e .

# Run worker
python worker.py

# Run workflow tests
pytest tests/workflows/
```

## Project Structure

```
.
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── api/v1/            # REST endpoints
│   │   ├── core/              # Config, logging, errors
│   │   ├── services/          # Business logic
│   │   ├── agents/            # LangGraph agent
│   │   ├── models/            # Pydantic schemas
│   │   └── utils/             # Utilities
│   └── tests/                 # Backend tests
├── frontend/                   # TanStack Start frontend
│   ├── app/
│   │   ├── routes/            # Page routes
│   │   ├── components/        # React components
│   │   └── lib/               # Utilities
│   └── tests/                 # Frontend tests
├── temporal/                   # Temporal workflows
│   ├── workflows/             # Workflow definitions
│   ├── activities/            # Activity functions
│   └── worker.py              # Worker entry point
└── infra/                     # DevOps configs
    ├── docker/                # Docker Compose
    ├── k8s/                   # Kubernetes manifests
    └── monitoring/            # Prometheus/Grafana
```

## Architecture Details

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design.

### Key Design Decisions

1. **Semantic Chunking**: Uses Tree-sitter AST nodes (functions/classes) instead of fixed-size chunks for better context preservation
2. **Hybrid Search**: Combines dense (semantic) and sparse (keyword) retrieval for improved relevance
3. **Secret Redaction**: Automatic detection and redaction of secrets before indexing
4. **Async-First**: All I/O operations use async/await for better performance
5. **Temporal Integration**: Durable workflow execution for reliable ingestion pipeline

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | Required |
| `JINA_API_KEY` | Jina AI API key for embeddings | Required |
| `OPENAI_API_KEY` | OpenAI API key (fallback) | Optional |
| `TEMPORAL_HOST` | Temporal server host | `localhost:7233` |
| `CHROMADB_HOST` | ChromaDB host | `localhost` |
| `CHROMADB_PORT` | ChromaDB port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `ENVIRONMENT` | Environment name | `development` |

## Monitoring

- **Metrics**: Prometheus metrics at `/metrics`
- **Logs**: Structured JSON logs via structlog
- **Health**: `/health` and `/health/ready` endpoints

## Testing

- Backend target: 80% code coverage
- Frontend: Component and integration tests
- E2E tests: Full workflow testing

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

For issues, questions, or contributions, please open an issue on GitHub.
