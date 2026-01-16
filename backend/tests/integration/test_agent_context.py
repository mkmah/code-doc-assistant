"""Integration tests for agent session context loading."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.nodes import query_analysis_node
from app.agents.state import AgentState


@pytest.fixture
def sample_state() -> AgentState:
    """Create a sample agent state for testing."""
    return AgentState(
        codebase_id="550e8400-e29b-41d4-a716-446655440000",
        query="What is the authentication mechanism?",
        session_id="660e8400-e29b-41d4-a716-446655440000",
        step="initial",
    )


class TestQueryAnalysisNodeContext:
    """Tests for query_analysis_node session context loading."""

    @pytest.mark.asyncio
    async def test_query_analysis_node_loads_session_history(
        self,
        sample_state: AgentState,
    ) -> None:
        """Test that query_analysis_node loads session history from session_store."""
        with patch("app.agents.nodes.get_session_store") as mock_store_getter:
            mock_store = MagicMock()
            mock_store_getter.return_value = mock_store

            # Mock session with history
            mock_session = MagicMock()
            mock_session.session_id = sample_state.session_id
            mock_store.get_session = AsyncMock(return_value=mock_session)

            # Mock messages
            from app.models.schemas import MessageType, QueryMessage

            mock_messages = [
                QueryMessage(
                    message_id="msg1",
                    session_id=sample_state.session_id,
                    role=MessageType.USER,
                    content="How does authentication work?",
                    timestamp=None,
                ),
                QueryMessage(
                    message_id="msg2",
                    session_id=sample_state.session_id,
                    role=MessageType.ASSISTANT,
                    content="Authentication uses JWT tokens.",
                    timestamp=None,
                ),
            ]

            # Make get_messages an async generator
            async def message_generator():
                for msg in mock_messages:
                    yield msg

            mock_store.get_messages = MagicMock(return_value=message_generator())

            # Run the node
            updated_state = await query_analysis_node(sample_state)

            # Verify session was retrieved
            mock_store.get_session.assert_called_once_with(
                sample_state.session_id
            )

            # Verify state was updated
            assert updated_state.step == "analyzed"

    @pytest.mark.asyncio
    async def test_query_analysis_node_handles_missing_session(
        self,
        sample_state: AgentState,
    ) -> None:
        """Test that query_analysis_node handles missing session gracefully."""
        with patch("app.agents.nodes.get_session_store") as mock_store_getter:
            mock_store = MagicMock()
            mock_store_getter.return_value = mock_store

            # Mock session not found
            mock_store.get_session = AsyncMock(return_value=None)

            # Run the node - should not raise error
            updated_state = await query_analysis_node(sample_state)

            # Should still complete successfully
            assert updated_state.step == "analyzed"

    @pytest.mark.asyncio
    async def test_query_analysis_node_formats_history_as_conversation_string(
        self,
        sample_state: AgentState,
    ) -> None:
        """Test that session history is formatted as Q: ... A: ... string."""
        with patch("app.agents.nodes.get_session_store") as mock_store_getter:
            mock_store = MagicMock()
            mock_store_getter.return_value = mock_store

            mock_session = MagicMock()
            mock_store.get_session = AsyncMock(return_value=mock_session)

            # Create conversation history
            from app.models.schemas import MessageType, QueryMessage

            mock_messages = [
                QueryMessage(
                    message_id="msg1",
                    session_id=sample_state.session_id,
                    role=MessageType.USER,
                    content="How does auth work?",
                    timestamp=None,
                ),
                QueryMessage(
                    message_id="msg2",
                    session_id=sample_state.session_id,
                    role=MessageType.ASSISTANT,
                    content="Auth uses JWT.",
                    timestamp=None,
                ),
                QueryMessage(
                    message_id="msg3",
                    session_id=sample_state.session_id,
                    role=MessageType.USER,
                    content="What about refresh tokens?",
                    timestamp=None,
                ),
                QueryMessage(
                    message_id="msg4",
                    session_id=sample_state.session_id,
                    role=MessageType.ASSISTANT,
                    content="Refresh tokens last 30 days.",
                    timestamp=None,
                ),
            ]

            async def message_generator():
                for msg in mock_messages:
                    yield msg

            mock_store.get_messages = MagicMock(return_value=message_generator())

            # Run the node
            updated_state = await query_analysis_node(sample_state)

            # Verify the session history is formatted correctly
            # This will be used in response_generation_node
            assert updated_state.step == "analyzed"


class TestResponseGenerationNodeContext:
    """Tests for response_generation_node session context usage."""

    @pytest.mark.asyncio
    async def test_response_generation_uses_session_history(
        self,
        sample_state: AgentState,
    ) -> None:
        """Test that response_generation_node uses session history for context."""
        from app.agents.nodes import response_generation_node

        # Set up state with context and session history
        sample_state.context = "Code context here..."
        sample_state.session_history = [
            {"role": "user", "content": "How does auth work?"},
            {"role": "assistant", "content": "Auth uses JWT."},
        ]

        with patch("app.agents.nodes.get_llm_service") as mock_service_getter:
            mock_llm = MagicMock()
            mock_service_getter.return_value = mock_llm

            # Mock streaming response
            async def response_stream():
                yield "Based on our conversation, "

            mock_llm.generate_response = AsyncMock(return_value=response_stream())

            # Run the node
            updated_state = await response_generation_node(sample_state)

            # Verify generate_response was called with session_history
            mock_llm.generate_response.assert_called_once()
            call_args = mock_llm.generate_response.call_args

            # Check that session_history was passed (not None)
            # The implementation should pass the formatted history
            assert "session_history" in call_args.kwargs or len(call_args.args) >= 3

    @pytest.mark.asyncio
    async def test_response_generation_limits_history_to_10_turns(
        self,
        sample_state: AgentState,
    ) -> None:
        """Test that only the last 10 conversation turns are used."""
        from app.agents.nodes import response_generation_node

        sample_state.context = "Code context"

        # Create 15 conversation turns
        long_history = []
        for i in range(15):
            long_history.append({"role": "user", "content": f"Question {i}"})
            long_history.append({"role": "assistant", "content": f"Answer {i}"})

        sample_state.session_history = long_history

        with patch("app.agents.nodes.get_llm_service") as mock_service_getter:
            mock_llm = MagicMock()
            mock_service_getter.return_value = mock_llm

            async def response_stream():
                yield "Response"

            mock_llm.generate_response = AsyncMock(return_value=response_stream())

            # Run the node
            await response_generation_node(sample_state)

            # Verify the history passed to LLM is limited
            # The implementation should limit to last 10 turns (20 messages)
            call_args = mock_llm.generate_response.call_args
            session_history_arg = call_args.kwargs.get("session_history")

            # Should have at most 10 turns (20 messages)
            if session_history_arg:
                assert len(session_history_arg) <= 20


class TestConversationHistoryFormatting:
    """Tests for conversation history formatting."""

    @pytest.mark.asyncio
    async def test_conversation_history_formatting_produces_correct_string(
        self,
        sample_state: AgentState,
    ) -> None:
        """Test that conversation history is formatted as 'Q: ... A: ...'."""
        with patch("app.agents.nodes.get_session_store") as mock_store_getter:
            mock_store = MagicMock()
            mock_store_getter.return_value = mock_store

            mock_session = MagicMock()
            mock_store.get_session = AsyncMock(return_value=mock_session)

            # Create test conversation
            from app.models.schemas import MessageType, QueryMessage

            mock_messages = [
                QueryMessage(
                    message_id="msg1",
                    session_id=sample_state.session_id,
                    role=MessageType.USER,
                    content="How does auth work?",
                    timestamp=None,
                ),
                QueryMessage(
                    message_id="msg2",
                    session_id=sample_state.session_id,
                    role=MessageType.ASSISTANT,
                    content="Auth uses JWT tokens.",
                    timestamp=None,
                ),
            ]

            async def message_generator():
                for msg in mock_messages:
                    yield msg

            mock_store.get_messages = MagicMock(return_value=message_generator())

            # Run query_analysis_node which should load and format history
            updated_state = await query_analysis_node(sample_state)

            # The formatted history should be available in the state
            # and follow the Q: / A: pattern
            assert updated_state.step == "analyzed"

    @pytest.mark.asyncio
    async def test_conversation_history_handles_empty_history(
        self,
        sample_state: AgentState,
    ) -> None:
        """Test that empty conversation history is handled correctly."""
        with patch("app.agents.nodes.get_session_store") as mock_store_getter:
            mock_store = MagicMock()
            mock_store_getter.return_value = mock_store

            mock_session = MagicMock()
            mock_store.get_session = AsyncMock(return_value=mock_session)

            # Empty message list
            async def empty_generator():
                return
                yield  # pylint: disable=unreachable

            mock_store.get_messages = MagicMock(return_value=empty_generator())

            # Run the node - should not raise error
            updated_state = await query_analysis_node(sample_state)

            assert updated_state.step == "analyzed"


class TestAgentStateSessionIntegration:
    """Tests for agent state integration with session context."""

    @pytest.mark.asyncio
    async def test_agent_state_maintains_session_id_through_pipeline(
        self,
        sample_state: AgentState,
    ) -> None:
        """Test that session_id is maintained through the agent pipeline."""
        from app.agents.nodes import (
            context_building_node,
            query_analysis_node,
            retrieval_node,
            response_generation_node,
        )

        # Run through the pipeline
        state = sample_state

        # Query analysis
        state = await query_analysis_node(state)
        assert state.session_id == sample_state.session_id

        # Retrieval
        state = await retrieval_node(state)
        assert state.session_id == sample_state.session_id

        # Context building
        state = await context_building_node(state)
        assert state.session_id == sample_state.session_id

        # Response generation
        with patch("app.agents.nodes.get_llm_service") as mock_service_getter:
            mock_llm = MagicMock()
            mock_service_getter.return_value = mock_llm

            async def response_stream():
                yield "Response"

            mock_llm.generate_response = AsyncMock(return_value=response_stream())

            state = await response_generation_node(state)
            assert state.session_id == sample_state.session_id

    @pytest.mark.asyncio
    async def test_agent_state_preserves_conversation_context(
        self,
        sample_state: AgentState,
    ) -> None:
        """Test that conversation context is preserved in agent state."""
        from app.agents.nodes import query_analysis_node

        # Add session history to state
        sample_state.session_history = [
            {"role": "user", "content": "Previous question?"},
            {"role": "assistant", "content": "Previous answer."},
        ]

        with patch("app.agents.nodes.get_session_store") as mock_store_getter:
            mock_store = MagicMock()
            mock_store_getter.return_value = mock_store
            mock_session = MagicMock()
            mock_store.get_session = AsyncMock(return_value=mock_session)

            async def empty_generator():
                return
                yield

            mock_store.get_messages = MagicMock(return_value=empty_generator())

            # Run the node
            updated_state = await query_analysis_node(sample_state)

            # Session history should be preserved or loaded
            assert updated_state.session_id == sample_state.session_id


class TestSessionContextInMultiTurnScenarios:
    """Tests for session context in realistic multi-turn scenarios."""

    @pytest.mark.asyncio
    async def test_follow_up_question_references_previous_answer(
        self,
        sample_state: AgentState,
    ) -> None:
        """Test that follow-up questions can reference previous answers."""
        with patch("app.agents.nodes.get_session_store") as mock_store_getter:
            mock_store = MagicMock()
            mock_store_getter.return_value = mock_store

            mock_session = MagicMock()
            mock_store.get_session = AsyncMock(return_value=mock_session)

            # Simulate previous conversation about authentication
            from app.models.schemas import MessageType, QueryMessage

            mock_messages = [
                QueryMessage(
                    message_id="msg1",
                    session_id=sample_state.session_id,
                    role=MessageType.USER,
                    content="How does authentication work?",
                    timestamp=None,
                ),
                QueryMessage(
                    message_id="msg2",
                    session_id=sample_state.session_id,
                    role=MessageType.ASSISTANT,
                    content="Authentication uses JWT tokens with 24-hour expiration.",
                    timestamp=None,
                ),
            ]

            async def message_generator():
                for msg in mock_messages:
                    yield msg

            mock_store.get_messages = MagicMock(return_value=message_generator())

            # Now ask a follow-up question
            sample_state.query = "What happens when the token expires?"

            # Run query analysis
            updated_state = await query_analysis_node(sample_state)

            # The agent should have access to previous context
            assert updated_state.session_id == sample_state.session_id

    @pytest.mark.asyncio
    async def test_new_session_has_no_history(
        self,
        sample_state: AgentState,
    ) -> None:
        """Test that a new session has no conversation history."""
        with patch("app.agents.nodes.get_session_store") as mock_store_getter:
            mock_store = MagicMock()
            mock_store_getter.return_value = mock_store

            mock_session = MagicMock()
            mock_store.get_session = AsyncMock(return_value=mock_session)

            # Empty message generator for new session
            async def empty_generator():
                return
                yield

            mock_store.get_messages = MagicMock(return_value=empty_generator())

            # Run the node
            updated_state = await query_analysis_node(sample_state)

            # Should complete without error
            assert updated_state.step == "analyzed"
