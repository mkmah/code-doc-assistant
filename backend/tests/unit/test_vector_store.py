"""Unit tests for vector store service."""

from unittest.mock import MagicMock, patch

import pytest
from uuid import uuid4

from app.services.vector_store import VectorStore, get_vector_store


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB client."""
    with patch("app.services.vector_store.chromadb") as mock:
        yield mock


@pytest.fixture
def vector_store() -> VectorStore:
    """Create a vector store instance for testing."""
    return VectorStore()


class TestVectorStoreDeleteCodebase:
    """Tests for delete_codebase method."""

    @pytest.mark.asyncio
    async def test_delete_codebase_with_chunks(self, vector_store: VectorStore) -> None:
        """Test deleting a codebase that has chunks in ChromaDB."""
        codebase_id = uuid4()

        # Mock collection with existing chunks
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["chunk1", "chunk2", "chunk3"],
            "documents": ["code1", "code2", "code3"],
            "metadatas": [
                {"codebase_id": str(codebase_id), "file_path": "test.py"},
                {"codebase_id": str(codebase_id), "file_path": "main.py"},
                {"codebase_id": str(codebase_id), "file_path": "utils.py"},
            ],
        }
        vector_store._collection = mock_collection

        # Delete codebase
        await vector_store.delete_codebase(codebase_id)

        # Verify chunks were queried and deleted
        mock_collection.get.assert_called_once_with(where={"codebase_id": str(codebase_id)})
        mock_collection.delete.assert_called_once_with(ids=["chunk1", "chunk2", "chunk3"])

    @pytest.mark.asyncio
    async def test_delete_codebase_with_no_chunks(self, vector_store: VectorStore) -> None:
        """Test deleting a codebase that has no chunks."""
        codebase_id = uuid4()

        # Mock collection with no chunks
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": [],
            "documents": [],
            "metadatas": [],
        }
        vector_store._collection = mock_collection

        # Delete codebase
        await vector_store.delete_codebase(codebase_id)

        # Verify get was called but delete was not (no chunks to delete)
        mock_collection.get.assert_called_once()
        mock_collection.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_codebase_many_chunks(self, vector_store: VectorStore) -> None:
        """Test deleting a codebase with many chunks (batch deletion)."""
        codebase_id = uuid4()

        # Mock collection with 1000 chunks
        chunk_ids = [f"chunk{i}" for i in range(1000)]
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": chunk_ids,
            "documents": [f"code{i}" for i in range(1000)],
            "metadatas": [
                {"codebase_id": str(codebase_id), "file_path": f"file{i}.py"}
                for i in range(1000)
            ],
        }
        vector_store._collection = mock_collection

        # Delete codebase
        await vector_store.delete_codebase(codebase_id)

        # Verify all chunks were deleted in one call
        mock_collection.delete.assert_called_once_with(ids=chunk_ids)

    @pytest.mark.asyncio
    async def test_delete_codebase_multiple_codebases(self, vector_store: VectorStore) -> None:
        """Test that deleting one codebase doesn't affect others."""
        codebase_id_1 = uuid4()
        codebase_id_2 = uuid4()

        # Mock collection with chunks from multiple codebases
        mock_collection = MagicMock()
        mock_collection.get.side_effect = [
            # First call (codebase_id_1)
            {
                "ids": ["chunk1", "chunk2"],
                "documents": ["code1", "code2"],
                "metadatas": [
                    {"codebase_id": str(codebase_id_1), "file_path": "test1.py"},
                    {"codebase_id": str(codebase_id_1), "file_path": "test2.py"},
                ],
            },
            # Second call (codebase_id_2) after deletion
            {
                "ids": ["chunk3", "chunk4"],
                "documents": ["code3", "code4"],
                "metadatas": [
                    {"codebase_id": str(codebase_id_2), "file_path": "test3.py"},
                    {"codebase_id": str(codebase_id_2), "file_path": "test4.py"},
                ],
            },
        ]
        vector_store._collection = mock_collection

        # Delete first codebase
        await vector_store.delete_codebase(codebase_id_1)

        # Verify only first codebase's chunks were deleted
        mock_collection.delete.assert_called_once_with(ids=["chunk1", "chunk2"])

    @pytest.mark.asyncio
    async def test_delete_codebase_handles_chromadb_error(
        self,
        vector_store: VectorStore,
    ) -> None:
        """Test that ChromaDB errors are propagated."""
        codebase_id = uuid4()

        # Mock collection that raises error
        mock_collection = MagicMock()
        mock_collection.get.side_effect = Exception("ChromaDB connection error")
        vector_store._collection = mock_collection

        # Should raise the error
        with pytest.raises(Exception, match="ChromaDB connection error"):
            await vector_store.delete_codebase(codebase_id)


class TestVectorStoreSingleton:
    """Tests for vector store singleton pattern."""

    def test_get_vector_store_returns_singleton(self) -> None:
        """Test that get_vector_store returns the same instance."""
        store1 = get_vector_store()
        store2 = get_vector_store()

        assert store1 is store2

    def test_get_vector_store_creates_new_instance_on_first_call(self) -> None:
        """Test that first call creates a new instance."""
        # Reset global singleton
        import app.services.vector_store
        app.services.vector_store._vector_store = None

        store = get_vector_store()

        assert isinstance(store, VectorStore)
        assert store is not None


class TestVectorStoreQuery:
    """Tests for query method (verify filtering still works after deletion)."""

    @pytest.mark.asyncio
    async def test_query_after_deletion_returns_empty(
        self,
        vector_store: VectorStore,
    ) -> None:
        """Test that querying after deletion returns no results."""
        codebase_id = uuid4()

        # Mock collection with no chunks (after deletion)
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
        }
        vector_store._collection = mock_collection

        # Query should return empty results
        results = await vector_store.query(
            query_embedding=[0.1, 0.2, 0.3],
            codebase_id=codebase_id,
            top_k=5,
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_query_filters_by_codebase_id(self, vector_store: VectorStore) -> None:
        """Test that query properly filters by codebase_id."""
        codebase_id = uuid4()
        query_embedding = [0.1, 0.2, 0.3]

        # Mock collection
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["chunk1"]],
            "documents": [["code content"]],
            "metadatas": [[{"codebase_id": str(codebase_id), "file_path": "test.py"}]],
        }
        vector_store._collection = mock_collection

        # Query
        await vector_store.query(
            query_embedding=query_embedding,
            codebase_id=codebase_id,
            top_k=5,
        )

        # Verify query was called with correct filter
        mock_collection.query.assert_called_once()
        call_kwargs = mock_collection.query.call_args.kwargs
        assert call_kwargs["where"]["codebase_id"] == str(codebase_id)


class TestVectorStoreHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, vector_store: VectorStore) -> None:
        """Test health check when ChromaDB is accessible."""
        mock_client = MagicMock()
        mock_client.heartbeat.return_value = True
        vector_store._client = mock_client

        result = await vector_store.health_check()

        assert result is True
        mock_client.heartbeat.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, vector_store: VectorStore) -> None:
        """Test health check when ChromaDB is not accessible."""
        mock_client = MagicMock()
        mock_client.heartbeat.side_effect = Exception("Connection failed")
        vector_store._client = mock_client

        result = await vector_store.health_check()

        assert result is False
