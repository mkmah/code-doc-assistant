"""In-memory session store for query sessions."""

from datetime import datetime
from typing import AsyncIterator
from uuid import UUID, uuid4

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import MessageType, QueryMessage, QuerySession, Source

settings = get_settings()
logger = get_logger(__name__)


class SessionStore:
    """In-memory store for query sessions (MVP).

    For production with multiple backend replicas, this should be
    replaced with Redis or another distributed cache.
    """

    def __init__(self) -> None:
        """Initialize the session store."""
        # session_id -> QuerySession
        self._sessions: dict[UUID, QuerySession] = {}
        # session_id -> list of messages
        self._messages: dict[UUID, list[QueryMessage]] = {}

    async def create_session(
        self,
        codebase_id: UUID,
    ) -> QuerySession:
        """Create a new query session.

        Args:
            codebase_id: Target codebase for the session

        Returns:
            Created session
        """
        session_id = uuid4()
        now = datetime.utcnow()

        session = QuerySession(
            session_id=session_id,
            codebase_id=codebase_id,
            created_at=now,
            last_active=now,
            message_count=0,
            context_chunks=None,
        )

        self._sessions[session_id] = session
        self._messages[session_id] = []

        logger.info(
            "session_created",
            session_id=str(session_id),
            codebase_id=str(codebase_id),
        )

        return session

    async def get_session(self, session_id: UUID) -> QuerySession | None:
        """Get a session by ID.

        Args:
            session_id: Session ID to retrieve

        Returns:
            Session if found, None otherwise
        """
        return self._sessions.get(session_id)

    async def list_sessions(
        self,
        codebase_id: UUID | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[QuerySession], int]:
        """List sessions, optionally filtered by codebase.

        Args:
            codebase_id: Optional codebase ID to filter by
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Tuple of (sessions list, total count)
        """
        # Filter sessions by codebase_id if provided
        if codebase_id:
            filtered = [
                s for s in self._sessions.values()
                if str(s.codebase_id) == str(codebase_id)
            ]
            sessions = filtered
        else:
            sessions = list(self._sessions.values())

        total = len(sessions)

        # Pagination
        start = (page - 1) * limit
        end = start + limit
        paginated = sessions[start:end]

        return paginated, total

    async def add_message(
        self,
        session_id: UUID,
        role: MessageType,
        content: str,
        citations: list[Source] | None = None,
        retrieved_chunks: list[UUID] | None = None,
        token_count: int | None = None,
    ) -> QueryMessage:
        """Add a message to a session.

        Args:
            session_id: Target session ID
            role: Message role (user/assistant)
            content: Message content
            citations: Source citations (for assistant messages)
            retrieved_chunks: Chunk IDs used for context
            token_count: Token count (for assistant messages)

        Returns:
            Created message

        Raises:
            ValueError: If session not found
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        message_id = uuid4()
        now = datetime.utcnow()

        message = QueryMessage(
            message_id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            timestamp=now,
            citations=citations,
            retrieved_chunks=retrieved_chunks,
            token_count=token_count,
        )

        self._messages[session_id].append(message)

        # Update session
        session.last_active = now
        session.message_count += 1

        logger.debug(
            "message_added",
            session_id=str(session_id),
            message_id=str(message_id),
            role=role.value,
        )

        return message

    async def get_messages(
        self,
        session_id: UUID,
        limit: int | None = None,
    ) -> AsyncIterator[QueryMessage]:
        """Get messages from a session.

        Args:
            session_id: Session ID
            limit: Maximum number of messages to return

        Yields:
            Messages from the session
        """
        messages = self._messages.get(session_id, [])

        if limit:
            messages = messages[-limit:]

        for message in messages:
            yield message

    async def delete_session(self, session_id: UUID) -> bool:
        """Delete a session and its messages.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            del self._messages[session_id]

            logger.info("session_deleted", session_id=str(session_id))
            return True

        return False

    async def cleanup_expired_sessions(self) -> int:
        """Remove sessions older than timeout.

        Returns:
            Number of sessions cleaned up
        """
        now = datetime.utcnow()
        expired_sessions = []

        for session_id, session in self._sessions.items():
            age_seconds = (now - session.last_active).total_seconds()
            if age_seconds > settings.session_timeout_seconds:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            await self.delete_session(session_id)

        if expired_sessions:
            logger.info(
                "expired_sessions_cleaned",
                count=len(expired_sessions),
            )

        return len(expired_sessions)


# Singleton instance
_session_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    """Get the singleton session store instance."""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
