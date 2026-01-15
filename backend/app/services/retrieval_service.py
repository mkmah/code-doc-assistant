"""Retrieval service for code chunks using vector search."""

from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import Source
from app.services.embedding_service import get_embedding_service
from app.services.vector_store import get_vector_store

settings = get_settings()
logger = get_logger(__name__)


class RetrievalService:
    """Retrieves relevant code chunks using vector search."""

    def __init__(self) -> None:
        """Initialize the retrieval service."""
        self._embedding_service = get_embedding_service()
        self._vector_store = get_vector_store()

    async def retrieve_code(
        self,
        query: str,
        codebase_id: UUID,
        top_k: int | None = None,
    ) -> tuple[list[dict[str, Any]], list[Source]]:
        """Retrieve relevant code chunks for a query.

        Args:
            query: User's natural language query
            codebase_id: Target codebase ID
            top_k: Number of results to return

        Returns:
            Tuple of (retrieved_chunks, sources)
        """
        if top_k is None:
            top_k = settings.default_top_k_results

        top_k = min(top_k, settings.max_top_k_results)

        # Generate query embedding
        query_embedding = await self._embedding_service.generate_query_embedding(query)
        if not query_embedding:
            raise RuntimeError("Failed to generate query embedding")

        # Search vector store
        chunks = await self._vector_store.query(
            query_embedding=query_embedding,
            codebase_id=codebase_id,
            top_k=top_k,
        )

        # Format results
        sources = []
        for chunk in chunks:
            sources.append(
                Source(
                    file_path=chunk["metadata"]["file_path"],
                    line_start=chunk["metadata"]["line_start"],
                    line_end=chunk["metadata"]["line_end"],
                    snippet=chunk["content"][:200] + "..." if len(chunk["content"]) > 200 else chunk["content"],
                )
            )

        logger.info(
            "code_retrieved",
            query=query[:100],
            codebase_id=str(codebase_id),
            results_count=len(chunks),
        )

        return chunks, sources

    async def retrieve_by_filter(
        self,
        query: str,
        codebase_id: UUID,
        language: str | None = None,
        chunk_type: str | None = None,
        file_path: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve code chunks with metadata filtering.

        Args:
            query: User's natural language query
            codebase_id: Target codebase ID
            language: Filter by programming language
            chunk_type: Filter by chunk type (function, class, etc.)
            file_path: Filter by file path
            top_k: Number of results to return

        Returns:
            List of retrieved chunks
        """
        # Build filter
        where_filter: dict[str, Any] = {}
        if language:
            where_filter["language"] = language
        if chunk_type:
            where_filter["chunk_type"] = chunk_type
        if file_path:
            where_filter["file_path"] = file_path

        # Generate query embedding
        query_embedding = await self._embedding_service.generate_query_embedding(query)
        if not query_embedding:
            raise RuntimeError("Failed to generate query embedding")

        # Search vector store with filters
        chunks = await self._vector_store.query(
            query_embedding=query_embedding,
            codebase_id=codebase_id,
            top_k=top_k,
            where=where_filter if where_filter else None,
        )

        logger.info(
            "code_retrieved_filtered",
            codebase_id=str(codebase_id),
            filters=where_filter,
            results_count=len(chunks),
        )

        return chunks


# Singleton instance
_retrieval_service: RetrievalService | None = None


def get_retrieval_service() -> RetrievalService:
    """Get the singleton retrieval service instance."""
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service
