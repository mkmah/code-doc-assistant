"""Integration tests for codebase status endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.db.session import AsyncSessionLocal
from app.models.db.codebase import Codebase as DBCodebase, SourceType as DBSourceType, CodebaseStatus as DBCodebaseStatus
from app.models.schemas import CodebaseStatus, SourceType


@pytest.fixture
async def db_session():
    """Create a database session for test setup."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_get_status_during_processing(client: AsyncClient, db_session):
    """Test retrieving status while codebase is being processed."""
    # Create a codebase in PROCESSING state
    codebase = DBCodebase(
        name="processing-codebase",
        description="A codebase currently being processed",
        source_type=DBSourceType.ZIP,
        source_url=None,
        size_bytes=1000,
        workflow_id="workflow-processing",
        status=DBCodebaseStatus.PROCESSING,
        total_files=100,
        processed_files=45,
    )
    db_session.add(codebase)
    await db_session.commit()
    await db_session.refresh(codebase)

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
async def test_get_status_completed(client: AsyncClient, db_session):
    """Test retrieving status for a completed codebase."""
    # Create a codebase in COMPLETED state
    codebase = DBCodebase(
        name="completed-codebase",
        description="A successfully processed codebase",
        source_type=DBSourceType.ZIP,
        source_url=None,
        size_bytes=2000,
        workflow_id="workflow-completed",
        status=DBCodebaseStatus.COMPLETED,
        total_files=50,
        processed_files=50,
    )
    db_session.add(codebase)
    await db_session.commit()
    await db_session.refresh(codebase)

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
async def test_get_status_failed_with_error_message(client: AsyncClient, db_session):
    """Test retrieving status for a failed codebase with error details."""
    # Create a codebase in FAILED state
    codebase = DBCodebase(
        name="failed-codebase",
        description="A codebase that failed processing",
        source_type=DBSourceType.ZIP,
        source_url=None,
        size_bytes=1500,
        workflow_id="workflow-failed",
        status=DBCodebaseStatus.FAILED,
        total_files=30,
        processed_files=10,
        error_message="Unable to parse Python files: syntax error in module.py",
    )
    db_session.add(codebase)
    await db_session.commit()
    await db_session.refresh(codebase)

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
async def test_get_status_queued(client: AsyncClient, db_session):
    """Test retrieving status for a queued codebase."""
    # Create a codebase (defaults to QUEUED state)
    codebase = DBCodebase(
        name="queued-codebase",
        description="A codebase waiting to be processed",
        source_type=DBSourceType.GITHUB_URL,
        source_url="https://github.com/user/repo",
        size_bytes=0,
        workflow_id="workflow-queued",
        status=DBCodebaseStatus.QUEUED,
    )
    db_session.add(codebase)
    await db_session.commit()
    await db_session.refresh(codebase)

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
async def test_get_status_progress_calculation(client: AsyncClient, db_session):
    """Test that progress is calculated correctly."""
    # Create a codebase with specific progress
    codebase = DBCodebase(
        name="progress-test",
        description="Testing progress calculation",
        source_type=DBSourceType.ZIP,
        source_url=None,
        size_bytes=1000,
        workflow_id="workflow-progress",
        status=DBCodebaseStatus.PROCESSING,
        total_files=200,
        processed_files=75,
    )
    db_session.add(codebase)
    await db_session.commit()
    await db_session.refresh(codebase)

    # Get status
    response = await client.get(f"/api/v1/codebase/{codebase.id}/status")

    assert response.status_code == 200
    result = response.json()

    # Verify progress calculation: (75/200) * 100 = 37.5%
    expected_progress = (75.0 / 200.0) * 100
    assert result["progress"] == expected_progress


@pytest.mark.asyncio
async def test_get_status_zero_division_protection(client: AsyncClient, db_session):
    """Test that progress calculation handles zero total_files gracefully."""
    # Create a codebase with no files
    codebase = DBCodebase(
        name="no-files-codebase",
        description="Codebase with no files",
        source_type=DBSourceType.ZIP,
        source_url=None,
        size_bytes=0,
        workflow_id="workflow-no-files",
        total_files=0,
        processed_files=0,
    )
    db_session.add(codebase)
    await db_session.commit()
    await db_session.refresh(codebase)

    # Get status
    response = await client.get(f"/api/v1/codebase/{codebase.id}/status")

    assert response.status_code == 200
    result = response.json()

    # Progress should be 0 when total_files is 0
    assert result["progress"] == 0.0
