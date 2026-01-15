"""In-memory codebase store for MVP (single-host deployment).

For production, this should be replaced with PostgreSQL.
"""

from datetime import datetime
from uuid import UUID, uuid4

from app.core.logging import get_logger
from app.models.schemas import Codebase, CodebaseStatus, SourceType

logger = get_logger(__name__)


class CodebaseStore:
    """In-memory store for codebase metadata (MVP).

    Tracks codebase upload status, file counts, and metadata.
    For production with multiple instances, migrate to PostgreSQL.
    """

    def __init__(self) -> None:
        """Initialize the codebase store."""
        # codebase_id -> Codebase
        self._codebases: dict[UUID, Codebase] = {}

    def create(
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
            source_type: Upload source type
            source_url: GitHub URL if applicable
            size_bytes: Upload size in bytes
            workflow_id: Temporal workflow ID

        Returns:
            Created codebase
        """
        codebase_id = uuid4()
        now = datetime.utcnow()

        codebase = Codebase(
            id=codebase_id,
            name=name,
            description=description,
            source_type=source_type,
            source_url=source_url,
            status=CodebaseStatus.QUEUED,
            total_files=0,
            processed_files=0,
            primary_language=None,
            all_languages=None,
            size_bytes=size_bytes,
            error_message=None,
            workflow_id=workflow_id,
            created_at=now,
            updated_at=now,
        )

        self._codebases[codebase_id] = codebase

        logger.info(
            "codebase_created",
            codebase_id=str(codebase_id),
            name=name,
            source_type=source_type.value,
        )

        return codebase

    def get(self, codebase_id: UUID) -> Codebase | None:
        """Get a codebase by ID.

        Args:
            codebase_id: Codebase ID to retrieve

        Returns:
            Codebase if found, None otherwise
        """
        return self._codebases.get(codebase_id)

    def update_status(
        self,
        codebase_id: UUID,
        status: CodebaseStatus,
        processed_files: int | None = None,
        total_files: int | None = None,
        primary_language: str | None = None,
        all_languages: list[str] | None = None,
        error_message: str | None = None,
    ) -> Codebase | None:
        """Update codebase status.

        Args:
            codebase_id: Codebase ID to update
            status: New status
            processed_files: Updated processed file count
            total_files: Updated total file count
            primary_language: Detected primary language
            all_languages: All detected languages
            error_message: Error message if failed

        Returns:
            Updated codebase if found, None otherwise
        """
        codebase = self._codebases.get(codebase_id)
        if not codebase:
            return None

        codebase.status = status
        codebase.updated_at = datetime.utcnow()

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

        logger.info(
            "codebase_updated",
            codebase_id=str(codebase_id),
            status=status.value,
            processed_files=codebase.processed_files,
        )

        return codebase

    def list_codebases(
        self,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Codebase], int]:
        """List all codebases with pagination.

        Args:
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Tuple of (codebases, total_count)
        """
        all_codebases = list(self._codebases.values())
        # Sort by created_at descending
        all_codebases.sort(key=lambda c: c.created_at, reverse=True)

        total = len(all_codebases)
        start = (page - 1) * limit
        end = start + limit

        page_codebases = all_codebases[start:end]

        return page_codebases, total

    def delete(self, codebase_id: UUID) -> bool:
        """Delete a codebase.

        Args:
            codebase_id: Codebase ID to delete

        Returns:
            True if deleted, False if not found
        """
        if codebase_id in self._codebases:
            del self._codebases[codebase_id]
            logger.info("codebase_deleted", codebase_id=str(codebase_id))
            return True
        return False


# Singleton instance
_codebase_store: CodebaseStore | None = None


def get_codebase_store() -> CodebaseStore:
    """Get the singleton codebase store instance."""
    global _codebase_store
    if _codebase_store is None:
        _codebase_store = CodebaseStore()
    return _codebase_store
