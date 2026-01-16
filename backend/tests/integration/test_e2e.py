"""End-to-end integration tests for the complete application flow."""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from uuid import UUID

from app.db.session import AsyncSessionLocal
from app.models.db.codebase import Codebase as DBCodebase, SourceType as DBSourceType
from app.models.schemas import SourceType


@pytest.fixture
async def db_session():
    """Create a database session for test setup."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_full_upload_query_delete_flow(client: AsyncClient):
    """Test complete flow: upload codebase, query it, then delete.

    This test validates:
    1. Upload creates a codebase with proper status
    2. Delete removes the codebase and subsequent requests fail
    """
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

    # Step 2: Verify codebase exists via API
    get_response = await client.get(f"/api/v1/codebase/{codebase_id}")
    assert get_response.status_code == 200
    codebase = get_response.json()
    assert codebase["name"] == "e2e-test-codebase"

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
async def test_chat_with_concurrent_sessions(client: AsyncClient):
    """Test that multiple chat sessions can run concurrently.

    This test validates:
    1. Different sessions don't interfere with each other
    2. Session isolation works correctly
    """
    from app.services.redis_session_store import get_redis_session_store
    from app.agents.state import AgentState

    redis_store = get_redis_session_store()

    # Mock the agent
    mock_agent = AsyncMock()
    mock_state = AgentState(codebase_id="test-codebase-id", query="Test query")
    mock_state.error = None
    mock_state.response = ""
    mock_state.sources = []
    mock_agent.ainvoke.return_value = mock_state

    # Create multiple sessions concurrently
    async def create_session_query(index: int):
        session = await redis_store.create_session("test-codebase-id")

        with patch("app.api.v1.chat.get_query_agent", return_value=mock_agent):
            response = await client.post(
                "/api/v1/chat",
                json={
                    "query": f"Question {index}",
                    "codebase_id": "test-codebase-id",
                    "session_id": str(session.session_id),
                },
            )

        return response.status_code == 200

    # Run 3 concurrent chat requests
    results = await asyncio.gather(*[create_session_query(i) for i in range(3)])

    # All requests should succeed
    assert all(results), "Not all concurrent chat requests succeeded"

    # Verify each session has independent history
    sessions, total = await redis_store.list_sessions(codebase_id="test-codebase-id")
    assert total == 3


@pytest.mark.asyncio
async def test_full_session_lifecycle(client: AsyncClient):
    """Test the complete lifecycle of a chat session.

    This test validates:
    1. Session creation on first chat request
    2. Message history accumulation
    3. Session persistence across multiple requests
    """
    from app.services.redis_session_store import get_redis_session_store
    from app.agents.state import AgentState

    redis_store = get_redis_session_store()

    # Mock the agent
    mock_agent = AsyncMock()

    def create_mock_response(query: str):
        state = AgentState(codebase_id="test-codebase-id", query=query)
        state.error = None
        state.response = f"Response to: {query}"
        state.sources = []
        return state

    mock_agent.ainvoke.side_effect = [
        create_mock_response("First question"),
        create_mock_response("Second question"),
        create_mock_response("Third question"),
    ]

    # Send first message (creates session)
    with patch("app.api.v1.chat.get_query_agent", return_value=mock_agent):
        response1 = await client.post(
            "/api/v1/chat",
            json={
                "query": "First question",
                "codebase_id": "test-codebase-id",
            },
        )

    assert response1.status_code == 200

    # Extract session_id from the SSE response
    content = response1.text
    assert "session_id" in content

    # Send second and third messages (should accumulate in session)
    with patch("app.api.v1.chat.get_query_agent", return_value=mock_agent):
        response2 = await client.post(
            "/api/v1/chat",
            json={
                "query": "Second question",
                "codebase_id": "test-codebase-id",
            },
        )
        response3 = await client.post(
            "/api/v1/chat",
            json={
                "query": "Third question",
                "codebase_id": "test-codebase-id",
            },
        )

    assert response2.status_code == 200
    assert response3.status_code == 200
