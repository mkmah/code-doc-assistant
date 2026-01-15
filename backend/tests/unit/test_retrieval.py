"""Unit tests for retrieval service."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.models.schemas import Source
from app.services.retrieval_service import RetrievalService


@pytest.fixture
def retrieval_service():
    """Create a retrieval service instance."""
    return RetrievalService()


@pytest.fixture
def mock_codebase_id():
    """Create a mock codebase ID."""
    return uuid4()


@pytest.fixture
def sample_chunks():
    """Create sample chunk data."""
    return [
        {
            "id": "chunk1",
            "content": "def hello_world():\n    print('Hello, World!')",
            "metadata": {
                "file_path": "app/main.py",
                "line_start": 1,
                "line_end": 2,
                "language": "python",
                "chunk_type": "function",
            },
            "embedding": [0.1] * 512,
        },
        {
            "id": "chunk2",
            "content": "class Calculator:\n    def add(self, a, b):\n        return a + b",
            "metadata": {
                "file_path": "app/calc.py",
                "line_start": 1,
                "line_end": 3,
                "language": "python",
                "chunk_type": "class",
            },
            "embedding": [0.2] * 512,
        },
        {
            "id": "chunk3",
            "content": "function greet(name) {\n    return 'Hello, ' + name;\n}",
            "metadata": {
                "file_path": "src/utils.js",
                "line_start": 1,
                "line_end": 2,
                "language": "javascript",
                "chunk_type": "function",
            },
            "embedding": [0.3] * 512,
        },
    ]


class TestRetrievalService:
    """Tests for RetrievalService class."""

    @pytest.mark.asyncio
    async def test_retrieve_code_basic(
        self, retrieval_service, mock_codebase_id, sample_chunks
    ):
        """Test basic code retrieval."""
        # Mock the embedding service
        with patch.object(
            retrieval_service._embedding_service,
            "generate_query_embedding",
            new_callable=AsyncMock,
            return_value=[0.1] * 512,
        ), patch.object(
            retrieval_service._vector_store,
            "query",
            new_callable=AsyncMock,
            return_value=sample_chunks,
        ):
            chunks, sources = await retrieval_service.retrieve_code(
                query="hello world function",
                codebase_id=mock_codebase_id,
                top_k=5,
            )

            # Verify results
            assert len(chunks) == 3
            assert len(sources) == 3

            # Verify chunk content
            assert chunks[0]["content"] == sample_chunks[0]["content"]
            assert chunks[1]["content"] == sample_chunks[1]["content"]

            # Verify sources
            assert sources[0].file_path == "app/main.py"
            assert sources[0].line_start == 1
            assert sources[0].line_end == 2

            # Verify snippet is truncated if too long
            assert len(sources[0].snippet) <= 203  # 200 + "..."

            # Verify vector store was called correctly
            retrieval_service._vector_store.query.assert_called_once()
            call_args = retrieval_service._vector_store.query.call_args
            assert call_args[1]["codebase_id"] == mock_codebase_id
            assert call_args[1]["top_k"] == 5

    @pytest.mark.asyncio
    async def test_retrieve_code_respects_max_top_k(
        self, retrieval_service, mock_codebase_id, sample_chunks
    ):
        """Test that retrieval respects max_top_k_results setting."""
        with patch.object(
            retrieval_service._embedding_service,
            "generate_query_embedding",
            new_callable=AsyncMock,
            return_value=[0.1] * 512,
        ), patch.object(
            retrieval_service._vector_store,
            "query",
            new_callable=AsyncMock,
            return_value=sample_chunks,
        ), patch(
            "app.services.retrieval_service.settings"
        ) as mock_settings:
            # Set a low max limit
            mock_settings.max_top_k_results = 2
            mock_settings.default_top_k_results = 10

            chunks, sources = await retrieval_service.retrieve_code(
                query="test",
                codebase_id=mock_codebase_id,
                top_k=10,  # Request more than max
            )

            # Should be capped at max_top_k_results
            retrieval_service._vector_store.query.assert_called_once()
            call_args = retrieval_service._vector_store.query.call_args
            assert call_args[1]["top_k"] == 2  # Capped at max

    @pytest.mark.asyncio
    async def test_retrieve_code_with_filters(
        self, retrieval_service, mock_codebase_id, sample_chunks
    ):
        """Test retrieval with metadata filters."""
        with patch.object(
            retrieval_service._embedding_service,
            "generate_query_embedding",
            new_callable=AsyncMock,
            return_value=[0.1] * 512,
        ), patch.object(
            retrieval_service._vector_store,
            "query",
            new_callable=AsyncMock,
            return_value=sample_chunks[:1],  # Return only one filtered result
        ):
            chunks = await retrieval_service.retrieve_by_filter(
                query="function",
                codebase_id=mock_codebase_id,
                language="python",
                chunk_type="function",
                file_path="app/main.py",
                top_k=5,
            )

            # Verify vector store was called with filters
            retrieval_service._vector_store.query.assert_called_once()
            call_args = retrieval_service._vector_store.query.call_args

            assert "where" in call_args[1]
            where_filter = call_args[1]["where"]
            assert where_filter["language"] == "python"
            assert where_filter["chunk_type"] == "function"
            assert where_filter["file_path"] == "app/main.py"

    @pytest.mark.asyncio
    async def test_retrieve_by_filter_partial_filters(
        self, retrieval_service, mock_codebase_id, sample_chunks
    ):
        """Test retrieval with partial filters (only language)."""
        with patch.object(
            retrieval_service._embedding_service,
            "generate_query_embedding",
            new_callable=AsyncMock,
            return_value=[0.1] * 512,
        ), patch.object(
            retrieval_service._vector_store,
            "query",
            new_callable=AsyncMock,
            return_value=sample_chunks,
        ):
            chunks = await retrieval_service.retrieve_by_filter(
                query="test",
                codebase_id=mock_codebase_id,
                language="javascript",
                top_k=5,
            )

            # Verify only language filter was applied
            retrieval_service._vector_store.query.assert_called_once()
            call_args = retrieval_service._vector_store.query.call_args
            where_filter = call_args[1]["where"]

            assert where_filter["language"] == "javascript"
            assert "chunk_type" not in where_filter
            assert "file_path" not in where_filter

    @pytest.mark.asyncio
    async def test_retrieve_code_embedding_failure(
        self, retrieval_service, mock_codebase_id
    ):
        """Test retrieval when embedding generation fails."""
        with patch.object(
            retrieval_service._embedding_service,
            "generate_query_embedding",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(RuntimeError, match="Failed to generate query embedding"):
                await retrieval_service.retrieve_code(
                    query="test query",
                    codebase_id=mock_codebase_id,
                )

    @pytest.mark.asyncio
    async def test_retrieve_by_filter_embedding_failure(
        self, retrieval_service, mock_codebase_id
    ):
        """Test filtered retrieval when embedding generation fails."""
        with patch.object(
            retrieval_service._embedding_service,
            "generate_query_embedding",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(RuntimeError, match="Failed to generate query embedding"):
                await retrieval_service.retrieve_by_filter(
                    query="test query",
                    codebase_id=mock_codebase_id,
                    language="python",
                )

    @pytest.mark.asyncio
    async def test_retrieve_code_empty_results(
        self, retrieval_service, mock_codebase_id
    ):
        """Test retrieval when no chunks match."""
        with patch.object(
            retrieval_service._embedding_service,
            "generate_query_embedding",
            new_callable=AsyncMock,
            return_value=[0.1] * 512,
        ), patch.object(
            retrieval_service._vector_store,
            "query",
            new_callable=AsyncMock,
            return_value=[],
        ):
            chunks, sources = await retrieval_service.retrieve_code(
                query="nonexistent code",
                codebase_id=mock_codebase_id,
            )

            assert len(chunks) == 0
            assert len(sources) == 0

    @pytest.mark.asyncio
    async def test_source_snippet_truncation(
        self, retrieval_service, mock_codebase_id
    ):
        """Test that long snippets are truncated correctly."""
        long_content = "x" * 300  # Longer than 200 chars

        chunk_with_long_content = {
            "id": "chunk1",
            "content": long_content,
            "metadata": {
                "file_path": "test.py",
                "line_start": 1,
                "line_end": 10,
            },
            "embedding": [0.1] * 512,
        }

        with patch.object(
            retrieval_service._embedding_service,
            "generate_query_embedding",
            new_callable=AsyncMock,
            return_value=[0.1] * 512,
        ), patch.object(
            retrieval_service._vector_store,
            "query",
            new_callable=AsyncMock,
            return_value=[chunk_with_long_content],
        ):
            chunks, sources = await retrieval_service.retrieve_code(
                query="test",
                codebase_id=mock_codebase_id,
            )

            # Snippet should be truncated
            assert len(sources[0].snippet) == 203  # 200 + "..."
            assert sources[0].snippet.endswith("...")

    @pytest.mark.asyncio
    async def test_retrieve_code_default_top_k(
        self, retrieval_service, mock_codebase_id, sample_chunks
    ):
        """Test that retrieval uses default_top_k_results when top_k is None."""
        with patch.object(
            retrieval_service._embedding_service,
            "generate_query_embedding",
            new_callable=AsyncMock,
            return_value=[0.1] * 512,
        ), patch.object(
            retrieval_service._vector_store,
            "query",
            new_callable=AsyncMock,
            return_value=sample_chunks,
        ), patch(
            "app.services.retrieval_service.settings"
        ) as mock_settings:
            mock_settings.default_top_k_results = 5
            mock_settings.max_top_k_results = 20

            chunks, sources = await retrieval_service.retrieve_code(
                query="test",
                codebase_id=mock_codebase_id,
                # top_k=None - use default
            )

            # Should use default_top_k_results
            retrieval_service._vector_store.query.assert_called_once()
            call_args = retrieval_service._vector_store.query.call_args
            assert call_args[1]["top_k"] == 5
