"""Codebase processing service orchestrating parsing, chunking, and embedding."""

from uuid import UUID, uuid4

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import SecretDetector
from app.models.schemas import Codebase, CodebaseStatus, CodeChunk
from app.services.codebase_store import get_codebase_store
from app.services.embedding_service import get_embedding_service
from app.services.vector_store import get_vector_store
from app.utils.chunking import CodeChunker, get_code_chunker
from app.utils.code_parser import CodeParser, get_code_parser

logger = get_logger(__name__)
settings = get_settings()
codebase_store = get_codebase_store()
embedding_service = get_embedding_service()
vector_store = get_vector_store()


class CodebaseProcessor:
    """Orchestrates codebase processing pipeline.

    Pipeline:
    1. Parse code files with Tree-sitter
    2. Detect and redact secrets
    3. Chunk code semantically
    4. Generate embeddings
    5. Store in vector database
    """

    def __init__(self) -> None:
        """Initialize the processor."""
        self._parser = get_code_parser()
        self._chunker = get_code_chunker()
        self._secret_detector = SecretDetector()

    async def process_codebase(
        self,
        codebase_id: UUID,
        files: dict[str, str],  # file_path -> content
    ) -> dict[str, any]:
        """Process a complete codebase.

        Args:
            codebase_id: Codebase ID
            files: Dictionary of file paths to content

        Returns:
            Processing result with statistics
        """
        codebase = codebase_store.get(codebase_id)
        if not codebase:
            raise ValueError(f"Codebase {codebase_id} not found")

        # Update status to processing
        codebase_store.update_status(codebase_id, CodebaseStatus.PROCESSING, total_files=len(files))

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
                from app.core.config import settings as app_settings

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

                # Update progress
                codebase_store.update_status(
                    codebase_id,
                    CodebaseStatus.PROCESSING,
                    processed_files=supported_files,
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

            texts = [chunk.content for chunk in all_chunks]
            embeddings = await embedding_service.generate_embeddings(texts)

            if embeddings:
                for chunk, embedding in zip(all_chunks, embeddings):
                    chunk.embedding = embedding

                # Store in vector database
                await vector_store.add_chunks(all_chunks)
            else:
                logger.error("embedding_generation_failed")
                raise RuntimeError("Failed to generate embeddings")

        # Update codebase status
        all_languages = set(chunk.language for chunk in all_chunks)
        primary_language = max(all_languages, key=all_languages.count) if all_languages else None

        codebase_store.update_status(
            codebase_id,
            CodebaseStatus.COMPLETED,
            processed_files=supported_files,
            primary_language=primary_language,
            all_languages=list(all_languages),
        )

        logger.info(
            "codebase_processing_complete",
            codebase_id=str(codebase_id),
            chunks_created=len(all_chunks),
            supported_files=supported_files,
            unsupported_files=unsupported_files,
            secrets_found=secrets_found,
        )

        return {
            "codebase_id": codebase_id,
            "chunks_created": len(all_chunks),
            "supported_files": supported_files,
            "unsupported_files": unsupported_files,
            "secrets_found": secrets_found,
            "primary_language": primary_language,
        }


# Singleton instance
_processor: CodebaseProcessor | None = None


def get_codebase_processor() -> CodebaseProcessor:
    """Get the singleton codebase processor instance."""
    global _processor
    if _processor is None:
        _processor = CodebaseProcessor()
    return _processor
