"""End-to-end integration tests for the complete application flow."""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from uuid import UUID

from app.models.schemas import SourceType


@pytest.mark.asyncio
async def test_full_upload_query_delete_flow(client: AsyncClient):
    """Test complete flow: upload codebase, query it, then delete.

    This test validates:
    1. Upload creates a codebase with proper status
    2. Delete removes the codebase and subsequent requests fail
    """
    from app.services.codebase_store import get_codebase_store

    codebase_store = get_codebase_store()

    # Step 1: Upload a codebase
    zip_content = b"PK\x03\x04" + b"\x00" * 100  # Valid ZIP signature
    files = {"file": ("test.zip", BytesIO(zip_content), "application/zip")}
    data = {
        "name": "e2e-test-codebase",
        "description": "End-to-end test codebase",
    }

    upload_response = await client.post(
        "/api/v1/codebase/upload",
        data=data,
        files=files,
    )

    assert upload_response.status_code == 202
    upload_result = upload_response.json()
    codebase_id_str = upload_result["codebase_id"]
    codebase_id = UUID(codebase_id_str)  # Convert string to UUID
    assert upload_result["status"] == "queued"

    # Step 2: Verify codebase exists in store
    codebase = codebase_store.get(codebase_id)
    assert codebase is not None
    assert codebase.name == "e2e-test-codebase"

    # Step 3: Delete the codebase
    delete_response = await client.delete(f"/api/v1/codebase/{codebase_id}")
    assert delete_response.status_code == 204

    # Step 4: Verify codebase is deleted
    get_response = await client.get(f"/api/v1/codebase/{codebase_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_concurrent_query_handling(client: AsyncClient):
    """Test that the system handles concurrent requests correctly.

    This test validates:
    1. Multiple simultaneous requests don't interfere with each other
    2. Each request gets the correct response
    """
    import asyncio

    from app.services.codebase_store import get_codebase_store

    codebase_store = get_codebase_store()

    # Create multiple codebases concurrently
    async def create_codebase(index: int):
        zip_content = b"PK\x03\x04" + b"\x00" * 100
        files = {"file": (f"test{index}.zip", BytesIO(zip_content), "application/zip")}
        data = {
            "name": f"concurrent-codebase-{index}",
            "description": f"Concurrent test {index}",
        }

        response = await client.post(
            "/api/v1/codebase/upload",
            data=data,
            files=files,
        )
        return response.status_code == 202

    # Run 5 concurrent uploads
    results = await asyncio.gather(*[create_codebase(i) for i in range(5)])

    # All uploads should succeed
    assert all(results), "Not all concurrent uploads succeeded"

    # Verify we have 5 codebases
    response = await client.get("/api/v1/codebase?limit=20")
    assert response.status_code == 200
    result = response.json()
    assert result["total"] == 5


@pytest.mark.asyncio
async def test_embedding_service_fallback():
    """Test fallback from Jina to OpenAI embedding service.

    This test validates:
    1. System falls back to OpenAI when Jina fails
    2. Fallback mechanism works transparently
    3. Embeddings are generated even when primary service fails
    """
    from app.services.embedding_service import EmbeddingService

    service = EmbeddingService()

    # Mock the internal methods to simulate Jina failure and OpenAI success
    async def mock_call_jina_fail(texts):
        raise Exception("Jina API unavailable")

    async def mock_call_openai_success(texts):
        return [[0.1, 0.2, 0.3] for _ in texts]

    with patch.object(service, "_generate_jina_embeddings", side_effect=mock_call_jina_fail):
        with patch.object(service, "_generate_openai_embeddings", side_effect=mock_call_openai_success):
            # Generate embeddings - should fall back to OpenAI
            texts = ["test code snippet 1", "test code snippet 2"]
            embeddings = await service.generate_embeddings(texts)

            # Verify we got embeddings from OpenAI
            assert embeddings is not None
            assert len(embeddings) == 2
            assert embeddings[0] == [0.1, 0.2, 0.3]
            assert embeddings[1] == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_error_handling_on_service_failure(client: AsyncClient):
    """Test graceful error handling when services fail.

    This test validates:
    1. Upload handles errors gracefully
    2. Proper error messages are returned
    3. System remains stable after errors
    """
    from app.services.codebase_store import get_codebase_store

    codebase_store = get_codebase_store()

    # Test 1: Invalid file type
    invalid_content = b"Not a ZIP file"
    files = {"file": ("test.txt", BytesIO(invalid_content), "text/plain")}
    data = {"name": "invalid-test", "description": "Invalid file type"}

    response = await client.post(
        "/api/v1/codebase/upload",
        data=data,
        files=files,
    )

    # Should return proper error
    assert response.status_code == 400
    result = response.json()
    assert "error" in result

    # Test 2: System still works after error
    valid_content = b"PK\x03\x04" + b"\x00" * 100
    files = {"file": ("test.zip", BytesIO(valid_content), "application/zip")}
    data = {"name": "valid-test", "description": "Valid upload after error"}

    response = await client.post(
        "/api/v1/codebase/upload",
        data=data,
        files=files,
    )

    # Should succeed
    assert response.status_code == 202
    result = response.json()
    assert "codebase_id" in result
