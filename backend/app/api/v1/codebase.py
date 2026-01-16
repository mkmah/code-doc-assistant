"""Codebase management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import limiter
from app.db.session import get_db
from app.models.db.codebase import CodebaseStatus as DBCodebaseStatus
from app.models.db.codebase import SourceType as DBSourceType
from app.models.schemas import (
    Codebase,
    CodebaseListResponse,
    CodebaseStatus,
    IngestionStatus,
    SourceType,
    UploadResponse,
)
from app.repositories.codebase_repository import CodebaseRepository
from app.services.codebase_processor import (
    FileSizeExceededError,
    InvalidFileError,
    get_codebase_processor,
)
from app.services.redis_session_store import get_redis_session_store
from app.services.vector_store import get_vector_store

settings = get_settings()
logger = get_logger(__name__)
router = APIRouter()
codebase_processor = get_codebase_processor()
redis_store = get_redis_session_store()
vector_store = get_vector_store()

# Temporal client singleton (lazily initialized)
_temporal_client: Client | None = None


async def get_temporal_client() -> Client:
    """Get or create Temporal client connection."""
    global _temporal_client
    if _temporal_client is None:
        _temporal_client = await Client.connect(settings.temporal_url)
    return _temporal_client


def _to_schema_status(status: DBCodebaseStatus) -> CodebaseStatus:
    """Convert DB status to schema status."""
    return CodebaseStatus(status.value)


def _to_schema_source_type(source_type: DBSourceType) -> SourceType:
    """Convert DB source type to schema source type."""
    return SourceType(source_type.value)


def _to_db_source_type(source_type: SourceType) -> DBSourceType:
    """Convert schema source type to DB source type."""
    return DBSourceType(source_type.value)


def _to_db_status(status: CodebaseStatus) -> DBCodebaseStatus:
    """Convert schema status to DB status."""
    return DBCodebaseStatus(status.value)


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("100/hour")
async def upload_codebase(
    request: Request,  # For rate limiting
    name: str = Form(..., min_length=1, max_length=100),
    description: str | None = Form(None, max_length=500),
    file: UploadFile | None = File(None),
    repository_url: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload a codebase for processing.

    Accepts either a ZIP/tar.gz file or a GitHub repository URL.
    The system will parse the code, generate embeddings, and index it.

    Rate limited to 100 requests per hour per IP address.

    Args:
        name: Human-readable codebase name
        description: Optional description
        file: ZIP or tar.gz archive (max 100MB)
        repository_url: GitHub repository URL (alternative to file)
        db: Async database session

    Returns:
        UploadResponse with codebase_id and workflow_id

    Raises:
        HTTPException: If request is invalid
    """
    repo = CodebaseRepository(db)

    # Validate that exactly one source is provided
    if not file and not repository_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either file or repository_url must be provided",
        )

    if file and repository_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only one of file or repository_url should be provided",
        )

    # Determine source type and validate
    source_type: SourceType
    size_bytes = 0

    if file:
        source_type = SourceType.ZIP

        # Read file content
        content = await file.read()
        size_bytes = len(content)

        # Validate file size
        if size_bytes > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds {settings.max_file_size_bytes} bytes",
            )

        # Validate file type
        if file.filename:
            filename_lower = file.filename.lower()
            if not (filename_lower.endswith(".zip") or filename_lower.endswith(".tar.gz")):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only ZIP and tar.gz files are supported",
                )

        # Create codebase record first to get the ID
        codebase = await repo.create(
            name=name,
            description=description,
            source_type=_to_db_source_type(source_type),
            source_url=None,
            size_bytes=size_bytes,
            workflow_id="",  # Will be set after workflow starts
        )

        logger.info(
            "file_upload_received",
            codebase_id=str(codebase.id),
            name=name,
            filename=file.filename,
            size_bytes=size_bytes,
        )

        # Save file to storage (validates ZIP format)
        try:
            file_path = await codebase_processor.save_file(codebase.id, content)
            logger.info(
                "file_saved_to_storage",
                codebase_id=str(codebase.id),
                file_path=file_path,
            )
        except FileSizeExceededError as e:
            await repo.update_status(codebase.id, DBCodebaseStatus.FAILED, error_message=str(e))
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=str(e),
            )
        except InvalidFileError as e:
            await repo.update_status(codebase.id, DBCodebaseStatus.FAILED, error_message=str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    else:
        source_type = SourceType.GITHUB_URL

        # Create codebase record
        codebase = await repo.create(
            name=name,
            description=description,
            source_type=_to_db_source_type(source_type),
            source_url=repository_url,
            size_bytes=0,
            workflow_id="",
        )

        logger.info(
            "github_url_received",
            codebase_id=str(codebase.id),
            name=name,
            repository_url=repository_url,
        )

    # Trigger Temporal workflow
    try:
        client = await get_temporal_client()

        # Import workflow and input models
        from app.types import IngestionInput
        from app.workflows.ingestion_workflow import IngestionWorkflow

        # Prepare workflow input
        workflow_input = IngestionInput(
            codebase_id=codebase.id,
            source_type=source_type.value,
            source_url=repository_url if source_type == SourceType.GITHUB_URL else None,
            file_data=content if file else None,
        )

        # Start workflow
        workflow_id = f"ingestion-{codebase.id}"
        await client.start_workflow(
            IngestionWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue="code-ingestion-task-queue",
        )

        # Update codebase with workflow ID
        await repo.update_workflow_id(codebase.id, workflow_id)

        logger.info(
            "temporal_workflow_started",
            codebase_id=str(codebase.id),
            workflow_id=workflow_id,
        )

    except Exception as e:
        # Update codebase status to failed
        await repo.update_status(codebase.id, DBCodebaseStatus.FAILED, error_message=str(e))
        logger.exception(
            "workflow_start_failed",
            codebase_id=str(codebase.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start ingestion workflow: {str(e)}",
        )

    # Return upload response
    return UploadResponse(
        codebase_id=codebase.id,
        status=_to_schema_status(codebase.status),
        workflow_id=workflow_id,
    )


@router.get("", response_model=CodebaseListResponse)
async def list_codebases(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List all uploaded codebases.

    Args:
        page: Page number (1-indexed)
        limit: Items per page (max 100)
        db: Async database session

    Returns:
        Paginated list of codebases
    """
    if limit > 100:
        limit = 100

    repo = CodebaseRepository(db)
    codebases, total = await repo.list_codebases(page=page, limit=limit)

    # Convert DB models to schema models
    schema_codebases = []
    for cb in codebases:
        schema_codebases.append(
            Codebase(
                id=cb.id,
                name=cb.name,
                description=cb.description,
                source_type=_to_schema_source_type(cb.source_type),
                source_url=cb.source_url,
                status=_to_schema_status(cb.status),
                total_files=cb.total_files,
                processed_files=cb.processed_files,
                primary_language=cb.primary_language,
                all_languages=cb.all_languages,
                size_bytes=cb.size_bytes,
                error_message=cb.error_message,
                workflow_id=cb.workflow_id,
                secrets_detected=cb.secrets_detected,
                created_at=cb.created_at,
                updated_at=cb.updated_at,
            )
        )

    return CodebaseListResponse(
        codebases=schema_codebases,
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{codebase_id}", response_model=Codebase)
async def get_codebase(
    codebase_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific codebase.

    Args:
        codebase_id: Codebase ID
        db: Async database session

    Returns:
        Codebase details

    Raises:
        HTTPException: If codebase not found
    """
    repo = CodebaseRepository(db)
    codebase = await repo.get(codebase_id)
    if not codebase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Codebase not found",
        )

    return Codebase(
        id=codebase.id,
        name=codebase.name,
        description=codebase.description,
        source_type=_to_schema_source_type(codebase.source_type),
        source_url=codebase.source_url,
        status=_to_schema_status(codebase.status),
        total_files=codebase.total_files,
        processed_files=codebase.processed_files,
        primary_language=codebase.primary_language,
        all_languages=codebase.all_languages,
        size_bytes=codebase.size_bytes,
        error_message=codebase.error_message,
        workflow_id=codebase.workflow_id,
        secrets_detected=codebase.secrets_detected,
        created_at=codebase.created_at,
        updated_at=codebase.updated_at,
    )


@router.get("/{codebase_id}/status", response_model=IngestionStatus)
async def get_codebase_status(
    codebase_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the ingestion status of a codebase.

    Args:
        codebase_id: Codebase ID
        db: Async database session

    Returns:
        Current ingestion status

    Raises:
        HTTPException: If codebase not found
    """
    repo = CodebaseRepository(db)
    codebase = await repo.get(codebase_id)
    if not codebase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Codebase not found",
        )

    # Calculate progress
    progress = 0.0
    if codebase.total_files > 0:
        progress = (codebase.processed_files / codebase.total_files) * 100

    # Determine current step based on status
    step_map: dict[DBCodebaseStatus, str | None] = {
        DBCodebaseStatus.QUEUED: "validating",
        DBCodebaseStatus.PROCESSING: "parsing",  # Simplified for MVP
        DBCodebaseStatus.COMPLETED: "complete",
        DBCodebaseStatus.FAILED: None,
    }

    current_step = step_map.get(codebase.status)

    return IngestionStatus(
        codebase_id=codebase.id,
        status=_to_schema_status(codebase.status),
        progress=progress,
        total_files=codebase.total_files,
        processed_files=codebase.processed_files,
        current_step=current_step,  # type: ignore
        error=codebase.error_message,
        secrets_detected=None,  # TODO: Track from secret detection results
        started_at=codebase.created_at if codebase.status != DBCodebaseStatus.QUEUED else None,
        completed_at=codebase.updated_at if codebase.status == DBCodebaseStatus.COMPLETED else None,
    )


@router.delete("/{codebase_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_codebase(
    codebase_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a codebase and all associated data.

    Performs complete cleanup including:
    - Deleting chunks from ChromaDB vector store
    - Cleaning up all associated sessions
    - Deleting local files
    - Cancelling active Temporal workflows
    - Deleting database record

    Args:
        codebase_id: Codebase ID to delete
        db: Async database session

    Raises:
        HTTPException: If codebase not found
    """
    repo = CodebaseRepository(db)

    # Get codebase first to check if it exists and get its metadata
    codebase = await repo.get(codebase_id)
    if not codebase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Codebase not found",
        )

    try:
        # Step 1: Delete from ChromaDB vector store
        logger.info("deleting_codebase_from_vector_store", codebase_id=str(codebase_id))
        await vector_store.delete_codebase(codebase_id)

        # Step 2: Clean up sessions from Redis
        logger.info("deleting_codebase_sessions", codebase_id=str(codebase_id))
        sessions_deleted = await redis_store.delete_sessions_by_codebase(codebase_id)
        logger.info("sessions_deleted", count=sessions_deleted, codebase_id=str(codebase_id))

        # Step 3: Delete local files
        if codebase.storage_path:
            try:
                logger.info("deleting_codebase_files", path=codebase.storage_path)
                await codebase_processor.delete_file(codebase_id)
                logger.info("files_deleted", codebase_id=str(codebase_id))
            except FileNotFoundError:
                # File might have already been deleted or never existed
                logger.warning("file_not_found_during_deletion", path=codebase.storage_path)
            except Exception as e:
                # Log error but continue with deletion
                logger.error("file_deletion_failed", path=codebase.storage_path, error=str(e))

        # Step 4: Cancel active Temporal workflow if processing
        if codebase.workflow_id and codebase.status == DBCodebaseStatus.PROCESSING:
            try:
                logger.info("canceling_workflow", workflow_id=codebase.workflow_id)
                temporal_client = await get_temporal_client()
                workflow_handle = temporal_client.get_workflow_handle(codebase.workflow_id)
                await workflow_handle.cancel()
                logger.info("workflow_cancelled", workflow_id=codebase.workflow_id)
            except Exception as e:
                # Log error but continue - workflow might have already completed
                logger.warning(
                    "workflow_cancellation_failed", workflow_id=codebase.workflow_id, error=str(e)
                )

        # Step 5: Delete codebase record from database (do this last)
        deleted = await repo.delete(codebase_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Codebase not found",
            )

        logger.info("codebase_deleted", codebase_id=str(codebase_id))

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log and wrap other exceptions
        logger.error("codebase_deletion_failed", codebase_id=str(codebase_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete codebase: {str(e)}",
        )

    return None
