"""Integration tests for codebase management endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.db.codebase import Codebase as DBCodebase, SourceType as DBSourceType, CodebaseStatus as DBCodebaseStatus
from app.models.schemas import SourceType


@pytest.fixture
async def db_session():
    """Create a database session for test setup."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_list_codebases_pagination(client: AsyncClient, db_session):
    """Test listing codebases with pagination."""
    # Create multiple codebases in database
    for i in range(5):
        codebase = DBCodebase(
            name=f"test-codebase-{i}",
            description=f"Test codebase {i}",
            source_type=DBSourceType.ZIP,
            source_url=None,
            size_bytes=1000 * (i + 1),
            workflow_id=f"workflow-{i}",
        )
        db_session.add(codebase)
    await db_session.commit()

    # Test first page with limit 2
    response = await client.get("/api/v1/codebase?page=1&limit=2")

    assert response.status_code == 200
    result = response.json()

    assert "codebases" in result
    assert len(result["codebases"]) == 2
    assert result["total"] == 5
    assert result["page"] == 1
    assert result["limit"] == 2

    # Verify codebase fields
    codebase = result["codebases"][0]
    assert "id" in codebase
    assert "name" in codebase
    assert "description" in codebase
    assert "status" in codebase
    assert "created_at" in codebase


@pytest.mark.asyncio
async def test_list_codebases_default_pagination(client: AsyncClient, db_session):
    """Test that default pagination works correctly."""
    # Create codebases in database
    for i in range(3):
        codebase = DBCodebase(
            name=f"codebase-{i}",
            description=f"Description {i}",
            source_type=DBSourceType.GITHUB_URL,
            source_url=f"https://github.com/user/repo{i}",
            size_bytes=0,
            workflow_id=f"workflow-{i}",
        )
        db_session.add(codebase)
    await db_session.commit()

    # Request without pagination parameters (should use defaults)
    response = await client.get("/api/v1/codebase")

    assert response.status_code == 200
    result = response.json()

    # Default limit is 20, so all 3 should be returned
    assert len(result["codebases"]) == 3
    assert result["total"] == 3
    assert result["page"] == 1


@pytest.mark.asyncio
async def test_list_codebases_empty_page(client: AsyncClient, db_session):
    """Test listing codebases when page is beyond available data."""
    # Create only 1 codebase
    codebase = DBCodebase(
        name="single-codebase",
        description="Only codebase",
        source_type=DBSourceType.ZIP,
        source_url=None,
        size_bytes=1000,
        workflow_id="workflow-single",
    )
    db_session.add(codebase)
    await db_session.commit()

    # Request page 2
    response = await client.get("/api/v1/codebase?page=2&limit=10")

    assert response.status_code == 200
    result = response.json()

    # Should return empty list
    assert len(result["codebases"]) == 0
    assert result["total"] == 1
    assert result["page"] == 2


@pytest.mark.asyncio
async def test_list_codebases_max_limit_enforcement(client: AsyncClient, db_session):
    """Test that the maximum limit of 100 is enforced."""
    # Create codebases in database
    for i in range(5):
        codebase = DBCodebase(
            name=f"codebase-{i}",
            description=f"Description {i}",
            source_type=DBSourceType.ZIP,
            source_url=None,
            size_bytes=1000,
            workflow_id=f"workflow-{i}",
        )
        db_session.add(codebase)
    await db_session.commit()

    # Request with limit > 100
    response = await client.get("/api/v1/codebase?limit=200")

    assert response.status_code == 200
    result = response.json()

    # Limit should be capped at 100
    assert result["limit"] == 100


@pytest.mark.asyncio
async def test_get_codebase_details(client: AsyncClient, db_session):
    """Test retrieving details of a specific codebase."""
    # Create a codebase with specific details
    codebase = DBCodebase(
        name="detailed-codebase",
        description="A codebase with detailed information",
        source_type=DBSourceType.GITHUB_URL,
        source_url="https://github.com/user/awesome-repo",
        size_bytes=5000,
        workflow_id="workflow-detailed",
        status=DBCodebaseStatus.COMPLETED,
        total_files=42,
        processed_files=42,
        primary_language="Python",
        all_languages=["Python", "JavaScript", "HTML"],
    )
    db_session.add(codebase)
    await db_session.commit()
    await db_session.refresh(codebase)

    # Get codebase details
    response = await client.get(f"/api/v1/codebase/{codebase.id}")

    assert response.status_code == 200
    result = response.json()

    # Verify all fields
    assert result["id"] == str(codebase.id)
    assert result["name"] == "detailed-codebase"
    assert result["description"] == "A codebase with detailed information"
    assert result["source_type"] == "github_url"
    assert result["source_url"] == "https://github.com/user/awesome-repo"
    assert result["status"] == "completed"
    assert result["total_files"] == 42
    assert result["processed_files"] == 42
    assert result["primary_language"] == "Python"
    assert result["all_languages"] == ["Python", "JavaScript", "HTML"]
    assert result["size_bytes"] == 5000
    assert result["workflow_id"] == "workflow-detailed"
    assert result["created_at"] is not None
    assert result["updated_at"] is not None


@pytest.mark.asyncio
async def test_get_codebase_not_found(client: AsyncClient):
    """Test that requesting a non-existent codebase returns 404."""
    fake_id = uuid4()

    response = await client.get(f"/api/v1/codebase/{fake_id}")

    assert response.status_code == 404
    result = response.json()
    assert "error" in result
    assert "Codebase not found" in result["error"]["message"]


@pytest.mark.asyncio
async def test_delete_codebase(client: AsyncClient, db_session):
    """Test deleting a codebase."""
    # Create a codebase
    codebase = DBCodebase(
        name="to-be-deleted",
        description="This codebase will be deleted",
        source_type=DBSourceType.ZIP,
        source_url=None,
        size_bytes=1000,
        workflow_id="workflow-delete",
    )
    db_session.add(codebase)
    await db_session.commit()
    await db_session.refresh(codebase)

    # Delete the codebase
    response = await client.delete(f"/api/v1/codebase/{codebase.id}")

    assert response.status_code == 204
    assert response.content == b""

    # Verify codebase is deleted
    get_response = await client.get(f"/api/v1/codebase/{codebase.id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_codebase_not_found(client: AsyncClient):
    """Test that deleting a non-existent codebase returns 404."""
    fake_id = uuid4()

    response = await client.delete(f"/api/v1/codebase/{fake_id}")

    assert response.status_code == 404
    result = response.json()
    assert "error" in result


@pytest.mark.asyncio
async def test_list_codebases_sorting(client: AsyncClient, db_session):
    """Test that codebases are sorted by creation date (newest first)."""
    # Create codebases with different timestamps
    codebase1 = DBCodebase(
        name="first-codebase",
        description="Created first",
        source_type=DBSourceType.ZIP,
        source_url=None,
        size_bytes=1000,
        workflow_id="workflow-1",
    )
    db_session.add(codebase1)
    await db_session.commit()

    codebase2 = DBCodebase(
        name="second-codebase",
        description="Created second",
        source_type=DBSourceType.ZIP,
        source_url=None,
        size_bytes=2000,
        workflow_id="workflow-2",
    )
    db_session.add(codebase2)
    await db_session.commit()

    # List codebases
    response = await client.get("/api/v1/codebase")

    assert response.status_code == 200
    result = response.json()

    # Should return newest first
    assert len(result["codebases"]) == 2
    assert result["codebases"][0]["name"] == "second-codebase"
    assert result["codebases"][1]["name"] == "first-codebase"


@pytest.mark.asyncio
async def test_get_codebase_with_all_optional_fields(client: AsyncClient, db_session):
    """Test retrieving a codebase with all optional fields populated."""
    # Create a comprehensive codebase
    codebase = DBCodebase(
        name="comprehensive-codebase",
        description="A codebase with all fields populated",
        source_type=DBSourceType.ZIP,
        source_url=None,
        size_bytes=10000,
        workflow_id="workflow-comprehensive",
        status=DBCodebaseStatus.PROCESSING,
        total_files=150,
        processed_files=75,
        primary_language="TypeScript",
        all_languages=["TypeScript", "Python", "Rust"],
        error_message=None,
    )
    db_session.add(codebase)
    await db_session.commit()
    await db_session.refresh(codebase)

    # Get codebase details
    response = await client.get(f"/api/v1/codebase/{codebase.id}")

    assert response.status_code == 200
    result = response.json()

    # Verify all fields are present and correct
    assert result["name"] == "comprehensive-codebase"
    assert result["status"] == "processing"
    assert result["total_files"] == 150
    assert result["processed_files"] == 75
    assert result["primary_language"] == "TypeScript"
    assert result["all_languages"] == ["TypeScript", "Python", "Rust"]
    assert result["error_message"] is None
