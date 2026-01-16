"""Integration tests for chat endpoint with session history."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def test_client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_codebase_id() -> str:
    """Mock codebase ID for testing."""
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def mock_session_id() -> str:
    """Mock session ID for testing."""
    return "660e8400-e29b-41d4-a716-446655440000"


class TestChatSessionCreation:
    """Tests for session creation during chat."""

    @pytest.mark.asyncio
    async def test_chat_creates_new_session_when_no_session_id(
        self,
        test_client: TestClient,
        mock_codebase_id: str,
    ) -> None:
        """Test that a new session is created when no session_id is provided."""
        # Mock the agent to return a simple response
        with patch("app.api.v1.chat.get_query_agent") as mock_agent:
            mock_state = MagicMock()
            mock_state.response = "Authentication is handled by JWT tokens."
            mock_state.sources = []
            mock_state.error = None
            mock_agent.return_value.ainvoke = AsyncMock(return_value=mock_state)

            response = test_client.post(
                "/api/v1/chat",
                json={
                    "codebase_id": mock_codebase_id,
                    "query": "How does authentication work?",
                },
            )

            # The response is streaming, so we check for 200
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_uses_existing_session(
        self,
        test_client: TestClient,
        mock_codebase_id: str,
        mock_session_id: str,
    ) -> None:
        """Test that an existing session is used when session_id is provided."""
        with patch("app.api.v1.chat.get_query_agent") as mock_agent:
            mock_state = MagicMock()
            mock_state.response = "As I mentioned before, authentication uses JWT."
            mock_state.sources = []
            mock_state.error = None
            mock_agent.return_value.ainvoke = AsyncMock(return_value=mock_state)

            response = test_client.post(
                "/api/v1/chat",
                json={
                    "codebase_id": mock_codebase_id,
                    "query": "What about refresh tokens?",
                    "session_id": mock_session_id,
                },
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_returns_404_for_invalid_session(
        self,
        test_client: TestClient,
        mock_codebase_id: str,
    ) -> None:
        """Test that 404 is returned when an invalid session_id is provided."""
        # Use a session ID that doesn't exist
        invalid_session_id = "990e8400-e29b-41d4-a716-446655440999"

        response = test_client.post(
            "/api/v1/chat",
            json={
                "codebase_id": mock_codebase_id,
                "query": "Test query",
                "session_id": invalid_session_id,
            },
        )

        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]


class TestChatSessionPersistence:
    """Tests for conversation turn persistence."""

    @pytest.mark.asyncio
    async def test_chat_saves_user_message_to_session(
        self,
        test_client: TestClient,
        mock_codebase_id: str,
    ) -> None:
        """Test that user messages are saved to the session."""
        with patch("app.api.v1.chat.get_query_agent") as mock_agent:
            mock_state = MagicMock()
            mock_state.response = "Here's the answer."
            mock_state.sources = []
            mock_state.error = None
            mock_agent.return_value.ainvoke = AsyncMock(return_value=mock_state)

            with patch("app.api.v1.chat.session_store") as mock_store:
                mock_session = MagicMock()
                mock_session.session_id = mock_codebase_id
                mock_store.create_session = AsyncMock(return_value=mock_session)
                mock_store.add_message = AsyncMock()

                response = test_client.post(
                    "/api/v1/chat",
                    json={
                        "codebase_id": mock_codebase_id,
                        "query": "What is the entry point?",
                    },
                )

                assert response.status_code == 200
                # Verify add_message was called for user message
                mock_store.add_message.assert_any_call(
                    session_id=mock_session.session_id,
                    role="user",
                    content="What is the entry point?",
                )

    @pytest.mark.asyncio
    async def test_chat_saves_assistant_message_to_session(
        self,
        test_client: TestClient,
        mock_codebase_id: str,
    ) -> None:
        """Test that assistant responses are saved to the session."""
        with patch("app.api.v1.chat.get_query_agent") as mock_agent:
            mock_state = MagicMock()
            mock_state.response = "The entry point is main()."
            mock_state.sources = []
            mock_state.error = None
            mock_agent.return_value.ainvoke = AsyncMock(return_value=mock_state)

            with patch("app.api.v1.chat.session_store") as mock_store:
                mock_session = MagicMock()
                mock_session.session_id = mock_codebase_id
                mock_store.create_session = AsyncMock(return_value=mock_session)
                mock_store.add_message = AsyncMock()

                response = test_client.post(
                    "/api/v1/chat",
                    json={
                        "codebase_id": mock_codebase_id,
                        "query": "What is the entry point?",
                    },
                )

                assert response.status_code == 200
                # Verify add_message was called for assistant message
                mock_store.add_message.assert_any_call(
                    session_id=mock_session.session_id,
                    role="assistant",
                    content="The entry point is main().",
                    citations=mock_state.sources,
                )


class TestChatMultiTurnConversation:
    """Tests for multi-turn conversation context."""

    @pytest.mark.asyncio
    async def test_conversation_context_maintained_across_turns(
        self,
        test_client: TestClient,
        mock_codebase_id: str,
    ) -> None:
        """Test that conversation context is maintained across multiple turns."""
        with patch("app.api.v1.chat.get_query_agent") as mock_agent:
            # First turn
            mock_state_1 = MagicMock()
            mock_state_1.response = "Authentication uses JWT tokens with a 24-hour expiration."
            mock_state_1.sources = []
            mock_state_1.error = None
            mock_agent.return_value.ainvoke = AsyncMock(return_value=mock_state_1)

            with patch("app.api.v1.chat.session_store") as mock_store:
                mock_session = MagicMock()
                mock_session.session_id = mock_codebase_id
                mock_store.create_session = AsyncMock(return_value=mock_session)
                mock_store.get_session = AsyncMock(return_value=mock_session)
                mock_store.add_message = AsyncMock()

                # First message
                response1 = test_client.post(
                    "/api/v1/chat",
                    json={
                        "codebase_id": mock_codebase_id,
                        "query": "How does authentication work?",
                    },
                )
                assert response1.status_code == 200

                # Verify session was created
                mock_store.create_session.assert_called_once()

                # Second turn with follow-up question
                response2 = test_client.post(
                    "/api/v1/chat",
                    json={
                        "codebase_id": mock_codebase_id,
                        "query": "What happens when the token expires?",
                        "session_id": mock_session.session_id,
                    },
                )
                assert response2.status_code == 200

                # Verify existing session was retrieved
                mock_store.get_session.assert_called_with(mock_session.session_id)

    @pytest.mark.asyncio
    async def test_session_history_loaded_by_agent(
        self,
        test_client: TestClient,
        mock_codebase_id: str,
        mock_session_id: str,
    ) -> None:
        """Test that session history is loaded and passed to the agent."""
        with patch("app.api.v1.chat.get_query_agent") as mock_agent:
            mock_state = MagicMock()
            mock_state.response = "Based on our previous discussion..."
            mock_state.sources = []
            mock_state.error = None
            mock_agent.return_value.ainvoke = AsyncMock(return_value=mock_state)

            with patch("app.api.v1.chat.session_store") as mock_store:
                mock_session = MagicMock()
                mock_session.session_id = mock_session_id
                mock_store.get_session = AsyncMock(return_value=mock_session)
                mock_store.add_message = AsyncMock()

                response = test_client.post(
                    "/api/v1/chat",
                    json={
                        "codebase_id": mock_codebase_id,
                        "query": "Can you elaborate?",
                        "session_id": mock_session_id,
                    },
                )

                assert response.status_code == 200
                # Verify session was retrieved
                mock_store.get_session.assert_called_once()


class TestChatSessionSources:
    """Tests for source citation handling in sessions."""

    @pytest.mark.asyncio
    async def test_chat_saves_sources_to_session(
        self,
        test_client: TestClient,
        mock_codebase_id: str,
    ) -> None:
        """Test that source citations are saved to the session."""
        with patch("app.api.v1.chat.get_query_agent") as mock_agent:
            from app.models.schemas import Source

            mock_source = Source(
                file_path="src/auth.py",
                line_start=42,
                line_end=50,
                snippet="def authenticate():",
                confidence=0.95,
            )

            mock_state = MagicMock()
            mock_state.response = "Authentication is in auth.py"
            mock_state.sources = [mock_source]
            mock_state.error = None
            mock_agent.return_value.ainvoke = AsyncMock(return_value=mock_state)

            with patch("app.api.v1.chat.session_store") as mock_store:
                mock_session = MagicMock()
                mock_session.session_id = mock_codebase_id
                mock_store.create_session = AsyncMock(return_value=mock_session)
                mock_store.add_message = AsyncMock()

                response = test_client.post(
                    "/api/v1/chat",
                    json={
                        "codebase_id": mock_codebase_id,
                        "query": "Where is authentication?",
                    },
                )

                assert response.status_code == 200
                # Verify sources were saved
                mock_store.add_message.assert_any_call(
                    session_id=mock_session.session_id,
                    role="assistant",
                    content="Authentication is in auth.py",
                    citations=[mock_source],
                )


class TestChatSessionErrorHandling:
    """Tests for error handling in chat sessions."""

    @pytest.mark.asyncio
    async def test_chat_handles_agent_error_gracefully(
        self,
        test_client: TestClient,
        mock_codebase_id: str,
    ) -> None:
        """Test that agent errors are handled gracefully."""
        with patch("app.api.v1.chat.get_query_agent") as mock_agent:
            mock_state = MagicMock()
            mock_state.error = "Failed to retrieve context"
            mock_agent.return_value.ainvoke = AsyncMock(return_value=mock_state)

            with patch("app.api.v1.chat.session_store") as mock_store:
                mock_session = MagicMock()
                mock_session.session_id = mock_codebase_id
                mock_store.create_session = AsyncMock(return_value=mock_session)

                response = test_client.post(
                    "/api/v1/chat",
                    json={
                        "codebase_id": mock_codebase_id,
                        "query": "Test query",
                    },
                )

                # Should still return 200 but with error event in stream
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_handles_session_store_errors(
        self,
        test_client: TestClient,
        mock_codebase_id: str,
    ) -> None:
        """Test that session store errors are handled."""
        with patch("app.api.v1.chat.get_query_agent") as mock_agent:
            mock_state = MagicMock()
            mock_state.response = "Response"
            mock_state.sources = []
            mock_state.error = None
            mock_agent.return_value.ainvoke = AsyncMock(return_value=mock_state)

            with patch("app.api.v1.chat.session_store") as mock_store:
                mock_store.create_session = AsyncMock(side_effect=Exception("Database error"))

                response = test_client.post(
                    "/api/v1/chat",
                    json={
                        "codebase_id": mock_codebase_id,
                        "query": "Test query",
                    },
                )

                # Should return error status
                assert response.status_code in [500, 503]
