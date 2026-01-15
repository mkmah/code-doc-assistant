"""Temporal worker for codebase ingestion workflows."""

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging

from temporal.activities import (
    clone_or_extract,
    generate_embeddings,
    index_chunks,
    parse_codebase,
    validate_codebase,
)
from temporal.workflows import IngestionWorkflow

settings = get_settings()
logger = get_logger(__name__)


async def run_worker() -> None:
    """Run the Temporal worker."""
    setup_logging()

    # Connect to Temporal server
    client = await Client.connect(
        settings.temporal_url,
    )

    logger.info(
        "temporal_worker_starting",
        temporal_url=settings.temporal_url,
    )

    # Run worker
    async with Worker(
        client,
        task_queue="code-ingestion-task-queue",
        workflows=[IngestionWorkflow],
        activities=[
            validate_codebase,
            clone_or_extract,
            parse_codebase,
            generate_embeddings,
            index_chunks,
        ],
    ):
        logger.info("temporal_worker_running")
        # Keep worker running
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(run_worker())
