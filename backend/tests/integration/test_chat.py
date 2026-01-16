"""Integration tests for chat endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from app.agents.state import AgentState


def create_mock_state(sample_codebase_id: str, query: str, sources: list = None) -> AgentState:
    """Helper to create a mock AgentState for testing."""
    state = AgentState(
        codebase_id=sample_codebase_id,
        query=query,
    )
    state.error = None
    state.response = ""
    state.sources = sources or []
    return state


@pytest.mark.asyncio
async def test_chat_valid_query(client: AsyncClient, sample_codebase_id):
    """Test submitting a valid query to a codebase."""
    # Mock the agent to return a simple response
    mock_agent = AsyncMock()
    mock_state = create_mock_state(sample_codebase_id, "What does this code do?")
    mock_agent.ainvoke.return_value = mock_state

    with patch("app.api.v1.chat.get_query_agent", return_value=mock_agent):
        response = await client.post(
            "/api/v1/chat",
            json={
                "query": "What does this code do?",
                "codebase_id": sample_codebase_id,
            },
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_chat_streaming_response_format(client: AsyncClient, sample_codebase_id):
    """Test that the chat response uses proper SSE format."""
    # Mock the agent to return a response with sources
    from app.models.schemas import Source

    mock_agent = AsyncMock()
    sources = [
        Source(
            file_path="test.py",
            line_start=1,
            line_end=5,
            snippet="def test():\n    pass",
        )
    ]
    mock_state = create_mock_state(sample_codebase_id, "What does this code do?", sources)
    mock_agent.ainvoke.return_value = mock_state

    with patch("app.api.v1.chat.get_query_agent", return_value=mock_agent):
        response = await client.post(
            "/api/v1/chat",
            json={
                "query": "What does this code do?",
                "codebase_id": sample_codebase_id,
            },
        )

    assert response.status_code == 200

    # Read the streaming response
    content = response.text
    lines = content.split("\n")

    # Check for SSE format (data: {...})
    data_lines = [line for line in lines if line.startswith("data: ")]

    assert len(data_lines) > 0

    # Parse SSE events
    import json

    events = []
    for line in data_lines:
        try:
            data = line[6:]  # Remove "data: " prefix
            # Replace escaped newlines
            data = data.replace("\\n", "\n")
            event = json.loads(data)
            events.append(event)
        except json.JSONDecodeError:
            continue

    # Check event types - should have sources and done events
    event_types = [e.get("type") for e in events]
    assert "sources" in event_types
    assert "done" in event_types

    # Verify sources format
    sources_events = [e for e in events if e.get("type") == "sources"]
    if sources_events:
        sources = sources_events[0].get("sources", [])
        assert len(sources) > 0
        # Check source structure
        source = sources[0]
        assert "file_path" in source
        assert "line_start" in source
        assert "line_end" in source
        assert "snippet" in source


@pytest.mark.asyncio
async def test_chat_citation_accuracy(client: AsyncClient, sample_codebase_id):
    """Test that citations include accurate file and line references."""
    from app.models.schemas import Source

    # Mock the agent to return a response with detailed sources
    mock_agent = AsyncMock()
    sources = [
        Source(
            file_path="calculator.py",
            line_start=10,
            line_end=15,
            snippet="def add(a, b):\n    return a + b",
        ),
        Source(
            file_path="utils.py",
            line_start=5,
            line_end=8,
            snippet="def validate_input(x):\n    return x > 0",
        ),
    ]
    mock_state = create_mock_state(sample_codebase_id, "How does the add function work?", sources)
    mock_agent.ainvoke.return_value = mock_state

    with patch("app.api.v1.chat.get_query_agent", return_value=mock_agent):
        response = await client.post(
            "/api/v1/chat",
            json={
                "query": "How does the add function work?",
                "codebase_id": sample_codebase_id,
            },
        )

    assert response.status_code == 200

    # Parse the response
    content = response.text
    lines = content.split("\n")
    data_lines = [line for line in lines if line.startswith("data: ")]

    import json

    sources_found = []
    for line in data_lines:
        try:
            data = line[6:].replace("\\n", "\n")
            event = json.loads(data)
            if event.get("type") == "sources":
                sources_found = event.get("sources", [])
                break
        except json.JSONDecodeError:
            continue

    # Verify citations are accurate
    assert len(sources_found) == 2

    # Check first source
    source1 = sources_found[0]
    assert source1["file_path"] == "calculator.py"
    assert source1["line_start"] == 10
    assert source1["line_end"] == 15
    assert "add" in source1["snippet"]

    # Check second source
    source2 = sources_found[1]
    assert source2["file_path"] == "utils.py"
    assert source2["line_start"] == 5
    assert source2["line_end"] == 8
    assert "validate_input" in source2["snippet"]


@pytest.mark.asyncio
async def test_chat_with_session_id(client: AsyncClient, sample_codebase_id):
    """Test that chat works with an existing session_id."""
    # First create a session
    from app.services.redis_session_store import get_redis_session_store
    redis_store = get_redis_session_store()

    session = await redis_store.create_session(sample_codebase_id)

    # Mock the agent
    mock_agent = AsyncMock()
    mock_state = create_mock_state(sample_codebase_id, "Follow up question")
    mock_agent.ainvoke.return_value = mock_state

    with patch("app.api.v1.chat.get_query_agent", return_value=mock_agent):
        response = await client.post(
            "/api/v1/chat",
            json={
                "query": "Follow up question",
                "codebase_id": sample_codebase_id,
                "session_id": str(session.session_id),
            },
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_chat_with_invalid_session_id(client: AsyncClient, sample_codebase_id):
    """Test that invalid session_id returns 404."""
    from uuid import uuid4

    fake_session_id = uuid4()

    response = await client.post(
        "/api/v1/chat",
        json={
            "query": "Test question",
            "codebase_id": sample_codebase_id,
            "session_id": fake_session_id,
        },
    )

    assert response.status_code == 404
    result = response.json()
    assert "error" in result


@pytest.mark.asyncio
async def test_chat_creates_new_session_without_session_id(client: AsyncClient, sample_codebase_id):
    """Test that a new session is created when no session_id is provided."""
    # Mock the agent
    mock_agent = AsyncMock()
    mock_state = create_mock_state(sample_codebase_id, "First question")
    mock_agent.ainvoke.return_value = mock_state

    with patch("app.api.v1.chat.get_query_agent", return_value=mock_agent):
        response = await client.post(
            "/api/v1/chat",
            json={
                "query": "First question",
                "codebase_id": sample_codebase_id,
            },
        )

    assert response.status_code == 200

    # Verify session was created in the store
    from app.services.redis_session_store import get_redis_session_store

    redis_store = get_redis_session_store()
    sessions, total = await redis_store.list_sessions(codebase_id=sample_codebase_id)
    assert len(sessions) > 0


@pytest.mark.asyncio
async def test_chat_error_in_agent(client: AsyncClient, sample_codebase_id):
    """Test that agent errors are handled correctly."""
    # Mock the agent to return an error state
    mock_agent = AsyncMock()
    mock_state = create_mock_state(sample_codebase_id, "Test question")
    mock_state.error = "Something went wrong"
    mock_agent.ainvoke.return_value = mock_state

    with patch("app.api.v1.chat.get_query_agent", return_value=mock_agent):
        response = await client.post(
            "/api/v1/chat",
            json={
                "query": "Test question",
                "codebase_id": sample_codebase_id,
            },
        )

    assert response.status_code == 200

    # Parse the error response
    content = response.text
    assert "error" in content.lower()


@pytest.mark.asyncio
async def test_chat_saves_to_session_history(client: AsyncClient, sample_codebase_id):
    """Test that messages are saved to session history."""
    from app.services.redis_session_store import get_redis_session_store

    redis_store = get_redis_session_store()

    # Mock the agent
    mock_agent = AsyncMock()
    mock_state = create_mock_state(sample_codebase_id, "Test question")
    mock_agent.ainvoke.return_value = mock_state

    with patch("app.api.v1.chat.get_query_agent", return_value=mock_agent):
        # Create a session and send a message
        session = await redis_store.create_session(sample_codebase_id)

        await client.post(
            "/api/v1/chat",
            json={
                "query": "Test question",
                "codebase_id": sample_codebase_id,
                "session_id": str(session.session_id),
            },
        )

    # Verify messages were saved
    messages = []
    async for msg in redis_store.get_messages(session.session_id):
        messages.append(msg)
    assert len(messages) >= 2  # user message + assistant message

    # Check user message
    user_msg = [m for m in messages if m.role == "user"][0]
    assert user_msg.content == "Test question"

    # Check assistant message
    assistant_msg = [m for m in messages if m.role == "assistant"][0]
    # Empty response for MVP
    assert assistant_msg.content == ""
