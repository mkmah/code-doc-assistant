"""Integration tests for codebase upload endpoints."""

from io import BytesIO

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_valid_zip(client: AsyncClient):
    """Test uploading a valid ZIP file."""
    # Create a minimal valid ZIP file (ZIP file signature)
    zip_content = b"PK\x03\x04" + b"\x00" * 100

    files = {"file": ("test.zip", BytesIO(zip_content), "application/zip")}
    data = {
        "name": "test-codebase",
        "description": "A test codebase",
    }

    response = await client.post("/api/v1/codebase/upload", data=data, files=files)

    assert response.status_code == 202
    result = response.json()
    assert "codebase_id" in result
    assert result["status"] == "queued"
    assert "workflow_id" in result


@pytest.mark.asyncio
async def test_upload_valid_tar_gz(client: AsyncClient):
    """Test uploading a valid tar.gz file."""
    # Create a minimal tar.gz file (gzip signature)
    tar_gz_content = b"\x1f\x8b\x08\x00" + b"\x00" * 100

    files = {"file": ("test.tar.gz", BytesIO(tar_gz_content), "application/gzip")}
    data = {"name": "test-codebase-tar"}

    response = await client.post("/api/v1/codebase/upload", data=data, files=files)

    assert response.status_code == 202
    result = response.json()
    assert "codebase_id" in result


@pytest.mark.asyncio
async def test_upload_invalid_file_type(client: AsyncClient):
    """Test that invalid file types are rejected."""
    # Try to upload a .txt file
    txt_content = b"This is not a valid archive"

    files = {"file": ("test.txt", BytesIO(txt_content), "text/plain")}
    data = {"name": "test-codebase"}

    response = await client.post("/api/v1/codebase/upload", data=data, files=files)

    assert response.status_code == 400
    result = response.json()
    assert "error" in result
    assert result["error"]["type"] == "HTTPException"
    assert "Only ZIP and tar.gz files are supported" in result["error"]["message"]


@pytest.mark.asyncio
async def test_upload_invalid_file_type_exe(client: AsyncClient):
    """Test that .exe files are rejected."""
    exe_content = b"MZ\x90\x00" + b"\x00" * 100

    files = {"file": ("test.exe", BytesIO(exe_content), "application/x-msdownload")}
    data = {"name": "test-codebase"}

    response = await client.post("/api/v1/codebase/upload", data=data, files=files)

    assert response.status_code == 400
    result = response.json()
    assert "Only ZIP and tar.gz files are supported" in result["error"]["message"]


@pytest.mark.asyncio
async def test_upload_file_size_exceeds_limit(client: AsyncClient):
    """Test that files exceeding size limit are rejected."""
    # Import settings to get max file size
    from app.core.config import get_settings
    settings = get_settings()

    # Create a file larger than max size
    large_content = b"\x00" * (settings.max_file_size_bytes + 1)

    files = {"file": ("large.zip", BytesIO(large_content), "application/zip")}
    data = {"name": "large-codebase"}

    response = await client.post("/api/v1/codebase/upload", data=data, files=files)

    assert response.status_code == 413
    result = response.json()
    assert "File size exceeds" in result["error"]["message"]


@pytest.mark.asyncio
async def test_upload_valid_github_url(client: AsyncClient):
    """Test uploading with a valid GitHub URL."""
    data = {
        "name": "github-repo",
        "repository_url": "https://github.com/user/repo",
    }

    response = await client.post("/api/v1/codebase/upload", data=data)

    assert response.status_code == 202
    result = response.json()
    assert "codebase_id" in result
    assert result["status"] == "queued"


@pytest.mark.asyncio
async def test_upload_github_url_with_git_extension(client: AsyncClient):
    """Test uploading with a GitHub URL ending in .git."""
    data = {
        "name": "github-repo-git",
        "repository_url": "https://github.com/user/repo.git",
    }

    response = await client.post("/api/v1/codebase/upload", data=data)

    assert response.status_code == 202
    result = response.json()
    assert "codebase_id" in result


@pytest.mark.asyncio
async def test_upload_missing_both_file_and_url(client: AsyncClient):
    """Test that request fails when neither file nor URL is provided."""
    data = {
        "name": "test-codebase",
    }

    response = await client.post("/api/v1/codebase/upload", data=data)

    assert response.status_code == 400
    result = response.json()
    assert "Either file or repository_url must be provided" in result["error"]["message"]


@pytest.mark.asyncio
async def test_upload_both_file_and_url(client: AsyncClient):
    """Test that request fails when both file and URL are provided."""
    zip_content = b"PK\x03\x04" + b"\x00" * 100

    files = {"file": ("test.zip", BytesIO(zip_content), "application/zip")}
    data = {
        "name": "test-codebase",
        "repository_url": "https://github.com/user/repo",
    }

    response = await client.post("/api/v1/codebase/upload", data=data, files=files)

    assert response.status_code == 400
    result = response.json()
    assert "Only one of file or repository_url should be provided" in result["error"]["message"]


@pytest.mark.asyncio
async def test_upload_creates_codebase_record(client: AsyncClient):
    """Test that successful upload creates a codebase record."""
    zip_content = b"PK\x03\x04" + b"\x00" * 100

    files = {"file": ("test.zip", BytesIO(zip_content), "application/zip")}
    data = {
        "name": "record-test",
        "description": "Testing record creation",
    }

    response = await client.post("/api/v1/codebase/upload", data=data, files=files)

    assert response.status_code == 202
    result = response.json()
    codebase_id = result["codebase_id"]

    # Verify the codebase was created
    get_response = await client.get(f"/api/v1/codebase/{codebase_id}")
    assert get_response.status_code == 200
    codebase = get_response.json()
    assert codebase["name"] == "record-test"
    assert codebase["description"] == "Testing record creation"


@pytest.mark.asyncio
async def test_upload_case_insensitive_file_extension(client: AsyncClient):
    """Test that file extension validation is case-insensitive."""
    zip_content = b"PK\x03\x04" + b"\x00" * 100

    # Test uppercase .ZIP
    files = {"file": ("test.ZIP", BytesIO(zip_content), "application/zip")}
    data = {"name": "test-uppercase"}

    response = await client.post("/api/v1/codebase/upload", data=data, files=files)

    assert response.status_code == 202
    result = response.json()
    assert "codebase_id" in result


@pytest.mark.asyncio
async def test_upload_tar_gz_case_insensitive(client: AsyncClient):
    """Test that tar.gz extension validation handles case correctly."""
    tar_content = b"\x1f\x8b\x08\x00" + b"\x00" * 100

    # Test .TAR.GZ (uppercase)
    files = {"file": ("test.TAR.GZ", BytesIO(tar_content), "application/gzip")}
    data = {"name": "test-tar-upper"}

    response = await client.post("/api/v1/codebase/upload", data=data, files=files)

    assert response.status_code == 202
    result = response.json()
    assert "codebase_id" in result
