"""Temporal activities for indexing in vector store."""

from uuid import UUID

from temporalio import activity

from app.services.vector_store import get_vector_store


@activity.defn
async def index_chunks(codebase_id: UUID, chunks: list) -> dict:
    """Index code chunks in vector store.

    Args:
        codebase_id: Codebase ID
        chunks: List of chunks with embeddings

    Returns:
        Index result
    """
    # Convert to CodeChunk model
    from uuid import uuid4

    from app.models.schemas import ChunkType, CodeChunk

    code_chunks = []
    for chunk_data in chunks:
        code_chunk = CodeChunk(
            id=uuid4(),
            codebase_id=codebase_id,
            file_path=chunk_data.get("file_path", ""),
            line_start=chunk_data.get("line_start", 0),
            line_end=chunk_data.get("line_end", 0),
            content=chunk_data.get("content", ""),
            language=chunk_data.get("language", ""),
            chunk_type=ChunkType(chunk_data.get("chunk_type", "function")),
            name=chunk_data.get("name"),
            docstring=chunk_data.get("docstring"),
            dependencies=chunk_data.get("dependencies"),
            parent_class=chunk_data.get("parent_class"),
            complexity=chunk_data.get("complexity", 0),
            embedding=chunk_data.get("embedding"),
            metadata=chunk_data.get("metadata", {}),
        )
        code_chunks.append(code_chunk)

    # Store in vector database
    vector_store = get_vector_store()
    await vector_store.add_chunks(code_chunks)

    return {
        "indexed": len(code_chunks),
        "codebase_id": str(codebase_id),
    }
