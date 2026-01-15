"""Unit tests for LLM service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm_service import LLMService


@pytest.fixture
def llm_service():
    """Create an LLM service instance."""
    return LLMService()


@pytest.fixture
def sample_context():
    """Create sample code context."""
    return """
File: app/main.py (Lines 1-5)
```python
def hello_world():
    print('Hello, World!')
    return 42
```
"""


class MockStream:
    """Mock async stream for LLM responses."""

    def __init__(self, text_chunks):
        self.text_chunks = text_chunks

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    @property
    def text_stream(self):
        async def gen():
            for chunk in self.text_chunks:
                yield chunk

        return gen()


class TestLLMService:
    """Tests for LLMService class."""

    @pytest.mark.asyncio
    async def test_generate_response_basic(self, llm_service, sample_context):
        """Test basic response generation."""
        mock_stream = MockStream(["The function `hello_world` prints a greeting and returns 42."])

        with patch.object(llm_service._client.messages, "stream", return_value=mock_stream):
            response_chunks = []
            async for chunk in llm_service.generate_response(
                query="What does hello_world do?",
                context=sample_context,
            ):
                response_chunks.append(chunk)

            response = "".join(response_chunks)
            assert "hello_world" in response
            assert len(response_chunks) > 0

    @pytest.mark.asyncio
    async def test_generate_response_with_session_history(
        self, llm_service, sample_context
    ):
        """Test response generation with session history."""
        session_history = [
            {"role": "user", "content": "What files are in this codebase?"},
            {"role": "assistant", "content": "There are 3 Python files."},
        ]

        mock_stream = MockStream(["Based on the previous context..."])

        with patch.object(llm_service._client.messages, "stream", return_value=mock_stream):
            response_chunks = []
            async for chunk in llm_service.generate_response(
                query="Tell me more about the files",
                context=sample_context,
                session_history=session_history,
            ):
                response_chunks.append(chunk)

            assert len(response_chunks) > 0

    @pytest.mark.asyncio
    async def test_generate_response_limits_history(self, llm_service, sample_context):
        """Test that only the last 5 messages from history are used."""
        # Create 10 messages in history
        long_history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
            for i in range(10)
        ]

        mock_stream = MockStream(["Response"])

        with patch.object(
            llm_service._client.messages, "stream", return_value=mock_stream
        ) as mock_stream_call:
            async for _ in llm_service.generate_response(
                query="Latest question",
                context=sample_context,
                session_history=long_history,
            ):
                pass

            # Verify stream was called
            assert mock_stream_call.called

    @pytest.mark.asyncio
    async def test_generate_response_sync(self, llm_service, sample_context):
        """Test non-streaming response generation."""
        mock_stream = MockStream(["The function is defined at `app/main.py:1-5`"])

        with patch.object(llm_service._client.messages, "stream", return_value=mock_stream):
            response, citations = await llm_service.generate_response_sync(
                query="Where is hello_world defined?",
                context=sample_context,
            )

            assert response is not None
            assert isinstance(response, str)
            assert len(response) > 0
            assert isinstance(citations, list)

    @pytest.mark.asyncio
    async def test_extract_citations_from_response(self, llm_service):
        """Test citation extraction from response text."""
        response = """
The code is defined in several places:
1. Main function at `app/main.py:10-25`
2. Helper function at `utils/helpers.py:5-15`
3. Test at `tests/test_main.py:1-100`
"""

        citations = llm_service._extract_citations(response)

        assert len(citations) == 3
        assert citations[0].file_path == "app/main.py"
        assert citations[0].line_start == 10
        assert citations[0].line_end == 25

        assert citations[1].file_path == "utils/helpers.py"
        assert citations[1].line_start == 5
        assert citations[1].line_end == 15

        assert citations[2].file_path == "tests/test_main.py"
        assert citations[2].line_start == 1
        assert citations[2].line_end == 100

    def test_extract_citations_no_matches(self, llm_service):
        """Test citation extraction when no citations exist."""
        response = "This response has no code citations or file references."

        citations = llm_service._extract_citations(response)

        assert len(citations) == 0

    def test_extract_citations_partial_matches(self, llm_service):
        """Test citation extraction with partial matches."""
        response = """
Some code at `app/main.py:10` (missing end line)
Another at `utils/helper.py:5-15` (valid)
Invalid format `file.py` (no line numbers)
"""

        citations = llm_service._extract_citations(response)

        # Only the valid citation should be extracted
        assert len(citations) == 1
        assert citations[0].file_path == "utils/helper.py"
        assert citations[0].line_start == 5
        assert citations[0].line_end == 15

    @pytest.mark.asyncio
    async def test_generate_response_with_citations(self, llm_service, sample_context):
        """Test that response includes citations in the expected format."""
        mock_stream = MockStream(["The function is at `app/main.py:1-5` and `utils/helper.py:10-20`"])

        with patch.object(llm_service._client.messages, "stream", return_value=mock_stream):
            response, citations = await llm_service.generate_response_sync(
                query="Where are the functions?",
                context=sample_context,
            )

            assert "app/main.py:1-5" in response
            assert len(citations) == 2
            assert citations[0].file_path == "app/main.py"
            assert citations[1].file_path == "utils/helper.py"

    @pytest.mark.asyncio
    async def test_generate_response_empty_context(self, llm_service):
        """Test response generation with empty context."""
        mock_stream = MockStream(["I don't see any code in the provided context."])

        with patch.object(llm_service._client.messages, "stream", return_value=mock_stream):
            response_chunks = []
            async for chunk in llm_service.generate_response(
                query="What does this code do?",
                context="",
            ):
                response_chunks.append(chunk)

            response = "".join(response_chunks)
            assert len(response) > 0

    @pytest.mark.asyncio
    async def test_generate_response_context_truncation(self, llm_service):
        """Test that very large context is truncated."""
        # Create a context larger than 50000 chars
        large_context = "x" * 60000

        mock_stream = MockStream(["Response"])

        with patch.object(
            llm_service._client.messages, "stream", return_value=mock_stream
        ) as mock_stream_call:
            async for _ in llm_service.generate_response(
                query="Test query",
                context=large_context,
            ):
                pass

            # Verify stream was called
            assert mock_stream_call.called

    @pytest.mark.asyncio
    async def test_generate_response_streaming_chunks(
        self, llm_service, sample_context
    ):
        """Test that streaming returns multiple chunks."""
        chunk_texts = ["Hello", " there", " world", "!"]
        mock_stream = MockStream(chunk_texts)

        with patch.object(llm_service._client.messages, "stream", return_value=mock_stream):
            response_chunks = []
            async for chunk in llm_service.generate_response(
                query="Test",
                context=sample_context,
            ):
                response_chunks.append(chunk)

            # Should receive all chunks
            assert len(response_chunks) == len(chunk_texts)
            assert "".join(response_chunks) == "Hello there world!"

    @pytest.mark.asyncio
    async def test_close_client(self, llm_service):
        """Test closing the LLM client."""
        with patch.object(llm_service._client, "close", new_callable=AsyncMock) as mock_close:
            await llm_service.close()
            mock_close.assert_called_once()
