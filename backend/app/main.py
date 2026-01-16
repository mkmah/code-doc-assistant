"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import chat, codebase, health
from app.core.config import get_settings
from app.core.errors import (
    AppError,
    app_error_handler,
    generic_exception_handler,
    http_exception_handler,
)
from app.core.logging import get_logger, setup_logging
from app.core.metrics import MetricsMiddleware, get_metrics_router, init_metrics
from app.core.tracing import init_tracing, shutdown_tracing
from app.db.session import close_db, init_db
from app.services.redis_session_store import get_redis_session_store

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events including:
    - Database connection initialization
    - Redis connection initialization
    - Graceful shutdown of all connections

    Note: Session cleanup is handled by a Temporal cron workflow
    that runs independently in the temporal worker.
    """

    # Setup logging
    setup_logging()

    # Initialize metrics
    init_metrics(version="1.0.0", environment=settings.environment)

    # Initialize tracing
    init_tracing(service_name="code-doc-assistant-backend")

    # Initialize database connection pool
    await init_db()

    # Initialize Redis connection (connection pool created on first use)
    redis_store = get_redis_session_store()
    await redis_store._get_redis()  # Initialize connection pool
    logger.info("redis_connection_initialized")

    logger.info(
        "application_starting",
        version="1.0.0",
        log_level=settings.log_level,
        environment=settings.environment,
        tracing_enabled=settings.enable_tracing,
        database=settings.app_db_name,
        redis_host=settings.redis_host,
    )

    yield

    logger.info("application_shutting_down")

    # Close Redis connection pool
    await redis_store.close()

    # Close database connection pool
    await close_db()

    # Shutdown tracing to flush any pending spans
    shutdown_tracing()

    logger.info("application_shutdown_complete")


# Create FastAPI application
app = FastAPI(
    title="Code Documentation Assistant API",
    description="RAG-based code documentation assistant API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add metrics middleware
app.add_middleware(MetricsMiddleware)

# Register error handlers
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Register routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(codebase.router, prefix="/api/v1/codebase", tags=["codebase"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])

# Register metrics endpoint
app.include_router(get_metrics_router(), prefix="/metrics", tags=["metrics"])


@app.get("/")
async def root():
    """Root endpoint.

    Returns:
        Welcome message
    """
    return {
        "message": "Code Documentation Assistant API",
        "version": "1.0.0",
        "docs": "/docs",
    }
