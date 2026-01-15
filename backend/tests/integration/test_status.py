"""Integration tests for codebase status endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from app.models.schemas import CodebaseStatus, SourceType


@pytest.mark.asyncio
async def test_get_status_during_processing(client: AsyncClient):
    """Test retrieving status while codebase is being processed."""
    from app.services.codebase_store import get_codebase_store

    codebase_store = get_codebase_store()

    # Create a codebase in PROCESSING state
    codebase = codebase_store.create(
        name="processing-codebase",
        description="A codebase currently being processed",
        source_type=SourceType.ZIP,
        source_url=None,
        size_bytes=1000,
        workflow_id="workflow-processing",
    )

    # Update to PROCESSING state
    codebase.status = CodebaseStatus.PROCESSING
    codebase.total_files = 100
    codebase.processed_files = 45

    # Get status
    response = await client.get(f"/api/v1/codebase/{codebase.id}/status")

    assert response.status_code == 200
    result = response.json()

    # Verify status response
    assert result["codebase_id"] == str(codebase.id)
    assert result["status"] == "processing"
    assert result["progress"] == 45.0  # (45/100) * 100
    assert result["total_files"] == 100
    assert result["processed_files"] == 45
    assert result["current_step"] == "parsing"
    assert result["error"] is None
    assert result["secrets_detected"] is None
    assert result["started_at"] is not None
    assert result["completed_at"] is None


@pytest.mark.asyncio
async def test_get_status_completed(client: AsyncClient):
    """Test retrieving status for a completed codebase."""
    from app.services.codebase_store import get_codebase_store

    codebase_store = get_codebase_store()

    # Create a codebase in COMPLETED state
    codebase = codebase_store.create(
        name="completed-codebase",
        description="A successfully processed codebase",
        source_type=SourceType.ZIP,
        source_url=None,
        size_bytes=2000,
        workflow_id="workflow-completed",
    )

    # Update to COMPLETED state
    codebase.status = CodebaseStatus.COMPLETED
    codebase.total_files = 50
    codebase.processed_files = 50

    # Get status
    response = await client.get(f"/api/v1/codebase/{codebase.id}/status")

    assert response.status_code == 200
    result = response.json()

    # Verify status response
    assert result["codebase_id"] == str(codebase.id)
    assert result["status"] == "completed"
    assert result["progress"] == 100.0  # (50/50) * 100
    assert result["total_files"] == 50
    assert result["processed_files"] == 50
    assert result["current_step"] == "complete"
    assert result["error"] is None
    assert result["secrets_detected"] is None
    assert result["started_at"] is not None
    assert result["completed_at"] is not None


@pytest.mark.asyncio
async def test_get_status_failed_with_error_message(client: AsyncClient):
    """Test retrieving status for a failed codebase with error details."""
    from app.services.codebase_store import get_codebase_store

    codebase_store = get_codebase_store()

    # Create a codebase in FAILED state
    codebase = codebase_store.create(
        name="failed-codebase",
        description="A codebase that failed processing",
        source_type=SourceType.ZIP,
        source_url=None,
        size_bytes=1500,
        workflow_id="workflow-failed",
    )

    # Update to FAILED state with error message
    codebase.status = CodebaseStatus.FAILED
    codebase.total_files = 30
    codebase.processed_files = 10
    codebase.error_message = "Unable to parse Python files: syntax error in module.py"

    # Get status
    response = await client.get(f"/api/v1/codebase/{codebase.id}/status")

    assert response.status_code == 200
    result = response.json()

    # Verify status response
    assert result["codebase_id"] == str(codebase.id)
    assert result["status"] == "failed"
    # Progress should be calculated even for failed status
    assert result["progress"] == (10.0 / 30.0) * 100
    assert result["total_files"] == 30
    assert result["processed_files"] == 10
    assert result["current_step"] is None  # Failed status has no step
    assert result["error"] == "Unable to parse Python files: syntax error in module.py"
    assert result["secrets_detected"] is None
    assert result["started_at"] is not None
    # Note: completed_at is None for FAILED status based on current implementation


@pytest.mark.asyncio
async def test_get_status_queued(client: AsyncClient):
    """Test retrieving status for a queued codebase."""
    from app.services.codebase_store import get_codebase_store

    codebase_store = get_codebase_store()

    # Create a codebase (defaults to QUEUED state)
    codebase = codebase_store.create(
        name="queued-codebase",
        description="A codebase waiting to be processed",
        source_type=SourceType.GITHUB_URL,
        source_url="https://github.com/user/repo",
        size_bytes=0,
        workflow_id="workflow-queued",
    )

    # Get status
    response = await client.get(f"/api/v1/codebase/{codebase.id}/status")

    assert response.status_code == 200
    result = response.json()

    # Verify status response
    assert result["codebase_id"] == str(codebase.id)
    assert result["status"] == "queued"
    assert result["progress"] == 0.0  # No files processed yet
    assert result["total_files"] == 0
    assert result["processed_files"] == 0
    assert result["current_step"] == "validating"
    assert result["error"] is None
    assert result["secrets_detected"] is None
    assert result["started_at"] is None  # Not started yet
    assert result["completed_at"] is None


@pytest.mark.asyncio
async def test_get_status_not_found(client: AsyncClient):
    """Test that requesting status for non-existent codebase returns 404."""
    fake_id = uuid4()

    response = await client.get(f"/api/v1/codebase/{fake_id}/status")

    assert response.status_code == 404
    result = response.json()
    assert "error" in result
    assert "Codebase not found" in result["error"]["message"]


@pytest.mark.asyncio
async def test_get_status_progress_calculation(client: AsyncClient):
    """Test that progress is calculated correctly."""
    from app.services.codebase_store import get_codebase_store

    codebase_store = get_codebase_store()

    # Create a codebase with specific progress
    codebase = codebase_store.create(
        name="progress-test",
        description="Testing progress calculation",
        source_type=SourceType.ZIP,
        source_url=None,
        size_bytes=1000,
        workflow_id="workflow-progress",
    )

    # Set progress values
    codebase.status = CodebaseStatus.PROCESSING
    codebase.total_files = 200
    codebase.processed_files = 75

    # Get status
    response = await client.get(f"/api/v1/codebase/{codebase.id}/status")

    assert response.status_code == 200
    result = response.json()

    # Verify progress calculation: (75/200) * 100 = 37.5%
    expected_progress = (75.0 / 200.0) * 100
    assert result["progress"] == expected_progress


@pytest.mark.asyncio
async def test_get_status_zero_division_protection(client: AsyncClient):
    """Test that progress calculation handles zero total_files gracefully."""
    from app.services.codebase_store import get_codebase_store

    codebase_store = get_codebase_store()

    # Create a codebase with no files
    codebase = codebase_store.create(
        name="no-files-codebase",
        description="Codebase with no files",
        source_type=SourceType.ZIP,
        source_url=None,
        size_bytes=0,
        workflow_id="workflow-no-files",
    )

    # Keep total_files at 0
    codebase.total_files = 0
    codebase.processed_files = 0

    # Get status
    response = await client.get(f"/api/v1/codebase/{codebase.id}/status")

    assert response.status_code == 200
    result = response.json()

    # Progress should be 0 when total_files is 0
    assert result["progress"] == 0.0
