"""Codebase processing service for file storage, parsing, chunking, and embedding."""

import asyncio
import io
import os
import zipfile
from pathlib import Path
from uuid import UUID, uuid4

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import SecretDetector
from app.models.schemas import CodeChunk
from app.services.embedding_service import get_embedding_service
from app.services.vector_store import get_vector_store
from app.utils.chunking import get_code_chunker
from app.utils.code_parser import get_code_parser

logger = get_logger(__name__)
settings = get_settings()
embedding_service = get_embedding_service()
vector_store = get_vector_store()


class FileSizeExceededError(Exception):
    """Raised when uploaded file exceeds size limit."""

    pass


class InvalidFileError(Exception):
    """Raised when uploaded file is invalid (corrupted, wrong format, etc.)."""

    pass


class CodebaseProcessor:
    """Orchestrates codebase processing pipeline.

    Features:
    - File storage with size validation
    - ZIP file validation
    - Parse code files with Tree-sitter
    - Detect and redact secrets
    - Chunk code semantically
    - Generate embeddings
    - Store in vector database
    """

    def __init__(self) -> None:
        """Initialize the processor."""
        self._parser = get_code_parser()
        self._chunker = get_code_chunker()
        self._secret_detector = SecretDetector()
        self._storage_path = Path(settings.storage_path)
        self._ensure_storage_directory()

    def _ensure_storage_directory(self) -> None:
        """Ensure storage directory exists."""
        self._storage_path.mkdir(parents=True, exist_ok=True)

    # ==========================================================================
    # File Storage Operations
    # ==========================================================================

    async def save_file(self, codebase_id: UUID, content: bytes) -> str:
        """Save uploaded file content to storage.

        Uses asyncio.to_thread() to avoid blocking the event loop during file I/O.

        Args:
            codebase_id: Unique identifier for the codebase
            content: File content (ZIP archive bytes)

        Returns:
            Absolute path to saved file

        Raises:
            FileSizeExceededError: If file size exceeds limit
            InvalidFileError: If file is invalid (corrupted, empty, etc.)
        """
        # Validate file size
        if len(content) > settings.max_file_size_bytes:
            logger.warning(
                "file_size_exceeded",
                codebase_id=str(codebase_id),
                size_bytes=len(content),
                max_bytes=settings.max_file_size_bytes,
            )
            raise FileSizeExceededError(
                f"File size ({len(content)} bytes) exceeds maximum "
                f"allowed size ({settings.max_file_size_bytes} bytes)"
            )

        # Validate file is not empty
        if len(content) == 0:
            raise InvalidFileError("File is empty")

        # Validate ZIP format
        if not self.is_valid_zip_file(content):
            raise InvalidFileError("File is not a valid ZIP archive")

        # Generate file path
        file_path = self._get_file_path(codebase_id)

        try:
            # Ensure directory exists (non-blocking)
            await asyncio.to_thread(file_path.parent.mkdir, parents=True, exist_ok=True)

            # Write file to disk in a thread pool to avoid blocking event loop
            def _write_file() -> str:
                with open(file_path, "wb") as f:
                    f.write(content)
                return str(file_path)

            result_path = await asyncio.to_thread(_write_file)

            logger.info(
                "file_saved",
                codebase_id=str(codebase_id),
                file_path=result_path,
                size_bytes=len(content),
            )

            return result_path

        except Exception as e:
            logger.error(
                "file_save_failed",
                codebase_id=str(codebase_id),
                error=str(e),
            )
            raise

    async def delete_file(self, codebase_id: UUID) -> bool:
        """Delete stored file for a codebase.

        Uses asyncio.to_thread() to avoid blocking the event loop during file I/O.

        Args:
            codebase_id: Codebase ID whose file should be deleted

        Returns:
            True if file was deleted, False if not found
        """
        file_path = self._get_file_path(codebase_id)

        # Check if file exists (non-blocking)
        file_exists = await asyncio.to_thread(file_path.exists)
        if not file_exists:
            return False

        try:
            # Delete file in a thread pool to avoid blocking event loop
            await asyncio.to_thread(file_path.unlink)
            logger.info(
                "file_deleted",
                codebase_id=str(codebase_id),
                file_path=str(file_path),
            )
            return True

        except Exception as e:
            logger.error(
                "file_deletion_failed",
                codebase_id=str(codebase_id),
                error=str(e),
            )
            return False

    async def get_file_path(self, codebase_id: UUID) -> str | None:
        """Get the path to a stored file.

        Uses asyncio.to_thread() to avoid blocking the event loop during file I/O.

        Args:
            codebase_id: Codebase ID to look up

        Returns:
            Absolute file path, or None if not found
        """
        file_path = self._get_file_path(codebase_id)

        # Check if file exists (non-blocking)
        file_exists = await asyncio.to_thread(file_path.exists)
        if file_exists:
            return str(file_path)

        return None

    async def get_file_size(self, codebase_id: UUID) -> int:
        """Get the size of a stored file.

        Uses asyncio.to_thread() to avoid blocking the event loop during file I/O.

        Args:
            codebase_id: Codebase ID to look up

        Returns:
            File size in bytes, or 0 if not found
        """
        file_path = self._get_file_path(codebase_id)

        def _get_size() -> int:
            if file_path.exists():
                return file_path.stat().st_size
            return 0

        return await asyncio.to_thread(_get_size)

    async def list_files(self, codebase_id: UUID) -> list[str]:
        """List all files within a codebase ZIP archive.

        Uses asyncio.to_thread() to avoid blocking the event loop during ZIP I/O.

        Args:
            codebase_id: Codebase ID to list files for

        Returns:
            List of file paths within the archive
        """
        file_path = self._get_file_path(codebase_id)

        # Check if file exists (non-blocking)
        file_exists = await asyncio.to_thread(file_path.exists)
        if not file_exists:
            return []

        try:
            # List ZIP contents in a thread pool to avoid blocking event loop
            def _list_zip() -> list[str]:
                with zipfile.ZipFile(file_path, "r") as zip_file:
                    return zip_file.namelist()

            return await asyncio.to_thread(_list_zip)

        except Exception as e:
            logger.error(
                "file_list_failed",
                codebase_id=str(codebase_id),
                error=str(e),
            )
            return []

    def is_valid_zip_file(self, content: bytes) -> bool:
        """Validate that content is a valid ZIP file.

        Args:
            content: File content to validate

        Returns:
            True if valid ZIP, False otherwise
        """
        try:
            # Check for ZIP file signature
            if not content.startswith(b"PK\x03\x04") and not content.startswith(b"PK\x05\x06"):
                return False

            # Try to parse as ZIP
            with zipfile.ZipFile(io.BytesIO(content), "r") as zip_file:
                pass  # Just opening is enough to validate

            return True

        except Exception:
            return False

    def is_safe_filename(self, filename: str) -> bool:
        """Check if a filename is safe (no path traversal, etc.).

        Args:
            filename: Filename to validate

        Returns:
            True if safe, False otherwise
        """
        # Reject absolute paths
        if os.path.isabs(filename):
            return False

        # Reject path traversal attempts
        if ".." in filename or filename.startswith("./"):
            return False

        # Reject filenames with spaces (potential issues)
        if " " in filename:
            return False

        # Only allow safe characters
        safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
        return all(c in safe_chars for c in filename)

    def _get_file_path(self, codebase_id: UUID) -> Path:
        """Get the storage path for a codebase file.

        Args:
            codebase_id: Codebase ID

        Returns:
            Path to file storage location
        """
        # Store as: storage_path/codebase_id.zip
        return self._storage_path / f"{codebase_id}.zip"

    async def process_codebase(
        self,
        codebase_id: UUID,
        files: dict[str, str],  # file_path -> content
    ) -> dict[str, any]:
        """Process a complete codebase.

        This method handles file operations only (parsing, chunking, embedding).
        Status updates should be handled by the calling Temporal workflow.

        Args:
            codebase_id: Codebase ID
            files: Dictionary of file paths to content

        Returns:
            Processing result with statistics including:
            - chunks_created: Number of code chunks created
            - supported_files: Number of successfully processed files
            - unsupported_files: Number of skipped files (unsupported language)
            - secrets_found: Number of secrets detected
            - primary_language: Most common language in the codebase
            - all_languages: Set of all languages detected
        """
        all_chunks = []
        supported_files = 0
        unsupported_files = 0
        secrets_found = 0

        logger.info(
            "processing_codebase",
            codebase_id=str(codebase_id),
            total_files=len(files),
        )

        for file_path, content in files.items():
            try:
                # Check if language is supported
                language = self._parser.detect_language(file_path)
                if not language:
                    unsupported_files += 1
                    continue

                # Detect and redact secrets
                from app.core.config import get_settings

                app_settings = get_settings()

                if app_settings.enable_secret_detection:
                    redacted_content, scan_result = self._secret_detector.redact(content)
                    if scan_result.has_secrets:
                        secrets_found += scan_result.secret_count
                        logger.warning(
                            "secrets_detected",
                            file_path=file_path,
                            count=scan_result.secret_count,
                        )
                    content = redacted_content

                # Parse code
                parsed = self._parser.parse_file(file_path, content)

                # Chunk code
                chunks = self._chunker.chunk_parsed_code(parsed, content)

                # Convert to internal CodeChunk model
                for chunk in chunks:
                    code_chunk = CodeChunk(
                        id=uuid4(),
                        codebase_id=codebase_id,
                        file_path=file_path,
                        line_start=chunk.line_start,
                        line_end=chunk.line_end,
                        content=chunk.content,
                        language=chunk.language,
                        chunk_type=chunk.chunk_type,
                        name=chunk.name,
                        docstring=chunk.docstring,
                        dependencies=chunk.dependencies,
                        parent_class=chunk.parent_class,
                        complexity=chunk.complexity,
                        embedding=None,  # Will be set in batch
                        metadata=chunk.metadata or {},
                    )
                    all_chunks.append(code_chunk)

                supported_files += 1

                logger.debug(
                    "file_processed",
                    file_path=file_path,
                    chunks_count=len(chunks),
                )

            except Exception as e:
                logger.error(
                    "file_processing_failed",
                    file_path=file_path,
                    error=str(e),
                )
                unsupported_files += 1

        # Generate embeddings for all chunks
        if all_chunks:
            logger.info("generating_embeddings", chunks_count=len(all_chunks))

            await vector_store.add_chunks(all_chunks)

        # Calculate language statistics
        languages_list = [chunk.language for chunk in all_chunks]
        all_languages = set(languages_list)
        primary_language = max(all_languages, key=languages_list.count) if all_languages else None

        logger.info(
            "codebase_processing_complete",
            codebase_id=str(codebase_id),
            chunks_created=len(all_chunks),
            supported_files=supported_files,
            unsupported_files=unsupported_files,
            secrets_found=secrets_found,
            primary_language=primary_language,
        )

        return {
            "codebase_id": codebase_id,
            "chunks_created": len(all_chunks),
            "supported_files": supported_files,
            "unsupported_files": unsupported_files,
            "secrets_found": secrets_found,
            "primary_language": primary_language,
            "all_languages": list(all_languages),
        }


# Singleton instance
_processor: CodebaseProcessor | None = None


def get_codebase_processor() -> CodebaseProcessor:
    """Get the singleton codebase processor instance."""
    global _processor
    if _processor is None:
        _processor = CodebaseProcessor()
    return _processor
