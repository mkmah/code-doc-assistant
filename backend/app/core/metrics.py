"""Prometheus metrics for monitoring application performance."""

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import Response as FastAPIResponse
from prometheus_client import Counter, Gauge, Histogram, Info
from prometheus_client.exposition import generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Application info
app_info = Info(
    "code_doc_assistant",
    "Code Documentation Assistant application information",
)

# HTTP metrics
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status_code"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"]
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress", "HTTP requests currently in progress", ["method", "endpoint"]
)

# Codebase metrics
codebase_uploads_total = Counter(
    "codebase_uploads_total",
    "Total codebase uploads",
    ["source_type", "status"],  # source_type: zip|github, status: success|failure
)

codebase_processing_duration_seconds = Histogram(
    "codebase_processing_duration_seconds",
    "Time taken to process a codebase",
    ["status"],  # status: success|failure
)

codebases_total = Gauge(
    "codebases_total",
    "Total number of codebases",
    ["status"],  # status: pending|processing|ready|failed
)

# Query metrics
query_requests_total = Counter(
    "query_requests_total",
    "Total query requests",
    ["status"],  # status: success|failure
)

query_duration_seconds = Histogram(
    "query_duration_seconds", "Time taken to process a query", ["status"]
)

# Chat-specific metrics (T055: query latency)
chat_requests_total = Counter(
    "chat_requests_total",
    "Total chat requests",
    ["status"],  # status: success|failure
)

chat_errors_total = Counter(
    "chat_errors_total",
    "Total chat errors",
    ["error_type"],  # error_type: rate_limit|session_not_found|llm_error
)

chat_latency_seconds = Histogram(
    "chat_latency_seconds",
    "Chat endpoint latency (p50, p95, p99)",
    buckets=[0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0]  # Up to 30s
)

# Session metrics
active_sessions = Gauge(
    "active_sessions",
    "Number of active chat sessions",
)

sessions_created_total = Counter(
    "sessions_created_total",
    "Total sessions created",
)

chunks_retrieved = Histogram(
    "chunks_retrieved", "Number of chunks retrieved per query", buckets=[1, 2, 5, 10, 20, 50, 100]
)

# Retrieval accuracy metrics (T055: retrieval accuracy)
retrieval_accuracy_count = Counter(
    "retrieval_accuracy_count",
    "Retrieval accuracy tracking",
    ["relevant"],  # relevant: true|false
)

# LLM metrics
llm_requests_total = Counter(
    "llm_requests_total",
    "Total LLM API requests",
    ["provider", "model", "status"],  # provider: anthropic|openai, status: success|failure
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total LLM tokens used",
    ["provider", "model", "type"],  # type: input|output
)

# Token usage metrics (T055: token usage)
llm_tokens_used = Gauge(
    "llm_tokens_used",
    "LLM tokens used per request",
    ["provider", "model", "type"],  # type: input|output
)

llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds", "LLM API request latency", ["provider", "model"]
)

# Embedding metrics
embedding_requests_total = Counter(
    "embedding_requests_total",
    "Total embedding API requests",
    ["provider", "status"],  # provider: jina|openai
)

embedding_chunks_total = Counter("embedding_chunks_total", "Total chunks embedded", ["provider"])

# Vector store metrics
vector_store_operations_total = Counter(
    "vector_store_operations_total",
    "Total vector store operations",
    ["operation", "status"],  # operation: add|query|delete
)

vector_store_operation_duration_seconds = Histogram(
    "vector_store_operation_duration_seconds", "Vector store operation latency", ["operation"]
)

# ChromaDB query duration (T055: chromadb query duration)
chromadb_query_duration_seconds = Histogram(
    "chromadb_query_duration_seconds",
    "ChromaDB query latency",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]  # 1ms to 1s
)

# Temporal workflow metrics
temporal_workflows_total = Counter(
    "temporal_workflows_total", "Total Temporal workflows started", ["workflow_type", "status"]
)

temporal_workflow_duration_seconds = Histogram(
    "temporal_workflow_duration_seconds", "Temporal workflow execution time", ["workflow_type"]
)

# Agent metrics
agent_execution_duration_seconds = Histogram(
    "agent_execution_duration_seconds", "Time taken for agent to process a query", ["status"]
)

agent_node_duration_seconds = Histogram(
    "agent_node_duration_seconds", "Time taken for each agent node", ["node_name"]
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Get endpoint path (remove parameters)
        endpoint = request.url.path
        try:
            path_params = dict(request.path_params)
            for param_value in path_params.values():
                endpoint = endpoint.replace(str(param_value), "{param}")
        except (AttributeError, TypeError):
            # If path_params is not iterable or has unexpected structure, skip it
            pass

        method = request.method

        # Track in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        # Measure duration
        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code

            # Record metrics
            http_requests_total.labels(
                method=method, endpoint=endpoint, status_code=status_code
            ).inc()

            duration = time.time() - start_time
            http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception:
            # Record error metrics
            http_requests_total.labels(method=method, endpoint=endpoint, status_code=500).inc()

            duration = time.time() - start_time
            http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

            raise

        finally:
            # Decrease in-progress counter
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()


def init_metrics(version: str = "0.1.0", environment: str = "development") -> None:
    """Initialize metrics with application info."""
    app_info.info({"version": version, "environment": environment})


def get_metrics_router():
    """Get the Prometheus metrics router."""
    from fastapi import APIRouter

    router = APIRouter()

    @router.get("/metrics")
    async def metrics():
        """Return Prometheus metrics."""
        return FastAPIResponse(
            content=generate_latest(),
            media_type="text/plain",
        )

    return router
