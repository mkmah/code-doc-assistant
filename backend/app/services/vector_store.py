"""Vector store service using ChromaDB."""

from typing import Any
from uuid import UUID

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import CodeChunk

settings = get_settings()
logger = get_logger(__name__)

# Collection name for code chunks
COLLECTION_NAME = "code_chunks"


class VectorStore:
    """ChromaDB vector store for code chunks."""

    def __init__(self) -> None:
        """Initialize the vector store client."""
        self._client: chromadb.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None

    @property
    def client(self) -> chromadb.ClientAPI:
        """Get or create ChromaDB client."""
        if self._client is None:
            logger.info(
                "connecting_to_chromadb",
                host=settings.chromadb_host,
                port=settings.chromadb_port,
            )
            self._client = chromadb.HttpClient(
                host=settings.chromadb_host,
                port=settings.chromadb_port,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
            logger.info("chromadb_connected")
        return self._client

    @property
    def collection(self) -> chromadb.Collection:
        """Get or create the code chunks collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "Code chunks for semantic search"},
            )
            logger.info("collection_ready", collection=COLLECTION_NAME)
        return self._collection

    async def add_chunks(self, chunks: list[CodeChunk]) -> None:
        """Add code chunks to the vector store.

        Args:
            chunks: List of code chunks to add

        Raises:
            ValueError: If any chunk is missing embeddings
        """
        if not chunks:
            logger.warning("no_chunks_to_add")
            return

        # Validate embeddings
        for chunk in chunks:
            if chunk.embedding is None:
                raise ValueError(f"Chunk {chunk.id} missing embedding")

        # Prepare batch data
        ids = [str(chunk.id) for chunk in chunks]
        embeddings = [chunk.embedding for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [
            {
                "codebase_id": str(chunk.codebase_id),
                "file_path": chunk.file_path,
                "line_start": chunk.line_start,
                "line_end": chunk.line_end,
                "language": chunk.language,
                "chunk_type": chunk.chunk_type.value,
                "name": chunk.name or "",
                "parent_class": chunk.parent_class or "",
            }
            for chunk in chunks
        ]

        # Add to collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        logger.info(
            "chunks_added",
            count=len(chunks),
            codebase_id=str(chunks[0].codebase_id),
        )

    async def query(
        self,
        query_embedding: list[float],
        codebase_id: UUID,
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Query the vector store for similar code chunks.

        Args:
            query_embedding: Query vector embedding
            codebase_id: Filter to this codebase
            top_k: Number of results to return
            where: Additional metadata filters

        Returns:
            List of matching chunks with metadata
        """
        # Build filter
        where_filter = {"codebase_id": str(codebase_id)}
        if where:
            where_filter.update(where)

        # Query collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
        )

        # Format results
        chunks = []
        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                chunks.append(
                    {
                        "id": chunk_id,
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                    }
                )

        logger.debug(
            "query_completed",
            results_count=len(chunks),
            codebase_id=str(codebase_id),
        )

        return chunks

    async def delete_codebase(self, codebase_id: UUID) -> None:
        """Delete all chunks for a codebase.

        Args:
            codebase_id: Codebase ID to delete
        """
        # Get chunks to delete
        results = self.collection.get(
            where={"codebase_id": str(codebase_id)},
        )

        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            logger.info(
                "codebase_deleted",
                codebase_id=str(codebase_id),
                chunks_deleted=len(results["ids"]),
            )
        else:
            logger.info("no_chunks_found_for_deletion", codebase_id=str(codebase_id))

    async def health_check(self) -> bool:
        """Check if ChromaDB is accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            self.client.heartbeat()
            return True
        except Exception as e:
            logger.error("chromadb_health_check_failed", error=str(e))
            return False


# Singleton instance
_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """Get the singleton vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
