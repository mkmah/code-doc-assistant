"""Temporal activities for embedding generation."""

from uuid import UUID

from temporalio import activity

from app.services.embedding_service import get_embedding_service


@activity.defn
async def generate_embeddings(codebase_id: UUID, chunks: list) -> dict:
    """Generate embeddings for code chunks.

    Args:
        codebase_id: Codebase ID
        chunks: List of code chunks

    Returns:
        Embedding result
    """
    service = get_embedding_service()

    texts = [chunk.get("content", "") for chunk in chunks]
    embeddings = await service.generate_embeddings(texts)

    if not embeddings:
        raise RuntimeError("Failed to generate embeddings")

    # Combine chunks with embeddings
    chunks_with_embeddings = []
    for chunk, embedding in zip(chunks, embeddings):
        chunk_with_emb = {**chunk, "embedding": embedding}
        chunks_with_embeddings.append(chunk_with_emb)

    return {
        "chunks_with_embeddings": chunks_with_embeddings,
        "count": len(chunks_with_embeddings),
    }
