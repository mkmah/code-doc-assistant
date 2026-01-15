"""Codebase management endpoints."""

import uuid
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import (
    Codebase,
    CodebaseListResponse,
    CodebaseStatus,
    ErrorResponse,
    IngestionStatus,
    SourceType,
    UploadRequest,
    UploadResponse,
)
from app.services.codebase_store import get_codebase_store

settings = get_settings()
logger = get_logger(__name__)
router = APIRouter()
codebase_store = get_codebase_store()


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_codebase(
    name: str = Form(..., min_length=1, max_length=100),
    description: str | None = Form(None, max_length=500),
    file: UploadFile | None = File(None),
    repository_url: str | None = Form(None),
):
    """Upload a codebase for processing.

    Accepts either a ZIP/tar.gz file or a GitHub repository URL.
    The system will parse the code, generate embeddings, and index it.

    Args:
        name: Human-readable codebase name
        description: Optional description
        file: ZIP or tar.gz archive (max 100MB)
        repository_url: GitHub repository URL (alternative to file)

    Returns:
        UploadResponse with codebase_id and workflow_id

    Raises:
        HTTPException: If request is invalid
    """
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

        # Validate file size
        content = await file.read()
        size_bytes = len(content)

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

        # TODO: Save file to storage and trigger workflow
        # For now, just create a placeholder
        logger.info(
            "file_upload_received",
            name=name,
            filename=file.filename,
            size_bytes=size_bytes,
        )

    else:
        source_type = SourceType.GITHUB_URL

        # GitHub URL validation is handled by Pydantic in the model
        logger.info(
            "github_url_received",
            name=name,
            repository_url=repository_url,
        )

    # Create codebase record
    workflow_id = f"workflow-{uuid.uuid4().hex[:8]}"  # Simplified for MVP
    codebase = codebase_store.create(
        name=name,
        description=description,
        source_type=source_type,
        source_url=repository_url,
        size_bytes=size_bytes,
        workflow_id=workflow_id,
    )

    # TODO: Trigger Temporal workflow
    # For now, just mark as queued

    logger.info(
        "codebase_upload_accepted",
        codebase_id=str(codebase.id),
        workflow_id=workflow_id,
    )

    return UploadResponse(
        codebase_id=codebase.id,
        status=CodebaseStatus.QUEUED,
        workflow_id=workflow_id,
    )


@router.get("", response_model=CodebaseListResponse)
async def list_codebases(
    page: int = 1,
    limit: int = 20,
):
    """List all uploaded codebases.

    Args:
        page: Page number (1-indexed)
        limit: Items per page (max 100)

    Returns:
        Paginated list of codebases
    """
    if limit > 100:
        limit = 100

    codebases, total = codebase_store.list_codebases(page=page, limit=limit)

    return CodebaseListResponse(
        codebases=codebases,
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{codebase_id}", response_model=Codebase)
async def get_codebase(codebase_id: UUID):
    """Get details of a specific codebase.

    Args:
        codebase_id: Codebase ID

    Returns:
        Codebase details

    Raises:
        HTTPException: If codebase not found
    """
    codebase = codebase_store.get(codebase_id)
    if not codebase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Codebase not found",
        )

    return codebase


@router.get("/{codebase_id}/status", response_model=IngestionStatus)
async def get_codebase_status(codebase_id: UUID):
    """Get the ingestion status of a codebase.

    Args:
        codebase_id: Codebase ID

    Returns:
        Current ingestion status

    Raises:
        HTTPException: If codebase not found
    """
    codebase = codebase_store.get(codebase_id)
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
    step_map: dict[CodebaseStatus, str | None] = {
        CodebaseStatus.QUEUED: "validating",
        CodebaseStatus.PROCESSING: "parsing",  # Simplified for MVP
        CodebaseStatus.COMPLETED: "complete",
        CodebaseStatus.FAILED: None,
    }

    current_step = step_map.get(codebase.status)

    return IngestionStatus(
        codebase_id=codebase.id,
        status=codebase.status,
        progress=progress,
        total_files=codebase.total_files,
        processed_files=codebase.processed_files,
        current_step=current_step,  # type: ignore
        error=codebase.error_message,
        secrets_detected=None,  # TODO: Track from secret detection results
        started_at=codebase.created_at if codebase.status != CodebaseStatus.QUEUED else None,
        completed_at=codebase.updated_at if codebase.status == CodebaseStatus.COMPLETED else None,
    )


@router.delete("/{codebase_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_codebase(codebase_id: UUID):
    """Delete a codebase and all associated data.

    Args:
        codebase_id: Codebase ID to delete

    Raises:
        HTTPException: If codebase not found
    """
    # TODO: Delete from ChromaDB vector store
    # TODO: Clean up sessions

    deleted = codebase_store.delete(codebase_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Codebase not found",
        )

    logger.info("codebase_deleted", codebase_id=str(codebase_id))

    return None
