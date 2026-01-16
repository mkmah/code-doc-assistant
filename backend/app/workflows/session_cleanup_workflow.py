"""Temporal cron workflow for session cleanup."""

from datetime import timedelta

import structlog
from temporalio import workflow

from app.types import SessionCleanupInput, SessionCleanupResult

logger = structlog.get_logger(__name__)


@workflow.defn
class SessionCleanupWorkflow:
    """Cron workflow for cleaning up expired sessions.

    This workflow runs on a schedule (daily at 2 AM by default) to:
    1. Clean up expired session entries from codebase indexes
    2. Remove stale references in codebase:{id}:sessions sets

    Redis handles TTL-based expiration automatically for session data,
    but we need to clean up references in the codebase session indexes.

    Benefits of using Temporal for this:
    - Durable execution (survives restarts)
    - Built-in retry policies
    - Observability via Temporal UI
    - Consistent with other async tasks in the system
    """

    @workflow.run
    async def run(self, input: SessionCleanupInput) -> SessionCleanupResult:
        """Execute the session cleanup workflow.

        Args:
            input: Empty input for cron workflow

        Returns:
            SessionCleanupResult with cleanup statistics
        """
        logger.info("session_cleanup_workflow_started")

        try:
            result = await workflow.execute_activity(
                "cleanup_expired_sessions_activity",
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=workflow.RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    backoff_coefficient=2.0,
                    maximum_interval=timedelta(minutes=1),
                    maximum_attempts=3,
                ),
            )

            logger.info(
                "session_cleanup_workflow_completed",
                cleaned_sessions=result.get("cleaned_sessions", 0),
                retention_days=result.get("retention_days", 0),
            )

            return SessionCleanupResult(
                status="success",
                cleaned_sessions=result.get("cleaned_sessions", 0),
                retention_days=result.get("retention_days", 0),
            )

        except Exception as e:
            logger.error(
                "session_cleanup_workflow_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
