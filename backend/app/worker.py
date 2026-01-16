"""Temporal worker for codebase ingestion and maintenance workflows."""

import asyncio

import structlog
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions

from app.activities import (
    cleanup_expired_sessions_activity,
    clone_or_extract,
    generate_embeddings,
    index_chunks,
    parse_codebase,
    scan_for_secrets_activity,
    update_codebase_status_activity,
    validate_codebase,
)
from app.core.config import get_settings
from app.types import SessionCleanupInput
from app.workflows import IngestionWorkflow, SessionCleanupWorkflow

settings = get_settings()
logger = structlog.get_logger(__name__)


def setup_logging() -> None:
    """Configure structlog for logging."""
    import logging

    log_level = settings.log_level.upper()

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Set standard logging level
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO))


async def run_worker() -> None:
    """Run the Temporal worker."""
    setup_logging()

    # Connect to Temporal server
    client = await Client.connect(settings.temporal_url)

    logger.info("temporal_worker_starting", temporal_url=settings.temporal_url)

    # Run worker
    async with Worker(
        client,
        task_queue="code-ingestion-task-queue",
        workflows=[IngestionWorkflow, SessionCleanupWorkflow],
        activities=[
            validate_codebase,
            clone_or_extract,
            parse_codebase,
            scan_for_secrets_activity,
            generate_embeddings,
            index_chunks,
            cleanup_expired_sessions_activity,
            update_codebase_status_activity,
        ],
        workflow_runner=SandboxedWorkflowRunner(
            restrictions=SandboxRestrictions.default.with_passthrough_modules(
                "app.types", "structlog"
            )
        ),
    ):
        logger.info("temporal_worker_running")

        # Start the session cleanup cron workflow
        # This runs daily at 2 AM to clean up expired session references
        try:
            await client.start_workflow(
                SessionCleanupWorkflow.run,
                SessionCleanupInput(),
                id="session-cleanup-workflow",
                task_queue="code-ingestion-task-queue",
                cron_schedule="0 2 * * *",  # Daily at 2 AM
            )
            logger.info("session_cleanup_cron_workflow_started")
        except Exception as e:
            # Workflow may already exist (e.g., worker restart)
            logger.info(
                "session_cleanup_workflow_exists_or_failed",
                error=str(e) if e else "already_exists",
            )

        # Keep worker running
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(run_worker())
