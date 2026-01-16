"""Temporal activities for database updates."""

from uuid import UUID

import structlog
from temporalio import activity

from app.db.session import get_db_context
from app.models.db.codebase import CodebaseStatus as DBCodebaseStatus
from app.repositories.codebase_repository import CodebaseRepository

logger = structlog.get_logger(__name__)


@activity.defn
async def update_codebase_status_activity(
    codebase_id: UUID,
    status: str,
    processed_files: int | None = None,
    total_files: int | None = None,
    error: str | None = None,
) -> None:
    """Update codebase status in database.

    Args:
        codebase_id: Codebase ID
        status: New status (QUEUED, PROCESSING, COMPLETED, FAILED)
        processed_files: Number of processed files (optional)
        total_files: Total number of files (optional)
        error: Error message if failed (optional)
    """
    async with get_db_context() as session:
        repo = CodebaseRepository(session)

        # Convert string status to enum
        try:
            db_status = DBCodebaseStatus(status)
        except ValueError:
            logger.error("invalid_status_EnumValue", status=status)
            return

        if processed_files is not None or total_files is not None:
            await repo.update_status(
                codebase_id,
                db_status,
                processed_files=processed_files,
                total_files=total_files,
                error_message=error,
            )
        else:
            await repo.update_status(
                codebase_id,
                db_status,
                error_message=error,
            )

        logger.info(
            "codebase_status_updated",
            codebase_id=str(codebase_id),
            status=status,
            processed_files=processed_files,
            total_files=total_files,
        )
