"""Integration tests for codebase API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_ready_check_fails_without_chromadb(client: AsyncClient):
    """Test readiness check fails when ChromaDB is not available."""
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    # Should be not_ready since ChromaDB is not running in tests
    assert data["status"] == "not_ready"


@pytest.mark.asyncio
async def test_get_codebase_not_found(client: AsyncClient):
    """Test getting a non-existent codebase."""
    response = await client.get("/api/v1/codebase/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_upload_codebase_missing_both_inputs(client: AsyncClient):
    """Test uploading with neither file nor GitHub URL."""
    response = await client.post(
        "/api/v1/codebase/upload",
        data={"name": "test-codebase"},
    )
    # Returns 400 (Bad Request) when both file and github_url are missing
    assert response.status_code == 400
    data = response.json()
    assert "error" in data or "detail" in data
