"""Temporal activities for code parsing."""

from datetime import timedelta
from pathlib import Path
from uuid import UUID

import git
from temporalio import activity

from app.core.logging import get_logger
from app.services.codebase_processor import get_codebase_processor

logger = get_logger(__name__)


@activity.defn
async def validate_codebase(
    codebase_id: UUID,
    source_type: str,
    source_url: str | None,
    file_data: bytes | None,
) -> dict:
    """Validate codebase source before processing.

    Args:
        codebase_id: Codebase ID
        source_type: Type of source ("zip" or "github_url")
        source_url: GitHub URL if applicable
        file_data: Uploaded file data if applicable

    Returns:
        Validation result
    """
    # Validate file size (100MB limit)
    max_size = 100 * 1024 * 1024  # 100MB

    if source_type == "zip" and file_data:
        if len(file_data) > max_size:
            raise ValueError(f"File size exceeds {max_size} bytes")

        # Validate file is a valid ZIP
        import zipfile

        try:
            with zipfile.ZipFile(file_data) as zf:
                file_list = zf.namelist()
                if not file_list:
                    raise ValueError("ZIP archive is empty")
        except Exception as e:
            raise ValueError(f"Invalid ZIP file: {e}")

    elif source_type == "github_url" and source_url:
        # Validate GitHub URL format is already done in the API
        # Additional validation could check if repo exists
        pass

    else:
        raise ValueError("Invalid source type")

    logger.info(
        "codebase_validated",
        codebase_id=str(codebase_id),
        source_type=source_type,
    )

    return {"valid": True}


@activity.defn
async def clone_or_extract(
    codebase_id: UUID,
    source_type: str,
    source_url: str | None,
    file_data: bytes | None,
) -> dict:
    """Clone repository or extract archive.

    Args:
        codebase_id: Codebase ID
        source_type: Type of source
        source_url: GitHub URL if applicable
        file_data: Uploaded file data if applicable

    Returns:
        Extracted files mapping (path -> content)
    """
    files = {}

    if source_type == "github_url" and source_url:
        # Clone repository using gitpython
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir) / "repo"
            git.Repo.clone_from(source_url, repo_dir)

            # Read all files
            for file_path in repo_dir.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(repo_dir)
                    try:
                        content = file_path.read_text(encoding="utf-8")
                        files[str(relative_path)] = content
                    except Exception:
                        # Skip binary files
                        pass

    elif source_type == "zip" and file_data:
        import io
        import zipfile

        with zipfile.ZipFile(io.BytesIO(file_data)) as zf:
            for file_info in zf.filelist:
                if not file_info.is_dir():
                    try:
                        content = zf.read(file_info).decode("utf-8")
                        files[file_info.filename] = content
                    except Exception:
                        # Skip binary files
                        pass

    logger.info(
        "codebase_extracted",
        codebase_id=str(codebase_id),
        files_count=len(files),
    )

    return {"files": files}


@activity.defn
async def parse_codebase(codebase_id: UUID, files: dict[str, str]) -> dict:
    """Parse code files using the codebase processor.

    Args:
        codebase_id: Codebase ID
        files: Mapping of file paths to content

    Returns:
        Parse result
    """
    processor = get_codebase_processor()

    result = await processor.process_codebase(codebase_id, files)

    logger.info(
        "codebase_parsed",
        codebase_id=str(codebase_id),
        result=result,
    )

    return result
