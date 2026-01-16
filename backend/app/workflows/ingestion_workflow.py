"""Temporal workflow for codebase ingestion."""

from datetime import timedelta
from uuid import UUID

import structlog
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

from app.types import IngestionInput, IngestionResult, IngestionStatus

logger = structlog.get_logger(__name__)


# Signal query for getting current status
@workflow.query
def get_status(self) -> IngestionStatus:
    """Query the current workflow status."""
    raise NotImplementedError


@workflow.defn
class IngestionWorkflow:
    """Workflow for ingesting a codebase.

    Orchestrates the following steps:
    1. Validate the codebase source
    2. Clone repository or extract archive
    3. Scan for secrets (security)
    4. Parse code files
    5. Generate embeddings
    6. Index in vector store

    Each step emits a status signal for progress tracking.
    """

    def __init__(self) -> None:
        """Initialize the workflow."""
        self._current_status = IngestionStatus(
            codebase_id=UUID("00000000-0000-0000-0000-000000000000"),
            step="initializing",
            progress=0.0,
            files_processed=0,
            files_total=0,
            chunks_created=0,
            secrets_found=0,
            message="Initializing ingestion workflow...",
        )

    @workflow.run
    async def run(self, input: IngestionInput) -> IngestionResult:
        """Execute the ingestion workflow.

        Args:
            input: Ingestion input parameters

        Returns:
            Ingestion result with statistics
        """
        # Initialize status
        self._current_status.codebase_id = input.codebase_id
        await self._update_status("validating", 0.05, 0, 0, 0, "Validating codebase source...")

        # Log workflow start
        logger.info(
            "ingestion_workflow_started",
            codebase_id=str(input.codebase_id),
            source_type=input.source_type,
            source_url=input.source_url,
            has_file_data=input.file_data is not None,
        )

        try:
            # Step 1: Validate codebase
            logger.info(
                "ingestion_stage_validation",
                codebase_id=str(input.codebase_id),
                stage="validation",
                message="Starting codebase validation",
            )
            await self._update_status("validating", 0.1, 0, 0, 0, "Validating codebase source...")
            await workflow.execute_activity(
                "validate_codebase",
                args=[input.codebase_id, input.source_type, input.source_url, input.file_data],
                start_to_close_timeout=timedelta(seconds=60),
            )
            logger.info(
                "ingestion_stage_validation_complete",
                codebase_id=str(input.codebase_id),
                stage="validation",
                message="Codebase validation successful",
            )

            # Step 2: Clone or extract
            logger.info(
                "ingestion_stage_extraction_start",
                codebase_id=str(input.codebase_id),
                stage="extraction",
                message="Starting repository clone or archive extraction",
            )
            await self._update_status(
                "extracting",
                0.15,
                0,
                0,
                0,
                0,
                {},
                "Cloning repository or extracting archive...",
            )
            extracted = await workflow.execute_activity(
                "clone_or_extract",
                args=[input.codebase_id, input.source_type, input.source_url, input.file_data],
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=2),
                    backoff_coefficient=2.0,
                    maximum_interval=timedelta(seconds=30),
                    maximum_attempts=3,
                ),
            )

            files = extracted["files"]
            files_total = len(files)

            logger.info(
                "ingestion_stage_extraction_complete",
                codebase_id=str(input.codebase_id),
                stage="extraction",
                message="Repository cloned or archive extracted successfully",
                files_total=files_total,
            )

            # Step 3: Parse codebase
            logger.info(
                "ingestion_stage_parsing_start",
                codebase_id=str(input.codebase_id),
                stage="parsing",
                message="Starting code parsing and chunking",
                files_total=files_total,
            )
            await self._update_status(
                "parsing",
                0.35,
                0,
                files_total,
                0,
                0,
                {},
                "Parsing code files...",
            )
            parsed = await workflow.execute_activity(
                "parse_codebase",
                args=[input.codebase_id, files],
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=2),
                    backoff_coefficient=2.0,
                    maximum_interval=timedelta(seconds=30),
                    maximum_attempts=3,
                ),
            )

            files_processed = parsed.get("supported_files", 0)
            chunks_count = parsed.get("chunks_created", 0)

            logger.info(
                "ingestion_stage_parsing_complete",
                codebase_id=str(input.codebase_id),
                stage="parsing",
                message="Code parsing and chunking complete",
                files_processed=files_processed,
                chunks_created=chunks_count,
            )

            # Parsing complete, update status which serves as intermediate progress save
            await self._update_status(
                "parsing",
                0.5,
                files_processed,
                files_total,
                chunks_count,
                0,
                {},
                "Code parsing and chunking complete",
            )

            # Step 4: Scan for secrets (security check) - AFTER parsing
            logger.info(
                "ingestion_stage_secret_scanning_start",
                codebase_id=str(input.codebase_id),
                stage="secret_scanning",
                message="Starting secret detection scan",
            )
            await self._update_status(
                "scanning_secrets",
                0.5,
                files_processed,
                files_total,
                chunks_count,
                0,
                {},
                "Scanning for secrets...",
            )
            secret_scan = await workflow.execute_activity(
                "scan_for_secrets_activity",
                args=[input.codebase_id, files],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=2),
                    backoff_coefficient=2.0,
                    maximum_interval=timedelta(seconds=30),
                    maximum_attempts=3,
                ),
            )

            secrets_found = secret_scan["total_secrets"]
            secrets_summary = secret_scan["secrets_summary"]

            logger.info(
                "ingestion_stage_secret_scanning_complete",
                codebase_id=str(input.codebase_id),
                stage="secret_scanning",
                message="Secret detection scan complete",
                secrets_found=secrets_found,
                files_with_secrets=len(secrets_summary),
            )

            # Emit secret detection status
            await self._update_status(
                "scanning_secrets",
                0.6,
                files_processed,
                files_total,
                chunks_count,
                secrets_found,
                secrets_summary,
                f"Found {secrets_found} potential secret(s) - see summary for details",
            )

            # Note: Embeddings and indexing are handled within parse_codebase activity
            # The process_codebase method generates embeddings and stores in vector DB

            logger.info(
                "ingestion_stage_embedding_indexing",
                codebase_id=str(input.codebase_id),
                stage="embedding_indexing",
                message="Embeddings and indexing completed within parsing stage",
                chunks_count=chunks_count,
            )

            # Final status - completed
            logger.info(
                "ingestion_workflow_completed",
                codebase_id=str(input.codebase_id),
                stage="completed",
                message="Ingestion workflow completed successfully",
                files_processed=files_processed,
                chunks_created=chunks_count,
                secrets_found=secrets_found,
            )

            await self._update_status(
                "completed",
                1.0,
                files_processed,
                files_total,
                chunks_count,
                secrets_found,
                secrets_summary,
                f"Ingestion complete: {files_processed} files, {chunks_count} chunks, {secrets_found} secret(s) found",
            )

            return IngestionResult(
                status="completed",
                chunks_created=chunks_count,
                files_processed=files_processed,
                secrets_found=secrets_found,
                secrets_summary=secrets_summary,
            )

        except Exception as e:
            # Log error
            logger.error(
                "ingestion_workflow_failed",
                codebase_id=str(input.codebase_id),
                stage="failed",
                error=str(e),
                error_type=type(e).__name__,
                progress=self._current_status.progress,
            )

            # Update status to failed
            await self._update_status(
                "failed",
                self._current_status.progress,
                self._current_status.files_processed,
                self._current_status.files_total,
                self._current_status.chunks_created,
                self._current_status.secrets_found,
                self._current_status.secrets_summary,
                "",
                str(e),
            )

            raise ApplicationError(f"Ingestion failed: {str(e)}") from e

    @workflow.query
    def get_status(self) -> IngestionStatus:
        """Query the current workflow status.

        Returns:
            Current ingestion status
        """
        return self._current_status

    async def _update_status(
        self,
        step: str,
        progress: float,
        files_processed: int,
        files_total: int,
        chunks_created: int,
        secrets_found: int,
        secrets_summary: dict[str, dict[str, int]] | None = None,
        message: str = "",
        error: str | None = None,
    ) -> None:
        """Update the current workflow status and sync to database.

        Args:
            step: Current workflow step
            progress: Progress value (0.0 to 1.0)
            files_processed: Number of files processed
            files_total: Total number of files
            chunks_created: Number of chunks created
            secrets_found: Number of secrets found
            secrets_summary: Summary of secrets by file and type
            message: Status message
            error: Error message if step failed
        """
        self._current_status = IngestionStatus(
            codebase_id=self._current_status.codebase_id,
            step=step,
            progress=progress,
            files_processed=files_processed,
            files_total=files_total,
            chunks_created=chunks_created,
            secrets_found=secrets_found,
            secrets_summary=secrets_summary or {},
            message=message,
            error=error,
        )

        # Determine DB status
        db_status = "processing"
        if step == "completed":
            db_status = "completed"
        elif step == "failed":
            db_status = "failed"
        elif step == "initializing":
            db_status = "queued"

        # Update DB status
        await workflow.execute_activity(
            "update_codebase_status_activity",
            args=[
                self._current_status.codebase_id,
                db_status,
                files_processed,
                files_total,
                error,
            ],
            start_to_close_timeout=timedelta(seconds=10),
        )
