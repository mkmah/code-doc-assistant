"""Semantic code chunking utilities."""

from typing import Any

from pydantic import BaseModel

from app.core.logging import get_logger
from app.models.schemas import ChunkType
from app.utils.code_parser import ParsedCode

logger = get_logger(__name__)


class CodeChunk(BaseModel):
    """A semantic code chunk ready for embedding."""

    content: str
    file_path: str
    line_start: int
    line_end: int
    language: str
    chunk_type: ChunkType
    name: str | None = None
    docstring: str | None = None
    dependencies: list[str] | None = None
    parent_class: str | None = None
    complexity: int = 0
    metadata: dict[str, Any] | None = None


class CodeChunker:
    """Splits code into semantic chunks for embedding."""

    def __init__(
        self,
        min_tokens: int = 512,
        max_tokens: int = 1024,
        overlap_tokens: int = 50,
    ) -> None:
        """Initialize the chunker.

        Args:
            min_tokens: Target minimum chunk size
            max_tokens: Maximum chunk size
            overlap_tokens: Overlap between chunks
        """
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk_parsed_code(
        self,
        parsed: ParsedCode,
        full_content: str,
    ) -> list[CodeChunk]:
        """Chunk parsed code into semantic units.

        Args:
            parsed: Parsed code from CodeParser
            full_content: Full source code content

        Returns:
            List of code chunks
        """
        chunks = []

        # Chunk functions
        for func in parsed.functions:
            chunk = self._create_function_chunk(func, parsed, full_content)
            if chunk:
                chunks.append(chunk)

        # Chunk classes
        for cls in parsed.classes:
            class_chunks = self._create_class_chunks(cls, parsed, full_content)
            chunks.extend(class_chunks)

        # Chunk imports
        if parsed.imports:
            chunk = self._create_import_chunk(parsed, full_content)
            if chunk:
                chunks.append(chunk)

        logger.info(
            "code_chunked",
            file_path=parsed.file_path,
            chunks_created=len(chunks),
        )

        return chunks

    def _create_function_chunk(
        self,
        func: dict[str, Any],
        parsed: ParsedCode,
        full_content: str,
    ) -> CodeChunk | None:
        """Create a chunk from a function.

        Args:
            func: Function metadata
            parsed: Parsed code
            full_content: Full source code

        Returns:
            CodeChunk or None if extraction fails
        """
        try:
            # Extract function content
            lines = full_content.split("\n")
            func_lines = lines[max(0, func["line_start"] - 1) : min(len(lines), func["line_end"])]
            content = "\n".join(func_lines)

            # Estimate tokens (rough approximation: 1 token ≈ 4 chars)
            estimated_tokens = len(content) // 4

            # Skip if too small
            if estimated_tokens < 50:
                return None

            # Truncate if too large
            if estimated_tokens > self.max_tokens:
                content = self._truncate_content(content, self.max_tokens)

            return CodeChunk(
                content=content,
                file_path=parsed.file_path,
                line_start=func["line_start"],
                line_end=func["line_end"],
                language=parsed.language,
                chunk_type=ChunkType.FUNCTION,
                name=func.get("name"),
                docstring=func.get("docstring"),
                dependencies=None,  # Could extract from function body
                parent_class=None,
                complexity=parsed.complexity,
                metadata={
                    "byte_start": func.get("byte_start"),
                    "byte_end": func.get("byte_end"),
                },
            )
        except Exception as e:
            logger.warning("function_chunk_failed", error=str(e))
            return None

    def _create_class_chunks(
        self,
        cls: dict[str, Any],
        parsed: ParsedCode,
        full_content: str,
    ) -> list[CodeChunk]:
        """Create chunks from a class.

        For large classes, chunk into method groups.

        Args:
            cls: Class metadata
            parsed: Parsed code
            full_content: Full source code

        Returns:
            List of code chunks
        """
        try:
            lines = full_content.split("\n")
            class_lines = lines[max(0, cls["line_start"] - 1) : min(len(lines), cls["line_end"])]
            content = "\n".join(class_lines)

            estimated_tokens = len(content) // 4

            # If class is small enough, keep as one chunk
            if estimated_tokens <= self.max_tokens:
                return [
                    CodeChunk(
                        content=content,
                        file_path=parsed.file_path,
                        line_start=cls["line_start"],
                        line_end=cls["line_end"],
                        language=parsed.language,
                        chunk_type=ChunkType.CLASS,
                        name=cls.get("name"),
                        docstring=None,
                        dependencies=None,
                        parent_class=None,
                        complexity=parsed.complexity,
                        metadata={
                            "byte_start": cls.get("byte_start"),
                            "byte_end": cls.get("byte_end"),
                        },
                    )
                ]

            # For large classes, split by methods
            # This would need more sophisticated AST traversal
            # For MVP, return class as single chunk (may be truncated)
            return [
                CodeChunk(
                    content=self._truncate_content(content, self.max_tokens),
                    file_path=parsed.file_path,
                    line_start=cls["line_start"],
                    line_end=cls["line_end"],
                    language=parsed.language,
                    chunk_type=ChunkType.CLASS,
                    name=cls.get("name"),
                    docstring=None,
                    dependencies=None,
                    parent_class=None,
                    complexity=parsed.complexity,
                    metadata={"truncated": True},
                )
            ]
        except Exception as e:
            logger.warning("class_chunk_failed", error=str(e))
            return []

    def _create_import_chunk(
        self,
        parsed: ParsedCode,
        full_content: str,
    ) -> CodeChunk | None:
        """Create a chunk from import statements.

        Args:
            parsed: Parsed code
            full_content: Full source code

        Returns:
            CodeChunk or None if no imports
        """
        if not parsed.imports:
            return None

        # Combine all imports into one chunk
        import_texts = [imp["text"] for imp in parsed.imports]
        content = "\n".join(import_texts)

        # Get line range
        first_line = min(imp["line"] for imp in parsed.imports)
        last_line = max(imp["line"] for imp in parsed.imports)

        return CodeChunk(
            content=content,
            file_path=parsed.file_path,
            line_start=first_line,
            line_end=last_line,
            language=parsed.language,
            chunk_type=ChunkType.IMPORT,
            name=None,
            docstring=None,
            dependencies=None,
            parent_class=None,
            complexity=0,
            metadata={"import_count": len(parsed.imports)},
        )

    def _truncate_content(self, content: str, max_tokens: int) -> str:
        """Truncate content to max tokens (rough estimate).

        Args:
            content: Content to truncate
            max_tokens: Maximum tokens

        Returns:
            Truncated content
        """
        # Rough estimate: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        if len(content) <= max_chars:
            return content

        # Truncate at a line boundary if possible
        truncated = content[:max_chars]
        last_newline = truncated.rfind("\n")
        if last_newline > max_chars // 2:
            truncated = content[:last_newline]

        return truncated + "\n# ... (truncated)"


# Singleton instance
_code_chunker: CodeChunker | None = None


def get_code_chunker() -> CodeChunker:
    """Get the singleton code chunker instance."""
    global _code_chunker
    if _code_chunker is None:
        _code_chunker = CodeChunker()
    return _code_chunker
