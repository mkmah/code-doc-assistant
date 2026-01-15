"""Health check endpoints."""

from fastapi import APIRouter

from app.core.logging import get_logger
from app.services.vector_store import get_vector_store

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health")
async def health_check():
    """Basic health check endpoint.

    Returns:
        Health status response
    """
    return {"status": "healthy", "version": "1.0.0"}


@router.get("/health/ready")
async def readiness_check():
    """Readiness check with dependency validation.

    Returns:
        Readiness status with dependency health
    """
    vector_store = get_vector_store()

    # Check ChromaDB
    chromadb_status = await vector_store.health_check()

    dependencies = {
        "chromadb": "ok" if chromadb_status else "error",
    }

    is_ready = all(status == "ok" for status in dependencies.values())

    if not is_ready:
        logger.warning("readiness_check_failed", dependencies=dependencies)

    return {
        "status": "ready" if is_ready else "not_ready",
        "dependencies": dependencies,
    }
