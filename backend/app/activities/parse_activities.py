"""Temporal activities for code parsing."""

import io
from datetime import datetime
from pathlib import Path
from uuid import UUID

import git
import structlog
from temporalio import activity

from app.services.codebase_processor import get_codebase_processor
from app.services.secret_scanner import get_secret_scanner

logger = structlog.get_logger(__name__)


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
            with zipfile.ZipFile(io.BytesIO(file_data)) as zf:
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


@activity.defn
async def scan_for_secrets_activity(
    codebase_id: UUID,
    files: dict[str, str],
) -> dict:
    """Scan codebase files for potential secrets.

    This activity scans all code files for secrets (API keys, tokens, passwords, etc.)
    using regex-based pattern matching.

    Retry policy: 3 attempts with exponential backoff (2s, 8s, 30s max)

    Args:
        codebase_id: Codebase ID to scan
        files: Mapping of file paths to content

    Returns:
        Dictionary with:
            - total_secrets: Total number of secrets found
            - secrets_summary: Summary by file and type
            - detections: List of SecretDetectionResult objects
    """
    scanner = get_secret_scanner()

    all_detections = []

    # Scan each file for secrets
    for file_path, content in files.items():
        try:
            # Skip binary files and very large files
            if len(content) > 1_000_000:  # 1MB limit per file
                continue

            # Skip non-text files
            if not content.isprintable() and any(ord(c) > 127 for c in content[:1000]):
                continue

            detections = scanner.scan_code(content, file_path)

            # Update codebase_id for each detection
            for detection in detections:
                detection.codebase_id = codebase_id
                detection.detected_at = datetime.utcnow()

            all_detections.extend(detections)

        except Exception as e:
            logger.warning(
                "secret_scan_failed_for_file",
                file_path=file_path,
                error=str(e),
            )
            # Continue scanning other files even if one fails
            continue

    # Get summary
    secrets_summary = scanner.get_summary(all_detections)

    # Count by secret type
    secret_counts: dict[str, int] = {}
    for detection in all_detections:
        secret_type = detection.secret_type.value
        secret_counts[secret_type] = secret_counts.get(secret_type, 0) + 1

    logger.info(
        "secret_scan_completed",
        codebase_id=str(codebase_id),
        total_secrets=len(all_detections),
        files_with_secrets=len(secrets_summary),
        secret_types=list(secret_counts.keys()),
    )

    return {
        "total_secrets": len(all_detections),
        "secrets_summary": secrets_summary,
        "detections": all_detections,
        "secret_counts": secret_counts,
    }
