"""Vector store service using ChromaDB."""

from typing import Any
from uuid import UUID

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils.embedding_functions import JinaEmbeddingFunction

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import CodeChunk

settings = get_settings()
logger = get_logger(__name__)


class VectorStore:
    """ChromaDB vector store for code chunks."""

    def __init__(self) -> None:
        """Initialize the vector store client."""
        self._client: chromadb.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None

    async def _get_client(self) -> chromadb.ClientAPI:
        """Get or create ChromaDB client."""
        if self._client is None:
            logger.info(
                "connecting_to_chromadb",
                host=settings.chromadb_host,
                port=settings.chromadb_port,
            )

            self._client = await chromadb.AsyncHttpClient(
                host=settings.chromadb_host,
                port=settings.chromadb_port,
                settings=ChromaSettings(
                    chroma_client_auth_provider="chromadb.auth.token.TokenAuthClientProvider",
                    chroma_client_auth_credentials=settings.chromadb_token,
                    anonymized_telemetry=False,
                ),
            )
            logger.info("chromadb_connected")
        return self._client

    async def _get_collection(self) -> chromadb.Collection:
        """Get or create the code chunks collection."""
        if self._collection is None:
            client = await self._get_client()

            jinaai_ef = JinaEmbeddingFunction(
                api_key=settings.jina_api_key,
                model_name="jina-embeddings-v4",
            )

            self._collection = await client.get_or_create_collection(
                name=settings.chromadb_collection,
                metadata={"description": "Code chunks for semantic search"},
                embedding_function=jinaai_ef,
            )
            logger.info("collection_ready", collection=settings.chromadb_collection)
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

        # Prepare batch data
        ids = [str(chunk.id) for chunk in chunks]
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

        collection = await self._get_collection()

        # Add to collection
        await collection.add(
            ids=ids,
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
        query: str,
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

        collection = await self._get_collection()

        # Build filter
        where_filter = {"codebase_id": str(codebase_id)}
        if where:
            where_filter.update(where)

        # Query collection
        results = await collection.query(
            query_texts=query,
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
        collection = await self._get_collection()

        results = await collection.get(
            where={"codebase_id": str(codebase_id)},
        )

        if results["ids"]:
            await collection.delete(ids=results["ids"])
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
            client = await self._get_client()
            client.heartbeat()
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
