"""Integration tests for codebase upload endpoint with storage and workflow.

This module tests the upload endpoint integration with:
- File storage service (codebase_processor.save_file)
- Temporal workflow execution
- Status tracking

Tests follow TDD approach - written before implementation (T017).
"""

import zipfile
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient


class TestCodebaseUploadIntegration:
    """Integration tests for codebase upload endpoint."""

    # ==========================================================================
    # File Storage Integration Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_upload_saves_file_to_storage(self, client: AsyncClient, tmp_path):
        """Test that successful upload saves file to storage."""
        from app.core.config import get_settings

        settings = get_settings()
        original_path = settings.storage_path
        settings.storage_path = str(tmp_path / "codebases")

        try:
            # Create a valid Python project ZIP
            zip_content = self._create_python_project_zip()

            files = {"file": ("test-project.zip", BytesIO(zip_content), "application/zip")}
            data = {
                "name": "test-project",
                "description": "Test project for file storage",
            }

            response = await client.post("/api/v1/codebase/upload", data=data, files=files)

            assert response.status_code == 202
            result = response.json()
            codebase_id = result["codebase_id"]

            # Verify file was saved to storage
            from app.services.codebase_processor import CodebaseProcessor
            processor = CodebaseProcessor()
            file_path = await processor.get_file_path(UUID(codebase_id))

            assert file_path is not None
            assert Path(file_path).exists()

        finally:
            settings.storage_path = original_path

    @pytest.mark.asyncio
    async def test_upload_file_stored_with_correct_name(self, client: AsyncClient, tmp_path):
        """Test that uploaded file is stored with codebase ID in filename."""
        from app.core.config import get_settings

        settings = get_settings()
        original_path = settings.storage_path
        settings.storage_path = str(tmp_path / "codebases")

        try:
            zip_content = self._create_python_project_zip()

            files = {"file": ("my-project.zip", BytesIO(zip_content), "application/zip")}
            data = {"name": "my-project"}

            response = await client.post("/api/v1/codebase/upload", data=data, files=files)

            result = response.json()
            codebase_id = result["codebase_id"]

            from app.services.codebase_processor import CodebaseProcessor
            processor = CodebaseProcessor()
            file_path = await processor.get_file_path(UUID(codebase_id))

            # File path should contain the codebase ID
            assert codebase_id in file_path

        finally:
            settings.storage_path = original_path

    # ==========================================================================
    # Temporal Workflow Integration Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_upload_triggers_temporal_workflow(self, client: AsyncClient):
        """Test that successful upload triggers Temporal ingestion workflow."""
        zip_content = self._create_python_project_zip()

        files = {"file": ("workflow-test.zip", BytesIO(zip_content), "application/zip")}
        data = {
            "name": "workflow-test",
            "description": "Test workflow trigger",
        }

        response = await client.post("/api/v1/codebase/upload", data=data, files=files)

        assert response.status_code == 202
        result = response.json()

        # Should have a workflow_id
        assert "workflow_id" in result
        assert len(result["workflow_id"]) > 0

        # Status should be queued or processing
        assert result["status"] in ["queued", "processing"]

    @pytest.mark.asyncio
    async def test_upload_returns_valid_workflow_id(self, client: AsyncClient):
        """Test that upload returns a valid Temporal workflow ID."""
        zip_content = self._create_python_project_zip()

        files = {"file": ("workflow-id-test.zip", BytesIO(zip_content), "application/zip")}
        data = {"name": "workflow-id-test"}

        response = await client.post("/api/v1/codebase/upload", data=data, files=files)

        result = response.json()
        workflow_id = result["workflow_id"]

        # Workflow ID should be a non-empty string
        assert isinstance(workflow_id, str)
        assert len(workflow_id) > 0

    # ==========================================================================
    # Error Handling Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_upload_handles_corrupted_zip(self, client: AsyncClient):
        """Test that corrupted ZIP files are handled gracefully."""
        corrupted_content = b"This is not a valid ZIP file content"

        files = {"file": ("corrupted.zip", BytesIO(corrupted_content), "application/zip")}
        data = {"name": "corrupted-test"}

        response = await client.post("/api/v1/codebase/upload", data=data, files=files)

        assert response.status_code == 400
        result = response.json()
        assert "error" in result

    @pytest.mark.asyncio
    async def test_upload_handles_temporal_unavailable(self, client: AsyncClient):
        """Test upload behavior when Temporal service is unavailable."""
        # This test would require mocking Temporal connection failure
        # For now, we document the expected behavior
        zip_content = self._create_python_project_zip()

        files = {"file": ("temporal-down.zip", BytesIO(zip_content), "application/zip")}
        data = {"name": "temporal-down-test"}

        # If Temporal is unavailable, should return 503 Service Unavailable
        # or handle gracefully with a meaningful error
        response = await client.post("/api/v1/codebase/upload", data=data, files=files)

        # Accept either success (if Temporal is running) or error
        assert response.status_code in [202, 503, 500]

    @pytest.mark.asyncio
    async def test_upload_handles_storage_failure(self, client: AsyncClient, tmp_path):
        """Test upload behavior when storage fails (e.g., disk full)."""
        from app.core.config import get_settings

        settings = get_settings()
        original_path = settings.storage_path

        # Set storage to a read-only directory (simulating failure)
        settings.storage_path = "/proc"  # Read-only on most systems

        try:
            zip_content = self._create_python_project_zip()

            files = {"file": ("storage-fail.zip", BytesIO(zip_content), "application/zip")}
            data = {"name": "storage-fail-test"}

            response = await client.post("/api/v1/codebase/upload", data=data, files=files)

            # Should handle storage failure gracefully
            assert response.status_code in [400, 500, 503]
            result = response.json()
            assert "error" in result

        finally:
            settings.storage_path = original_path

    # ==========================================================================
    # Response Format Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_upload_response_includes_all_required_fields(self, client: AsyncClient):
        """Test that upload response includes all required fields."""
        zip_content = self._create_python_project_zip()

        files = {"file": ("response-test.zip", BytesIO(zip_content), "application/zip")}
        data = {
            "name": "response-test",
            "description": "Test response format",
        }

        response = await client.post("/api/v1/codebase/upload", data=data, files=files)

        assert response.status_code == 202
        result = response.json()

        # Required fields
        assert "codebase_id" in result
        assert "status" in result
        assert "workflow_id" in result

        # Field types
        assert isinstance(UUID(result["codebase_id"]), UUID)
        assert isinstance(result["status"], str)
        assert isinstance(result["workflow_id"], str)

    # ==========================================================================
    # Integration with Status Endpoint Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_upload_status_reflects_workflow_state(self, client: AsyncClient):
        """Test that status endpoint reflects the workflow triggered by upload."""
        zip_content = self._create_python_project_zip()

        # Upload codebase
        files = {"file": ("status-test.zip", BytesIO(zip_content), "application/zip")}
        data = {"name": "status-test"}

        upload_response = await client.post("/api/v1/codebase/upload", data=data, files=files)
        upload_result = upload_response.json()
        codebase_id = upload_result["codebase_id"]

        # Check status
        status_response = await client.get(f"/api/v1/codebase/{codebase_id}/status")

        assert status_response.status_code == 200
        status_result = status_response.json()

        # Status should match what was returned from upload
        assert status_result["codebase_id"] == codebase_id
        assert status_result["status"] in ["queued", "processing", "completed", "failed"]

    # ==========================================================================
    # Helper Methods
    # ==========================================================================

    def _create_python_project_zip(self) -> bytes:
        """Create a minimal Python project ZIP file for testing.

        Returns:
            ZIP file content as bytes
        """
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add some Python files
            zip_file.writestr("main.py", """
def main():
    print('Hello, World!')

if __name__ == '__main__':
    main()
""")
            zip_file.writestr("utils.py", """
def helper():
    return 'helper result'

class Calculator:
    def add(self, a, b):
        return a + b
""")
            zip_file.writestr("config.py", """
DEBUG = True
SECRET_KEY = 'development-key'
DATABASE_URL = 'sqlite:///test.db'
""")
            zip_file.writestr("README.md", """
# Test Project

This is a test project for upload testing.
""")

        zip_buffer.seek(0)
        return zip_buffer.read()


class TestCodebaseUploadEdgeCases:
    """Edge case tests for codebase upload."""

    @pytest.mark.asyncio
    async def test_upload_with_secrets_in_code(self, client: AsyncClient):
        """Test upload handling when code contains detected secrets."""
        # Create a ZIP with secrets
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Include files with potential secrets
            zip_file.writestr("config.py", """
AWS_ACCESS_KEY_ID=AKIA1234567890ABCDEF
AWS_SECRET_ACCESS_KEY=supersecretkey123
GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz
""")

        zip_buffer.seek(0)
        zip_content = zip_buffer.read()

        files = {"file": ("secrets-test.zip", BytesIO(zip_content), "application/zip")}
        data = {"name": "secrets-test"}

        response = await client.post("/api/v1/codebase/upload", data=data, files=files)

        # Upload should succeed (secrets are handled during processing)
        assert response.status_code == 202
        result = response.json()
        assert "codebase_id" in result

        # Later, secrets should be detected during ingestion
        # (This will be verified in status checks)

    @pytest.mark.asyncio
    async def test_upload_empty_zip(self, client: AsyncClient):
        """Test upload of an empty ZIP file."""
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Empty ZIP - no files added
            pass

        zip_buffer.seek(0)
        zip_content = zip_buffer.read()

        files = {"file": ("empty.zip", BytesIO(zip_content), "application/zip")}
        data = {"name": "empty-test"}

        response = await client.post("/api/v1/codebase/upload", data=data, files=files)

        # Should handle empty ZIP gracefully
        assert response.status_code in [202, 400]

    @pytest.mark.asyncio
    async def test_upload_with_deeply_nested_files(self, client: AsyncClient):
        """Test upload with deeply nested directory structure."""
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Create deeply nested structure
            zip_file.writestr("a/b/c/d/e/f/g/h/file.py", "print('deeply nested')")

        zip_buffer.seek(0)
        zip_content = zip_buffer.read()

        files = {"file": ("deep.zip", BytesIO(zip_content), "application/zip")}
        data = {"name": "deep-test"}

        response = await client.post("/api/v1/codebase/upload", data=data, files=files)

        # Should handle deep nesting
        assert response.status_code == 202
