"""Unit tests for Redis session store."""

import asyncio
from datetime import datetime
from uuid import UUID, uuid4

import pytest

from app.models.schemas import MessageType, QuerySession, Source
from app.services.redis_session_store import RedisSessionStore, get_redis_session_store


@pytest.fixture
async def session_store() -> RedisSessionStore:
    """Create a fresh Redis session store for each test."""
    store = RedisSessionStore()
    # Initialize Redis connection
    await store._get_redis()
    yield store
    # Cleanup
    await store.close()


@pytest.fixture
def sample_codebase_id() -> UUID:
    """Sample codebase ID for testing."""
    return uuid4()


@pytest.mark.asyncio
async def test_create_session(session_store: RedisSessionStore, sample_codebase_id: UUID) -> None:
    """Test creating a new session."""
    session = await session_store.create_session(sample_codebase_id)

    assert isinstance(session, QuerySession)
    assert session.codebase_id == sample_codebase_id
    assert session.session_id != UUID("00000000-0000-0000-0000-000000000000")
    assert session.message_count == 0
    assert isinstance(session.created_at, datetime)
    assert isinstance(session.last_active, datetime)


@pytest.mark.asyncio
async def test_get_session_existing(session_store: RedisSessionStore, sample_codebase_id: UUID) -> None:
    """Test retrieving an existing session."""
    created = await session_store.create_session(sample_codebase_id)
    retrieved = await session_store.get_session(created.session_id)

    assert retrieved is not None
    assert retrieved.session_id == created.session_id
    assert retrieved.codebase_id == sample_codebase_id


@pytest.mark.asyncio
async def test_get_session_nonexistent(session_store: RedisSessionStore) -> None:
    """Test retrieving a non-existent session."""
    fake_id = uuid4()
    result = await session_store.get_session(fake_id)

    assert result is None


@pytest.mark.asyncio
async def test_add_message(session_store: RedisSessionStore, sample_codebase_id: UUID) -> None:
    """Test adding a message to a session."""
    session = await session_store.create_session(sample_codebase_id)

    message = await session_store.add_message(
        session_id=session.session_id,
        role=MessageType.USER,
        content="How does authentication work?",
    )

    assert message.session_id == session.session_id
    assert message.role == MessageType.USER
    assert message.content == "How does authentication work?"
    assert isinstance(message.timestamp, datetime)

    # Verify session was updated
    updated_session = await session_store.get_session(session.session_id)
    assert updated_session is not None
    assert updated_session.message_count == 1


@pytest.mark.asyncio
async def test_add_message_with_citations(session_store: RedisSessionStore, sample_codebase_id: UUID) -> None:
    """Test adding a message with source citations."""
    session = await session_store.create_session(sample_codebase_id)

    citations = [
        Source(
            file_path="src/auth.py",
            line_start=10,
            line_end=20,
            snippet="def authenticate():",
            confidence=0.95,
        )
    ]

    message = await session_store.add_message(
        session_id=session.session_id,
        role=MessageType.ASSISTANT,
        content="Authentication is handled by the authenticate() function.",
        citations=citations,
    )

    assert message.role == MessageType.ASSISTANT
    assert len(message.citations) == 1
    assert message.citations[0].file_path == "src/auth.py"


@pytest.mark.asyncio
async def test_get_messages(session_store: RedisSessionStore, sample_codebase_id: UUID) -> None:
    """Test retrieving messages from a session."""
    session = await session_store.create_session(sample_codebase_id)

    # Add multiple messages
    await session_store.add_message(
        session_id=session.session_id,
        role=MessageType.USER,
        content="Question 1",
    )
    await session_store.add_message(
        session_id=session.session_id,
        role=MessageType.ASSISTANT,
        content="Answer 1",
    )
    await session_store.add_message(
        session_id=session.session_id,
        role=MessageType.USER,
        content="Question 2",
    )

    # Get all messages
    messages = []
    async for msg in session_store.get_messages(session.session_id):
        messages.append(msg)

    # Redis stores messages in reverse order (most recent first)
    assert len(messages) == 3


@pytest.mark.asyncio
async def test_get_messages_with_limit(session_store: RedisSessionStore, sample_codebase_id: UUID) -> None:
    """Test retrieving limited number of most recent messages."""
    session = await session_store.create_session(sample_codebase_id)

    # Add 5 messages
    for i in range(5):
        await session_store.add_message(
            session_id=session.session_id,
            role=MessageType.USER,
            content=f"Message {i}",
        )

    # Get last 3 messages
    messages = []
    async for msg in session_store.get_messages(session.session_id, limit=3):
        messages.append(msg)

    assert len(messages) == 3


@pytest.mark.asyncio
async def test_delete_session(session_store: RedisSessionStore, sample_codebase_id: UUID) -> None:
    """Test deleting a session."""
    session = await session_store.create_session(sample_codebase_id)
    session_id = session.session_id

    # Verify session exists
    assert await session_store.get_session(session_id) is not None

    # Delete session
    result = await session_store.delete_session(session_id)
    assert result is True

    # Verify session is gone
    assert await session_store.get_session(session_id) is None


@pytest.mark.asyncio
async def test_delete_session_nonexistent(session_store: RedisSessionStore) -> None:
    """Test deleting a non-existent session."""
    fake_id = uuid4()
    result = await session_store.delete_session(fake_id)

    assert result is False


@pytest.mark.asyncio
async def test_delete_sessions_by_codebase(session_store: RedisSessionStore) -> None:
    """Test deleting all sessions for a specific codebase."""
    codebase_id_1 = uuid4()
    codebase_id_2 = uuid4()

    # Create sessions for codebase 1
    sessions_1 = []
    for _ in range(3):
        session = await session_store.create_session(codebase_id_1)
        sessions_1.append(session)

    # Create sessions for codebase 2
    sessions_2 = []
    for _ in range(2):
        session = await session_store.create_session(codebase_id_2)
        sessions_2.append(session)

    # Delete all sessions for codebase 1
    deleted_count = await session_store.delete_sessions_by_codebase(codebase_id_1)

    # Verify 3 sessions were deleted
    assert deleted_count == 3

    # Verify codebase 1 sessions are gone
    for session in sessions_1:
        assert await session_store.get_session(session.session_id) is None

    # Verify codebase 2 sessions still exist
    for session in sessions_2:
        assert await session_store.get_session(session.session_id) is not None


@pytest.mark.asyncio
async def test_save_conversation_turn(session_store: RedisSessionStore, sample_codebase_id: UUID) -> None:
    """Test saving a complete conversation turn (query + response)."""
    session = await session_store.create_session(sample_codebase_id)

    citations = [
        Source(
            file_path="src/auth.py",
            line_start=10,
            line_end=20,
            snippet="def authenticate():",
            confidence=0.95,
        )
    ]

    # Save a conversation turn
    await session_store.save_conversation_turn(
        session_id=session.session_id,
        query="How does authentication work?",
        response="Authentication is handled by the authenticate() function.",
        sources=citations,
    )

    # Verify messages were saved
    messages = []
    async for msg in session_store.get_messages(session.session_id):
        messages.append(msg)

    assert len(messages) == 2
    assert messages[0].role == MessageType.ASSISTANT
    assert messages[1].role == MessageType.USER


@pytest.mark.asyncio
async def test_list_sessions_by_codebase(session_store: RedisSessionStore) -> None:
    """Test listing sessions filtered by codebase."""
    codebase_id_1 = uuid4()
    codebase_id_2 = uuid4()

    # Create sessions for codebase 1
    for _ in range(3):
        await session_store.create_session(codebase_id_1)

    # Create sessions for codebase 2
    for _ in range(2):
        await session_store.create_session(codebase_id_2)

    # List sessions for codebase 1
    sessions, total = await session_store.list_sessions(codebase_id=codebase_id_1)

    assert total == 3
    assert len(sessions) == 3
    assert all(s.codebase_id == codebase_id_1 for s in sessions)


@pytest.mark.asyncio
async def test_list_sessions_pagination(session_store: RedisSessionStore) -> None:
    """Test session listing with pagination."""
    codebase_id = uuid4()

    # Create 5 sessions
    for _ in range(5):
        await session_store.create_session(codebase_id)

    # Get first page
    page1, total = await session_store.list_sessions(codebase_id=codebase_id, page=1, limit=2)
    assert total == 5
    assert len(page1) == 2

    # Get second page
    page2, _ = await session_store.list_sessions(codebase_id=codebase_id, page=2, limit=2)
    assert len(page2) == 2

    # Verify different sessions
    assert page1[0].session_id != page2[0].session_id


@pytest.mark.asyncio
async def test_thread_safety_concurrent_create(session_store: RedisSessionStore) -> None:
    """Test that concurrent session creation is thread-safe."""
    codebase_id = uuid4()

    # Create 10 sessions concurrently
    tasks = [session_store.create_session(codebase_id) for _ in range(10)]
    sessions = await asyncio.gather(*tasks)

    # Verify all sessions were created with unique IDs
    session_ids = [s.session_id for s in sessions]
    assert len(set(session_ids)) == 10
    assert all(s.codebase_id == codebase_id for s in sessions)


@pytest.mark.asyncio
async def test_get_redis_session_store_singleton() -> None:
    """Test that get_redis_session_store returns singleton instance."""
    store1 = get_redis_session_store()
    store2 = get_redis_session_store()

    assert store1 is store2


@pytest.mark.asyncio
async def test_get_or_create_session_existing(session_store: RedisSessionStore, sample_codebase_id: UUID) -> None:
    """Test get_or_create_session with existing session."""
    created = await session_store.create_session(sample_codebase_id)

    # Get existing session
    retrieved = await session_store.get_or_create_session(sample_codebase_id, created.session_id)

    assert retrieved.session_id == created.session_id


@pytest.mark.asyncio
async def test_get_or_create_session_new(session_store: RedisSessionStore, sample_codebase_id: UUID) -> None:
    """Test get_or_create_session creates new session if ID not provided."""
    session = await session_store.get_or_create_session(sample_codebase_id, None)

    assert session.codebase_id == sample_codebase_id
    assert session.session_id != UUID("00000000-0000-0000-0000-000000000000")


@pytest.mark.asyncio
async def test_cleanup_expired_sessions(session_store: RedisSessionStore) -> None:
    """Test cleanup of expired sessions (Redis handles TTL automatically)."""
    # Redis automatically handles TTL, so this test verifies the method runs
    cleaned_count = await session_store.cleanup_expired_sessions()
    assert cleaned_count == 0  # No sessions to clean
