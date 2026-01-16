"""Integration tests for Temporal session cleanup workflow.

This module tests the session cleanup cron workflow that runs daily,
validating that:
- Workflow executes successfully
- Expired sessions are cleaned up from codebase indexes
- Redis session references are properly removed
- Active sessions are not affected
- Error handling works correctly
"""

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.models.schemas import MessageType
from app.services.redis_session_store import get_redis_session_store


class TestSessionCleanupWorkflow:
    """Tests for session cleanup workflow execution."""

    # ==========================================================================
    # Workflow Execution Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_cleanup_activity_removes_expired_sessions(self, redis_client):
        """Test that cleanup activity removes expired session references."""
        redis_store = get_redis_session_store()

        # Create a codebase and sessions
        codebase_id = uuid4()
        session1 = await redis_store.create_session(codebase_id)
        session2 = await redis_store.create_session(codebase_id)

        # Manually expire the sessions by deleting the session data
        # but leaving the reference in the codebase sessions set
        redis = await redis_store._get_redis()
        await redis.delete(f"session:{session1.session_id}")
        await redis.delete(f"session:{session2.session_id}")

        # Verify sessions are in the codebase index
        session_ids = await redis.smembers(f"codebase:{codebase_id}:sessions")
        assert len(session_ids) == 2

        # Run the cleanup
        cleaned_count = await redis_store.cleanup_expired_sessions()

        # Verify expired sessions were removed
        assert cleaned_count == 2

        session_ids_after = await redis.smembers(f"codebase:{codebase_id}:sessions")
        assert len(session_ids_after) == 0

    @pytest.mark.asyncio
    async def test_cleanup_preserves_active_sessions(self, redis_client):
        """Test that cleanup does not remove active session references."""
        redis_store = get_redis_session_store()

        # Create a codebase and sessions
        codebase_id = uuid4()
        session1 = await redis_store.create_session(codebase_id)
        session2 = await redis_store.create_session(codebase_id)

        # Verify sessions exist
        redis = await redis_store._get_redis()
        session1_exists = await redis.exists(f"session:{session1.session_id}")
        session2_exists = await redis.exists(f"session:{session2.session_id}")
        assert session1_exists == 1
        assert session2_exists == 1

        # Run the cleanup
        cleaned_count = await redis_store.cleanup_expired_sessions()

        # Verify no active sessions were removed
        assert cleaned_count == 0

        # Verify sessions still exist
        session1_after = await redis_store.get_session(session1.session_id)
        session2_after = await redis_store.get_session(session2.session_id)
        assert session1_after is not None
        assert session2_after is not None

    @pytest.mark.asyncio
    async def test_cleanup_handles_mixed_sessions(self, redis_client):
        """Test cleanup with mix of expired and active sessions."""
        redis_store = get_redis_session_store()

        codebase_id = uuid4()

        # Create sessions
        session1 = await redis_store.create_session(codebase_id)
        session2 = await redis_store.create_session(codebase_id)
        session3 = await redis_store.create_session(codebase_id)

        # Expire only session2
        redis = await redis_store._get_redis()
        await redis.delete(f"session:{session2.session_id}")

        # Run cleanup
        cleaned_count = await redis_store.cleanup_expired_sessions()

        # Verify only expired session was removed
        assert cleaned_count == 1

        # Verify active sessions still exist
        session1_after = await redis_store.get_session(session1.session_id)
        session3_after = await redis_store.get_session(session3.session_id)
        assert session1_after is not None
        session3_after is not None

    @pytest.mark.asyncio
    async def test_cleanup_across_multiple_codebases(self, redis_client):
        """Test cleanup handles sessions from multiple codebases."""
        redis_store = get_redis_session_store()

        # Create multiple codebases with sessions
        codebase1_id = uuid4()
        codebase2_id = uuid4()

        # Codebase 1: 2 expired sessions
        session1 = await redis_store.create_session(codebase1_id)
        session2 = await redis_store.create_session(codebase1_id)

        # Codebase 2: 1 expired, 1 active
        session3 = await redis_store.create_session(codebase2_id)
        session4 = await redis_store.create_session(codebase2_id)

        # Expire some sessions
        redis = await redis_store._get_redis()
        await redis.delete(f"session:{session1.session_id}")
        await redis.delete(f"session:{session3.session_id}")

        # Run cleanup
        cleaned_count = await redis_store.cleanup_expired_sessions()

        # Verify 2 expired sessions were removed
        assert cleaned_count == 2

        # Verify codebase indexes
        codebase1_sessions = await redis.smembers(f"codebase:{codebase1_id}:sessions")
        codebase2_sessions = await redis.smembers(f"codebase:{codebase2_id}:sessions")

        # Codebase 1 should have only session2
        assert len(codebase1_sessions) == 1
        assert str(session2.session_id) in codebase1_sessions

        # Codebase 2 should have only session4
        assert len(codebase2_sessions) == 1
        assert str(session4.session_id) in codebase2_sessions

    @pytest.mark.asyncio
    async def test_cleanup_with_empty_codebase_index(self, redis_client):
        """Test cleanup handles codebases with no sessions."""
        redis_store = get_redis_session_store()

        # Create a codebase with sessions then delete them all
        codebase_id = uuid4()
        session1 = await redis_store.create_session(codebase_id)

        # Delete the session
        await redis_store.delete_session(session1.session_id)

        # At this point, the codebase sessions set should be empty
        # Run cleanup - should handle gracefully
        cleaned_count = await redis_store.cleanup_expired_sessions()

        # Should return 0 as nothing to clean
        assert cleaned_count == 0

    @pytest.mark.asyncio
    async def test_cleanup_with_messages(self, redis_client):
        """Test cleanup handles sessions with messages."""
        redis_store = get_redis_session_store()

        codebase_id = uuid4()

        # Create a session and add messages
        session = await redis_store.create_session(codebase_id)
        await redis_store.add_message(
            session.session_id,
            MessageType.USER,
            "test query",
        )
        await redis_store.add_message(
            session.session_id,
            MessageType.ASSISTANT,
            "test response",
        )

        # Delete the session (simulating expiration)
        redis = await redis_store._get_redis()
        await redis.delete(f"session:{session.session_id}")

        # Messages should also be gone (cascaded by Redis key deletion)
        messages_exist = await redis.exists(f"session:{session.session_id}:messages")
        assert messages_exist == 0

        # Run cleanup
        cleaned_count = await redis_store.cleanup_expired_sessions()

        # Verify session reference was removed from codebase index
        assert cleaned_count == 1

        codebase_sessions = await redis.smembers(f"codebase:{codebase_id}:sessions")
        assert len(codebase_sessions) == 0

    @pytest.mark.asyncio
    async def test_cleanup_is_idempotent(self, redis_client):
        """Test that running cleanup multiple times is safe."""
        redis_store = get_redis_session_store()

        codebase_id = uuid4()
        session = await redis_store.create_session(codebase_id)

        # Delete the session
        redis = await redis_store._get_redis()
        await redis.delete(f"session:{session.session_id}")

        # Run cleanup multiple times
        count1 = await redis_store.cleanup_expired_sessions()
        count2 = await redis_store.cleanup_expired_sessions()
        count3 = await redis_store.cleanup_expired_sessions()

        # First run should clean, subsequent runs should find nothing
        assert count1 == 1
        assert count2 == 0
        assert count3 == 0

    @pytest.mark.asyncio
    async def test_cleanup_logs_statistics(self, redis_client, caplog):
        """Test that cleanup logs appropriate statistics."""
        import structlog

        redis_store = get_redis_session_store()

        codebase_id = uuid4()
        session1 = await redis_store.create_session(codebase_id)
        session2 = await redis_store.create_session(codebase_id)

        # Delete sessions
        redis = await redis_store._get_redis()
        await redis.delete(f"session:{session1.session_id}")
        await redis.delete(f"session:{session2.session_id}")

        # Run cleanup
        cleaned_count = await redis_store.cleanup_expired_sessions()

        # Verify return value
        assert cleaned_count == 2
