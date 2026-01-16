"""Async Redis-based session store for distributed deployment.

Replaces the in-memory SessionStore with Redis for production multi-instance deployments.
All operations are async for non-blocking Redis access.
"""

import json
from collections.abc import AsyncIterator
from datetime import datetime
from uuid import UUID

from redis.asyncio import ConnectionPool, Redis

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import MessageType, QueryMessage, QuerySession, Source

settings = get_settings()
logger = get_logger(__name__)


class RedisSessionStore:
    """Async Redis-based session store for distributed deployment.

    Features:
    - Async operations for non-blocking Redis access
    - Automatic TTL-based expiration (7-day default)
    - Session indexing by codebase for bulk operations
    - Atomic operations using Redis pipelines

    Redis Data Structure:
    - session:{session_id} -> Hash of session metadata
    - session:{session_id}:messages -> List of message JSON
    - codebase:{codebase_id}:sessions -> Set of session IDs
    - session:counter -> Global counter for session IDs
    - session:{session_id}:message_counter -> Per-session message counter
    """

    def __init__(self) -> None:
        """Initialize Redis session store."""
        self._pool: ConnectionPool | None = None
        self._redis: Redis | None = None

    async def _get_redis(self) -> Redis:
        """Get or create async Redis connection.

        Returns:
            Async Redis client
        """
        if self._redis is None:
            self._pool = ConnectionPool.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.redis_pool_size,
            )
            self._redis = Redis(connection_pool=self._pool)
        return self._redis

    async def create_session(self, codebase_id: UUID) -> QuerySession:
        """Create a new session.

        Args:
            codebase_id: Target codebase UUID

        Returns:
            Created QuerySession
        """
        redis = await self._get_redis()
        # session_id = UUID(hex=await redis.incr("session:counter"))
        import uuid

        session_id = uuid.uuid4()
        now = datetime.utcnow().isoformat()

        session_data = {
            "session_id": str(session_id),
            "codebase_id": str(codebase_id),
            "created_at": now,
            "last_active": now,
            "message_count": "0",
            "context_chunks": "",
        }

        pipe = redis.pipeline()
        pipe.hset(f"session:{session_id}", mapping={k: v or "" for k, v in session_data.items()})
        pipe.expire(f"session:{session_id}", settings.redis_ttl_seconds)
        pipe.sadd(f"codebase:{codebase_id}:sessions", str(session_id))
        await pipe.execute()

        logger.info(
            "session_created",
            session_id=str(session_id),
            codebase_id=str(codebase_id),
        )

        return QuerySession(
            session_id=session_id,
            codebase_id=codebase_id,
            created_at=datetime.fromisoformat(now),
            last_active=datetime.fromisoformat(now),
            message_count=0,
            context_chunks=None,
        )

    async def get_session(self, session_id: UUID) -> QuerySession | None:
        """Get session by ID.

        Args:
            session_id: Session UUID

        Returns:
            QuerySession or None if not found
        """
        redis = await self._get_redis()
        data = await redis.hgetall(f"session:{session_id}")

        if not data:
            return None

        return QuerySession(
            session_id=UUID(data["session_id"]),
            codebase_id=UUID(data["codebase_id"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_active=datetime.fromisoformat(data["last_active"]),
            message_count=int(data["message_count"]),
            context_chunks=json.loads(data["context_chunks"])
            if data.get("context_chunks")
            else None,
        )

    async def get_or_create_session(
        self, codebase_id: UUID, session_id: UUID | None = None
    ) -> QuerySession:
        """Get existing session or create a new one.

        Args:
            codebase_id: Target codebase UUID
            session_id: Optional existing session ID

        Returns:
            QuerySession (existing or newly created)
        """
        if session_id:
            session = await self.get_session(session_id)
            if session:
                return session
        return await self.create_session(codebase_id)

    async def add_message(
        self,
        session_id: UUID,
        role: MessageType,
        content: str,
        citations: list[Source] | None = None,
        retrieved_chunks: list[UUID] | None = None,
        token_count: int | None = None,
    ) -> QueryMessage:
        """Add message to session.

        Args:
            session_id: Session UUID
            role: Message role (user/assistant)
            content: Message content
            citations: Optional list of sources
            retrieved_chunks: Optional list of chunk IDs
            token_count: Optional token count

        Returns:
            Created QueryMessage
        """
        redis = await self._get_redis()
        # message_id = UUID(hex=await redis.incr(f"session:{session_id}:message_counter"))
        import uuid

        message_id = uuid.uuid4()
        now = datetime.utcnow().isoformat()

        message_data = {
            "message_id": str(message_id),
            "session_id": str(session_id),
            "role": role.value,
            "content": content,
            "timestamp": now,
            "citations": json.dumps([c.model_dump() for c in citations]) if citations else "",
            "retrieved_chunks": json.dumps([str(c) for c in retrieved_chunks])
            if retrieved_chunks
            else "",
            "token_count": str(token_count) if token_count else "",
        }

        pipe = redis.pipeline()
        pipe.lpush(f"session:{session_id}:messages", json.dumps(message_data))
        pipe.hincrby(f"session:{session_id}", "message_count", 1)
        pipe.hset(f"session:{session_id}", "last_active", now)
        pipe.expire(f"session:{session_id}", settings.redis_ttl_seconds)
        await pipe.execute()

        return QueryMessage(
            message_id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            timestamp=datetime.fromisoformat(now),
            citations=citations,
            retrieved_chunks=retrieved_chunks,
            token_count=token_count,
        )

    async def get_messages(
        self, session_id: UUID, limit: int | None = None
    ) -> AsyncIterator[QueryMessage]:
        """Get messages from session (most recent first).

        Args:
            session_id: Session UUID
            limit: Optional max number of messages

        Yields:
            QueryMessage objects
        """
        redis = await self._get_redis()
        stop = limit or -1
        messages_json = await redis.lrange(f"session:{session_id}:messages", 0, stop)

        for msg_json in messages_json:
            data = json.loads(msg_json)
            yield QueryMessage(
                message_id=UUID(data["message_id"]),
                session_id=UUID(data["session_id"]),
                role=MessageType(data["role"]),
                content=data["content"],
                timestamp=datetime.fromisoformat(data["timestamp"]),
                citations=[Source(**c) for c in json.loads(data["citations"])]
                if data.get("citations")
                else None,
                retrieved_chunks=[UUID(c) for c in json.loads(data["retrieved_chunks"])]
                if data.get("retrieved_chunks")
                else None,
                token_count=int(data["token_count"]) if data.get("token_count") else None,
            )

    async def save_conversation_turn(
        self,
        session_id: UUID,
        query: str,
        response: str,
        sources: list[Source] | None = None,
        retrieved_chunks: list[UUID] | None = None,
        token_count: int | None = None,
    ) -> tuple[QueryMessage, QueryMessage]:
        """Save a complete conversation turn (user + assistant messages).

        Args:
            session_id: Session UUID
            query: User query
            response: Assistant response
            sources: Optional sources from response
            retrieved_chunks: Optional retrieved chunk IDs
            token_count: Optional token count

        Returns:
            Tuple of (user_message, assistant_message)
        """
        user_message = await self.add_message(
            session_id=session_id,
            role=MessageType.USER,
            content=query,
        )

        assistant_message = await self.add_message(
            session_id=session_id,
            role=MessageType.ASSISTANT,
            content=response,
            citations=sources,
            retrieved_chunks=retrieved_chunks,
            token_count=token_count,
        )

        return user_message, assistant_message

    async def delete_session(self, session_id: UUID) -> bool:
        """Delete session and all associated messages.

        Args:
            session_id: Session UUID

        Returns:
            True if deleted, False if not found
        """
        redis = await self._get_redis()
        session = await self.get_session(session_id)

        if not session:
            return False

        pipe = redis.pipeline()
        pipe.delete(f"session:{session_id}")
        pipe.delete(f"session:{session_id}:messages")
        pipe.srem(f"codebase:{session.codebase_id}:sessions", str(session_id))
        await pipe.execute()

        logger.info("session_deleted", session_id=str(session_id))
        return True

    async def delete_sessions_by_codebase(self, codebase_id: UUID) -> int:
        """Delete all sessions associated with a codebase.

        Args:
            codebase_id: Codebase UUID

        Returns:
            Number of sessions deleted
        """
        redis = await self._get_redis()
        session_ids = await redis.smembers(f"codebase:{codebase_id}:sessions")

        count = 0
        for session_id_str in session_ids:
            if await self.delete_session(UUID(session_id_str)):
                count += 1

        await redis.delete(f"codebase:{codebase_id}:sessions")

        logger.info(
            "codebase_sessions_deleted",
            codebase_id=str(codebase_id),
            count=count,
        )

        return count

    async def list_sessions(
        self,
        codebase_id: UUID | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[QuerySession], int]:
        """List sessions with optional codebase filter and pagination.

        Args:
            codebase_id: Optional codebase UUID to filter by
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Tuple of (list of sessions, total count)
        """
        redis = await self._get_redis()

        if codebase_id:
            # Get sessions for specific codebase
            session_ids = await redis.smembers(f"codebase:{codebase_id}:sessions")
            sessions = []
            for session_id_str in session_ids:
                session = await self.get_session(UUID(session_id_str))
                if session:
                    sessions.append(session)

            total = len(sessions)
            start = (page - 1) * limit
            end = start + limit
            paginated = sessions[start:end]

            return paginated, total
        else:
            # Get all sessions (requires scanning)
            pattern = "session:*"
            sessions = []
            async for key in redis.scan_iter(match=pattern):
                if not key.endswith(":messages") and not key.endswith(":message_counter"):
                    session_id_str = key.split(":")[1]
                    try:
                        session = await self.get_session(UUID(session_id_str))
                        if session:
                            sessions.append(session)
                    except ValueError:
                        continue

            # Sort by created_at descending
            sessions.sort(key=lambda s: s.created_at, reverse=True)

            total = len(sessions)
            start = (page - 1) * limit
            end = start + limit
            paginated = sessions[start:end]

            return paginated, total

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions from codebase indexes.

        Redis handles TTL automatically for session data, but we need
        to clean up stale entries in the codebase:{id}:sessions sets.

        Returns:
            Number of stale entries removed
        """
        redis = await self._get_redis()
        pattern = "codebase:*:sessions"
        count = 0

        async for key in redis.scan_iter(match=pattern):
            codebase_id = key.split(":")[1]
            session_ids = await redis.smembers(key)

            # Check if each session still exists
            for session_id_str in session_ids:
                if not await redis.exists(f"session:{session_id_str}"):
                    await redis.srem(key, session_id_str)
                    count += 1

        if count > 0:
            logger.info("expired_sessions_cleaned", count=count)

        return count

    async def close(self) -> None:
        """Close Redis connection pool.

        Should be called on application shutdown.
        """
        if self._redis:
            await self._redis.close()
            self._redis = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
            logger.info("redis_connection_closed")


# Singleton instance
_redis_session_store: RedisSessionStore | None = None


def get_redis_session_store() -> RedisSessionStore:
    """Get the singleton Redis session store instance.

    Returns:
        RedisSessionStore instance
    """
    global _redis_session_store
    if _redis_session_store is None:
        _redis_session_store = RedisSessionStore()
    return _redis_session_store
