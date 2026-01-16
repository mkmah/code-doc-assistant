"""Async repository for Codebase database operations."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.db.codebase import Codebase, CodebaseStatus, SourceType

logger = get_logger(__name__)


class CodebaseRepository:
    """Async repository for Codebase database operations.

    Replaces the in-memory CodebaseStore with persistent PostgreSQL storage.
    All operations are async for non-blocking database access.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with async database session.

        Args:
            db: Async SQLAlchemy session
        """
        self.db = db

    async def create(
        self,
        name: str,
        description: str | None,
        source_type: SourceType,
        source_url: str | None,
        size_bytes: int,
        workflow_id: str,
    ) -> Codebase:
        """Create a new codebase record.

        Args:
            name: Codebase name
            description: Optional description
            source_type: ZIP or GITHUB_URL
            source_url: GitHub URL if applicable
            size_bytes: Upload size in bytes
            workflow_id: Temporal workflow ID

        Returns:
            Created Codebase model instance
        """
        codebase = Codebase(
            name=name,
            description=description,
            source_type=source_type,
            source_url=source_url,
            size_bytes=size_bytes,
            workflow_id=workflow_id,
            status=CodebaseStatus.QUEUED,
        )

        self.db.add(codebase)
        await self.db.flush()
        await self.db.refresh(codebase)

        logger.info(
            "codebase_created",
            codebase_id=str(codebase.id),
            name=name,
            source_type=source_type.value,
        )

        return codebase

    async def get(self, codebase_id: UUID) -> Codebase | None:
        """Get codebase by ID.

        Args:
            codebase_id: Codebase UUID

        Returns:
            Codebase model instance or None if not found
        """
        result = await self.db.execute(select(Codebase).filter(Codebase.id == codebase_id))
        return result.scalar_one_or_none()

    async def update_status(
        self,
        codebase_id: UUID,
        status: CodebaseStatus,
        processed_files: int | None = None,
        total_files: int | None = None,
        primary_language: str | None = None,
        all_languages: list[str] | None = None,
        error_message: str | None = None,
    ) -> Codebase | None:
        """Update codebase status and related fields.

        Args:
            codebase_id: Codebase UUID
            status: New status
            processed_files: Optional processed file count
            total_files: Optional total file count
            primary_language: Optional primary language
            all_languages: Optional list of all languages
            error_message: Optional error message

        Returns:
            Updated Codebase model instance or None if not found
        """
        codebase = await self.get(codebase_id)
        if not codebase:
            return None

        if status is not None:
            codebase.status = status
        if processed_files is not None:
            codebase.processed_files = processed_files
        if total_files is not None:
            codebase.total_files = total_files
        if primary_language is not None:
            codebase.primary_language = primary_language
        if all_languages is not None:
            codebase.all_languages = all_languages
        if error_message is not None:
            codebase.error_message = error_message

        await self.db.flush()
        await self.db.refresh(codebase)

        logger.debug(
            "codebase_status_updated",
            codebase_id=str(codebase_id),
            status=status.value,
            processed_files=processed_files,
        )

        return codebase

    async def update_workflow_id(self, codebase_id: UUID, workflow_id: str) -> Codebase | None:
        """Update workflow ID for a codebase.

        Args:
            codebase_id: Codebase UUID
            workflow_id: Temporal workflow ID

        Returns:
            Updated Codebase model instance or None if not found
        """
        codebase = await self.get(codebase_id)
        if not codebase:
            return None

        codebase.workflow_id = workflow_id
        await self.db.flush()
        await self.db.refresh(codebase)

        logger.debug(
            "codebase_workflow_updated",
            codebase_id=str(codebase_id),
            workflow_id=workflow_id,
        )

        return codebase

    async def list_codebases(
        self,
        page: int = 1,
        limit: int = 20,
        status: CodebaseStatus | None = None,
    ) -> tuple[list[Codebase], int]:
        """List codebases with pagination and optional status filter.

        Args:
            page: Page number (1-indexed)
            limit: Items per page
            status: Optional status filter

        Returns:
            Tuple of (list of Codebases, total count)
        """
        query = select(Codebase)

        if status is not None:
            query = query.filter(Codebase.status == status)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Get paginated results
        offset = (page - 1) * limit
        query = query.order_by(Codebase.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def delete(self, codebase_id: UUID) -> bool:
        """Delete codebase by ID.

        Args:
            codebase_id: Codebase UUID

        Returns:
            True if deleted, False if not found
        """
        codebase = await self.get(codebase_id)
        if not codebase:
            return False

        await self.db.delete(codebase)
        await self.db.flush()

        logger.info("codebase_deleted", codebase_id=str(codebase_id))

        return True
