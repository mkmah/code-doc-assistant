"""Unit tests for codebase processor service.

This module tests the CodebaseProcessor service which handles file storage
and codebase file management.

Tests follow TDD approach - written before implementation.
"""

import os
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest


class TestCodebaseProcessorService:
    """Tests for CodebaseProcessor service functionality."""

    @pytest.fixture
    def processor(self, tmp_path):
        """Create a CodebaseProcessor instance for testing.

        Note: This will fail until T016 (implementation) is complete.
        """
        from app.services.codebase_processor import CodebaseProcessor
        from app.core.config import get_settings

        # Use temp directory for testing
        settings = get_settings()
        original_path = settings.storage_path
        settings.storage_path = str(tmp_path / "codebases")

        processor = CodebaseProcessor()

        yield processor

        # Cleanup
        settings.storage_path = original_path

    # ==========================================================================
    # File Saving Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_save_zip_file(self, processor):
        """Test saving a ZIP file to storage."""
        # Create a test ZIP file
        codebase_id = uuid4()
        zip_content = self._create_test_zip({"main.py": "print('hello')"})

        file_path = await processor.save_file(codebase_id, zip_content)

        assert file_path is not None
        assert Path(file_path).exists()
        assert str(codebase_id) in file_path
        assert file_path.endswith(".zip")

    @pytest.mark.asyncio
    async def test_save_file_uses_correct_directory(self, processor):
        """Test that files are saved in the configured storage directory."""
        from app.core.config import get_settings

        settings = get_settings()
        codebase_id = uuid4()
        zip_content = self._create_test_zip({"test.py": "x = 1"})

        file_path = await processor.save_file(codebase_id, zip_content)

        # File should be under the storage path
        storage_dir = Path(settings.storage_path)
        assert Path(file_path).is_relative_to(storage_dir)

    @pytest.mark.asyncio
    async def test_save_file_creates_unique_filename(self, processor):
        """Test that saving creates unique filenames per codebase."""
        codebase_id_1 = uuid4()
        codebase_id_2 = uuid4()
        zip_content = self._create_test_zip({"test.py": "x = 1"})

        file_path_1 = await processor.save_file(codebase_id_1, zip_content)
        file_path_2 = await processor.save_file(codebase_id_2, zip_content)

        # Files should have different paths (different codebase IDs)
        assert file_path_1 != file_path_2

    # ==========================================================================
    # File Validation Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_file_size_limit_enforcement(self, processor):
        """Test that files exceeding size limit are rejected."""
        from app.core.config import get_settings
        from app.services.codebase_processor import FileSizeExceededError

        settings = get_settings()
        codebase_id = uuid4()

        # Create a file larger than the limit
        large_content = b"x" * (settings.max_file_size_bytes + 1)

        with pytest.raises(FileSizeExceededError) as exc_info:
            await processor.save_file(codebase_id, large_content)

        assert "size" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_valid_zip_file(self, processor):
        """Test that valid ZIP files are accepted."""
        codebase_id = uuid4()
        zip_content = self._create_test_zip({"valid.py": "print('valid')"})

        file_path = await processor.save_file(codebase_id, zip_content)

        assert file_path is not None
        assert Path(file_path).exists()

    @pytest.mark.asyncio
    async def test_corrupted_zip_file_rejected(self, processor):
        """Test that corrupted ZIP files are rejected."""
        from app.services.codebase_processor import InvalidFileError

        codebase_id = uuid4()
        corrupted_content = b"This is not a valid ZIP file"

        with pytest.raises(InvalidFileError):
            await processor.save_file(codebase_id, corrupted_content)

    @pytest.mark.asyncio
    async def test_empty_file_rejected(self, processor):
        """Test that empty files are rejected."""
        from app.services.codebase_processor import InvalidFileError

        codebase_id = uuid4()
        empty_content = b""

        with pytest.raises(InvalidFileError):
            await processor.save_file(codebase_id, empty_content)

    # ==========================================================================
    # File Deletion Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_delete_file(self, processor):
        """Test deleting a stored file."""
        codebase_id = uuid4()
        zip_content = self._create_test_zip({"to_delete.py": "x = 1"})

        file_path = await processor.save_file(codebase_id, zip_content)
        assert Path(file_path).exists()

        await processor.delete_file(codebase_id)

        assert not Path(file_path).exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file_no_error(self, processor):
        """Test that deleting a non-existent file doesn't raise error."""
        non_existent_id = uuid4()

        # Should not raise an error
        await processor.delete_file(non_existent_id)

    # ==========================================================================
    # File Retrieval Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_get_file_path(self, processor):
        """Test getting the path to a stored file."""
        codebase_id = uuid4()
        zip_content = self._create_test_zip({"test.py": "x = 1"})

        saved_path = await processor.save_file(codebase_id, zip_content)
        retrieved_path = await processor.get_file_path(codebase_id)

        assert saved_path == retrieved_path

    @pytest.mark.asyncio
    async def test_get_file_path_for_nonexistent_codebase(self, processor):
        """Test getting path for non-existent codebase returns None."""
        non_existent_id = uuid4()

        path = await processor.get_file_path(non_existent_id)

        assert path is None

    # ==========================================================================
    # File Listing Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_list_files_in_codebase(self, processor):
        """Test listing files within a codebase ZIP."""
        codebase_id = uuid4()
        files = {
            "main.py": "print('main')",
            "utils.py": "def helper(): pass",
            "config.py": "DEBUG = True"
        }
        zip_content = self._create_test_zip(files)

        await processor.save_file(codebase_id, zip_content)
        file_list = await processor.list_files(codebase_id)

        assert len(file_list) == 3
        assert "main.py" in file_list
        assert "utils.py" in file_list
        assert "config.py" in file_list

    @pytest.mark.asyncio
    async def test_list_files_empty_codebase(self, processor):
        """Test listing files in an empty ZIP."""
        codebase_id = uuid4()
        zip_content = self._create_test_zip({})

        await processor.save_file(codebase_id, zip_content)
        file_list = await processor.list_files(codebase_id)

        assert len(file_list) == 0

    # ==========================================================================
    # File Size Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_get_file_size(self, processor):
        """Test getting the size of a stored file."""
        codebase_id = uuid4()
        files = {"test.py": "x = " + "1" * 1000}
        zip_content = self._create_test_zip(files)

        await processor.save_file(codebase_id, zip_content)
        size = await processor.get_file_size(codebase_id)

        assert size > 0
        assert size == len(zip_content)

    @pytest.mark.asyncio
    async def test_get_file_size_nonexistent(self, processor):
        """Test getting size for non-existent file returns 0."""
        non_existent_id = uuid4()

        size = await processor.get_file_size(non_existent_id)

        assert size == 0

    # ==========================================================================
    # Storage Cleanup Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_cleanup_old_files(self, processor):
        """Test cleanup of files older than specified days."""
        import time

        codebase_id_1 = uuid4()
        codebase_id_2 = uuid4()

        zip_content = self._create_test_zip({"test.py": "x = 1"})

        # Save first file
        await processor.save_file(codebase_id_1, zip_content)
        file_path_1 = await processor.get_file_path(codebase_id_1)

        # Wait and save second file
        time.sleep(0.1)
        await processor.save_file(codebase_id_2, zip_content)

        # Cleanup files older than 0 days (should delete first file)
        # Note: This test may need adjustment based on implementation
        deleted_count = await processor.cleanup_old_files(days_old=0)

        assert deleted_count >= 1

    # ==========================================================================
    # Helper Methods
    # ==========================================================================

    def _create_test_zip(self, files: dict[str, str]) -> bytes:
        """Create a test ZIP file from a dictionary of filenames to content.

        Args:
            files: Dictionary mapping filenames to content

        Returns:
            ZIP file as bytes
        """
        import io

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, content in files.items():
                zip_file.writestr(filename, content)

        zip_buffer.seek(0)
        return zip_buffer.read()


class TestCodebaseProcessorValidation:
    """Tests for CodebaseProcessor validation logic."""

    @pytest.fixture
    def processor(self, tmp_path):
        """Create a CodebaseProcessor instance."""
        from app.services.codebase_processor import CodebaseProcessor
        from app.core.config import get_settings

        settings = get_settings()
        original_path = settings.storage_path
        settings.storage_path = str(tmp_path / "codebases")

        processor = CodebaseProcessor()

        yield processor

        settings.storage_path = original_path

    # ==========================================================================
    # Filename Validation Tests
    # ==========================================================================

    def test_validate_safe_filename(self, processor):
        """Test validation of safe filenames."""
        safe_names = [
            "codebase.zip",
            "my-project.zip",
            "project_v1.2.3.zip",
        ]

        for name in safe_names:
            assert processor.is_safe_filename(name) is True

    def test_validate_unsafe_filename(self, processor):
        """Test rejection of unsafe filenames."""
        unsafe_names = [
            "../../../etc/passwd.zip",
            "/absolute/path.zip",
            "./hidden.zip",
            "file with spaces.zip",
        ]

        for name in unsafe_names:
            assert processor.is_safe_filename(name) is False

    # ==========================================================================
    # File Type Validation Tests
    # ==========================================================================

    def test_validate_zip_file_type(self, processor):
        """Test validation of ZIP file type."""
        zip_content = self._create_test_zip({"test.py": "x = 1"})

        is_valid = processor.is_valid_zip_file(zip_content)
        assert is_valid is True

    def test_reject_non_zip_file_type(self, processor):
        """Test rejection of non-ZIP file types."""
        non_zip_content = b"This is plain text, not a ZIP file"

        is_valid = processor.is_valid_zip_file(non_zip_content)
        assert is_valid is False

    # ==========================================================================
    # Content Type Detection Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_detect_primary_language(self, processor):
        """Test detection of primary programming language."""
        files = {
            "main.py": "print('hello')",
            "utils.py": "def helper(): pass",
            "config.py": "DEBUG = True",
            "README.md": "# My Project",
        }
        codebase_id = uuid4()
        zip_content = self._create_test_zip(files)

        await processor.save_file(codebase_id, zip_content)
        language = await processor.detect_primary_language(codebase_id)

        assert language == "Python" or language == "python"

    @pytest.mark.asyncio
    async def test_detect_multiple_languages(self, processor):
        """Test detection of multiple programming languages."""
        files = {
            "app.py": "print('hello')",
            "utils.js": "console.log('world')",
            "styles.css": "body { color: red; }",
        }
        codebase_id = uuid4()
        zip_content = self._create_test_zip(files)

        await processor.save_file(codebase_id, zip_content)
        languages = await processor.detect_languages(codebase_id)

        assert "Python" in languages or "python" in languages
        assert "JavaScript" in languages or "javascript" in languages

    def _create_test_zip(self, files: dict[str, str]) -> bytes:
        """Create a test ZIP file."""
        import io

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, content in files.items():
                zip_file.writestr(filename, content)

        zip_buffer.seek(0)
        return zip_buffer.read()
