"""Temporal activities for cleanup tasks."""

import structlog
from temporalio import activity

from app.core.config import get_settings
from app.services.redis_session_store import get_redis_session_store

logger = structlog.get_logger(__name__)
settings = get_settings()


@activity.defn
async def cleanup_expired_sessions_activity() -> dict:
    """Clean up expired sessions from codebase indexes.

    Redis handles TTL automatically for session data, but we need
    to clean up stale entries in the codebase:{id}:sessions sets.

    This activity should be run daily via a Temporal cron workflow.

    Returns:
        Dictionary with cleanup results including count of removed sessions
    """
    try:
        redis_store = get_redis_session_store()
        cleaned_count = await redis_store.cleanup_expired_sessions()

        logger.info(
            "temporal_session_cleanup_completed",
            cleaned_sessions=cleaned_count,
            retention_days=settings.session_retention_days,
        )

        return {
            "status": "success",
            "cleaned_sessions": cleaned_count,
            "retention_days": settings.session_retention_days,
        }

    except Exception as e:
        logger.error(
            "temporal_session_cleanup_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise activity.ApplicationError(f"Session cleanup failed: {e}") from e
