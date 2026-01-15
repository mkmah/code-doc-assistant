"""LangGraph agent tools for code retrieval and analysis."""

from typing import Any

from app.core.logging import get_logger
from app.services.retrieval_service import get_retrieval_service

logger = get_logger(__name__)


async def retrieve_code(
    query: str,
    codebase_id: str,
    top_k: int = 5,
    language: str | None = None,
    chunk_type: str | None = None,
    file_path: str | None = None,
) -> dict[str, Any]:
    """Retrieve relevant code chunks using vector search.

    This tool performs semantic search over the codebase to find
    code chunks that match the user's query.

    Args:
        query: Natural language query describing the code to find
        codebase_id: UUID of the codebase to search
        top_k: Maximum number of results to return (default: 5, max: 20)
        language: Optional filter by programming language (e.g., "python", "typescript")
        chunk_type: Optional filter by chunk type (e.g., "function", "class")
        file_path: Optional filter to specific file path

    Returns:
        Dictionary containing:
            - chunks: List of retrieved code chunks with metadata
            - sources: List of source citations (file_path, line_start, line_end, snippet)
            - count: Number of chunks retrieved

    Example:
        >>> result = await retrieve_code(
        ...     query="How is authentication implemented?",
        ...     codebase_id="123e4567-e89b-12d3-a456-426614174000",
        ...     top_k=5
        ... )
        >>> print(f"Found {result['count']} relevant chunks")
    """
    from uuid import UUID

    retrieval_service = get_retrieval_service()

    try:
        # Convert codebase_id string to UUID
        codebase_uuid = UUID(codebase_id)

        # Use filtered retrieval if filters provided
        if language or chunk_type or file_path:
            chunks = await retrieval_service.retrieve_by_filter(
                query=query,
                codebase_id=codebase_uuid,
                language=language,
                chunk_type=chunk_type,
                file_path=file_path,
                top_k=min(top_k, 20),
            )

            # Build sources from chunks
            from app.models.schemas import Source

            sources = [
                Source(
                    file_path=chunk["metadata"]["file_path"],
                    line_start=chunk["metadata"]["line_start"],
                    line_end=chunk["metadata"]["line_end"],
                    snippet=(
                        chunk["content"][:200] + "..."
                        if len(chunk["content"]) > 200
                        else chunk["content"]
                    ),
                )
                for chunk in chunks
            ]
        else:
            # Use standard retrieval
            chunks, sources = await retrieval_service.retrieve_code(
                query=query,
                codebase_id=codebase_uuid,
                top_k=min(top_k, 20),
            )

        logger.info(
            "tool_retrieve_code_called",
            query=query[:100],
            codebase_id=codebase_id,
            results_count=len(chunks),
            filters={"language": language, "chunk_type": chunk_type, "file_path": file_path},
        )

        return {
            "chunks": chunks,
            "sources": [source.model_dump() for source in sources],
            "count": len(chunks),
        }

    except Exception as e:
        logger.error(
            "tool_retrieve_code_error",
            query=query[:100],
            codebase_id=codebase_id,
            error=str(e),
        )
        raise


# Tool definition for LangGraph
# This describes the tool interface for the agent
retrieve_code_tool_definition = {
    "name": "retrieve_code",
    "description": "Retrieve relevant code chunks using semantic vector search over the codebase. "
    "Use this tool when you need to find specific code, functions, or classes "
    "that match the user's query.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language query describing the code to find. "
                "Be specific and include relevant technical terms.",
            },
            "codebase_id": {
                "type": "string",
                "description": "UUID of the codebase to search.",
            },
            "top_k": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 5, max: 20).",
                "default": 5,
            },
            "language": {
                "type": "string",
                "description": "Optional filter by programming language (e.g., 'python', 'typescript').",
            },
            "chunk_type": {
                "type": "string",
                "description": "Optional filter by chunk type (e.g., 'function', 'class').",
            },
            "file_path": {
                "type": "string",
                "description": "Optional filter to specific file path.",
            },
        },
        "required": ["query", "codebase_id"],
    },
}


__all__ = [
    "retrieve_code",
    "retrieve_code_tool_definition",
]
