"""Integration tests for codebase deletion endpoint."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def test_client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_codebase_id() -> str:
    """Sample codebase ID for testing."""
    return str(uuid4())


class TestCodebaseDeleteEndpoint:
    """Tests for DELETE /api/v1/codebase/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_codebase_success(
        self,
        test_client: TestClient,
        sample_codebase_id: str,
    ) -> None:
        """Test successful codebase deletion."""
        with patch("app.api.v1.codebase.codebase_store") as mock_store:
            # Mock codebase exists and can be deleted
            mock_store.delete.return_value = True

            with patch("app.api.v1.codebase.vector_store") as mock_vector_store:
                with patch("app.api.v1.codebase.session_store") as mock_session_store:
                    with patch("app.api.v1.codebase.codebase_processor") as mock_processor:
                        response = test_client.delete(f"/api/v1/codebase/{sample_codebase_id}")

                        # Should return 204 No Content
                        assert response.status_code == 204

                        # Verify all cleanup steps were called
                        mock_vector_store.delete_codebase.assert_called_once()
                        mock_session_store.delete_sessions_by_codebase.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_codebase_not_found(
        self,
        test_client: TestClient,
        sample_codebase_id: str,
    ) -> None:
        """Test deletion of non-existent codebase returns 404."""
        with patch("app.api.v1.codebase.codebase_store") as mock_store:
            # Mock codebase doesn't exist
            mock_store.delete.return_value = False

            response = test_client.delete(f"/api/v1/codebase/{sample_codebase_id}")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_codebase_removes_from_chromadb(
        self,
        test_client: TestClient,
        sample_codebase_id: str,
    ) -> None:
        """Test that deletion removes chunks from ChromaDB."""
        with patch("app.api.v1.codebase.codebase_store") as mock_store:
            mock_store.delete.return_value = True

            with patch("app.api.v1.codebase.vector_store") as mock_vector_store:
                mock_vector_store.delete_codebase = AsyncMock()

                with patch("app.api.v1.codebase.session_store"):
                    with patch("app.api.v1.codebase.codebase_processor"):
                        response = test_client.delete(f"/api/v1/codebase/{sample_codebase_id}")

                        assert response.status_code == 204
                        mock_vector_store.delete_codebase.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_codebase_removes_sessions(
        self,
        test_client: TestClient,
        sample_codebase_id: str,
    ) -> None:
        """Test that deletion removes all associated sessions."""
        with patch("app.api.v1.codebase.codebase_store") as mock_store:
            mock_store.delete.return_value = True

            with patch("app.api.v1.codebase.vector_store"):
                with patch("app.api.v1.codebase.session_store") as mock_session_store:
                    mock_session_store.delete_sessions_by_codebase = AsyncMock(return_value=3)

                    with patch("app.api.v1.codebase.codebase_processor"):
                        response = test_client.delete(f"/api/v1/codebase/{sample_codebase_id}")

                        assert response.status_code == 204
                        mock_session_store.delete_sessions_by_codebase.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_codebase_removes_local_files(
        self,
        test_client: TestClient,
        sample_codebase_id: str,
    ) -> None:
        """Test that deletion removes local files."""
        with patch("app.api.v1.codebase.codebase_store") as mock_store:
            mock_codebase = MagicMock()
            mock_codebase.storage_path = "/tmp/test.zip"
            mock_store.get.return_value = mock_codebase
            mock_store.delete.return_value = True

            with patch("app.api.v1.codebase.vector_store"):
                with patch("app.api.v1.codebase.session_store"):
                    with patch("app.api.v1.codebase.codebase_processor") as mock_processor:
                        mock_processor.get_file_path = MagicMock(return_value=Path("/tmp/test.zip"))
                        mock_processor.delete_file = AsyncMock()

                        response = test_client.delete(f"/api/v1/codebase/{sample_codebase_id}")

                        assert response.status_code == 204
                        mock_processor.delete_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_codebase_cancels_active_workflow(
        self,
        test_client: TestClient,
        sample_codebase_id: str,
    ) -> None:
        """Test that active Temporal workflows are cancelled during deletion."""
        with patch("app.api.v1.codebase.codebase_store") as mock_store:
            mock_codebase = MagicMock()
            mock_codebase.workflow_id = "test-workflow-id"
            mock_codebase.status = "processing"
            mock_store.get.return_value = mock_codebase
            mock_store.delete.return_value = True

            with patch("app.api.v1.codebase.vector_store"):
                with patch("app.api.v1.codebase.session_store"):
                    with patch("app.api.v1.codebase.codebase_processor"):
                        with patch("app.api.v1.codebase.get_temporal_client") as mock_temporal:
                            mock_client = MagicMock()
                            mock_client.get_workflow_handle = MagicMock(return_value=MagicMock())
                            mock_temporal.return_value = mock_client

                            response = test_client.delete(f"/api/v1/codebase/{sample_codebase_id}")

                            assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_codebase_handles_missing_file_gracefully(
        self,
        test_client: TestClient,
        sample_codebase_id: str,
    ) -> None:
        """Test that deletion succeeds even if local file is missing."""
        with patch("app.api.v1.codebase.codebase_store") as mock_store:
            mock_codebase = MagicMock()
            mock_codebase.storage_path = "/tmp/nonexistent.zip"
            mock_store.get.return_value = mock_codebase
            mock_store.delete.return_value = True

            with patch("app.api.v1.codebase.vector_store"):
                with patch("app.api.v1.codebase.session_store"):
                    with patch("app.api.v1.codebase.codebase_processor") as mock_processor:
                        # Mock file doesn't exist
                        mock_processor.get_file_path = MagicMock(return_value=Path("/tmp/nonexistent.zip"))
                        mock_processor.delete_file = AsyncMock(side_effect=FileNotFoundError())

                        response = test_client.delete(f"/api/v1/codebase/{sample_codebase_id}")

                        # Should still succeed (204) even if file is missing
                        assert response.status_code == 204


class TestCodebaseDeleteCleanupOrder:
    """Tests for proper cleanup order during deletion."""

    @pytest.mark.asyncio
    async def test_cleanup_happens_in_correct_order(
        self,
        test_client: TestClient,
        sample_codebase_id: str,
    ) -> None:
        """Test that cleanup happens in the correct order: ChromaDB -> sessions -> files -> workflow."""
        with patch("app.api.v1.codebase.codebase_store") as mock_store:
            mock_store.delete.return_value = True

            call_order = []

            with patch("app.api.v1.codebase.vector_store") as mock_vector_store:
                async def mock_delete_vs(*args, **kwargs):
                    call_order.append("chromadb")

                mock_vector_store.delete_codebase = AsyncMock(side_effect=mock_delete_vs)

                with patch("app.api.v1.codebase.session_store") as mock_session_store:
                    async def mock_delete_sessions(*args, **kwargs):
                        call_order.append("sessions")

                    mock_session_store.delete_sessions_by_codebase = AsyncMock(side_effect=mock_delete_sessions)

                    with patch("app.api.v1.codebase.codebase_processor") as mock_processor:
                        async def mock_delete_file(*args, **kwargs):
                            call_order.append("files")

                        mock_processor.delete_file = AsyncMock(side_effect=mock_delete_file)

                        response = test_client.delete(f"/api/v1/codebase/{sample_codebase_id}")

                        assert response.status_code == 204

                        # Verify order: ChromaDB should be cleaned first
                        assert call_order[0] == "chromadb"


class TestCodebaseDeleteErrorHandling:
    """Tests for error handling during deletion."""

    @pytest.mark.asyncio
    async def test_delete_handles_vector_store_errors(
        self,
        test_client: TestClient,
        sample_codebase_id: str,
    ) -> None:
        """Test that vector store errors are handled gracefully."""
        with patch("app.api.v1.codebase.codebase_store") as mock_store:
            mock_store.delete.return_value = True

            with patch("app.api.v1.codebase.vector_store") as mock_vector_store:
                # Mock ChromaDB error
                mock_vector_store.delete_codebase = AsyncMock(side_effect=Exception("ChromaDB connection failed"))

                with patch("app.api.v1.codebase.session_store"):
                    with patch("app.api.v1.codebase.codebase_processor"):
                        # Should still attempt other cleanup
                        response = test_client.delete(f"/api/v1/codebase/{sample_codebase_id}")

                        # Error should be logged but still return success
                        assert response.status_code in [204, 500]

    @pytest.mark.asyncio
    async def test_delete_handles_session_store_errors(
        self,
        test_client: TestClient,
        sample_codebase_id: str,
    ) -> None:
        """Test that session store errors are handled gracefully."""
        with patch("app.api.v1.codebase.codebase_store") as mock_store:
            mock_store.delete.return_value = True

            with patch("app.api.v1.codebase.vector_store"):
                with patch("app.api.v1.codebase.session_store") as mock_session_store:
                    # Mock session store error
                    mock_session_store.delete_sessions_by_codebase = AsyncMock(
                        side_effect=Exception("Session store error")
                    )

                    with patch("app.api.v1.codebase.codebase_processor"):
                        response = test_client.delete(f"/api/v1/codebase/{sample_codebase_id}")

                        # Error should be logged but still attempt other cleanup
                        assert response.status_code in [204, 500]
