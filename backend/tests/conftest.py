"""Pytest configuration and shared fixtures."""

import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

# Set test environment before importing app modules
os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["JINA_API_KEY"] = "test-key"
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["TEMPORAL_HOST"] = "localhost"
os.environ["TEMPORAL_PORT"] = "7233"
os.environ["CHROMADB_HOST"] = "localhost"
os.environ["CHROMADB_PORT"] = "8000"
os.environ["LOG_LEVEL"] = "info"
os.environ["ENVIRONMENT"] = "test"


@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def app() -> FastAPI:
    """Create a test FastAPI application."""
    from app.main import app
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB client."""
    mock = MagicMock()
    mock_client = MagicMock()
    mock_client.get_or_create_collection.return_value = mock
    return mock_client


@pytest.fixture
def mock_temporal():
    """Mock Temporal client."""
    mock = MagicMock()
    mock.start_workflow.return_value = MagicMock(id="test-workflow-id")
    return mock


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service."""
    mock = AsyncMock()
    mock.generate_embeddings.return_value = [[0.1, 0.2, 0.3]]
    return mock


@pytest.fixture
def mock_llm_service():
    """Mock LLM service."""
    mock = AsyncMock()
    mock.generate_response.return_value = "Test response"
    return mock


@pytest.fixture
def sample_codebase_id():
    """Sample codebase ID for testing."""
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def sample_session_id():
    """Sample session ID for testing."""
    return "770e8400-e29b-41d4-a716-446655440002"


@pytest.fixture
def sample_zip_file(tmp_path):
    """Create a sample ZIP file for testing."""
    import zipfile
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("test.py", "def hello():\n    return 'world'")
    return zip_path


@pytest.fixture(autouse=True)
async def clear_stores():
    """Clear in-memory stores before each test for isolation."""
    from app.services.codebase_store import get_codebase_store
    from app.services.session_store import get_session_store

    # Clear stores before test
    codebase_store = get_codebase_store()
    codebase_store._codebases.clear()

    session_store = get_session_store()
    session_store._sessions.clear()
    session_store._messages.clear()

    yield

    # Clear stores after test
    codebase_store._codebases.clear()
    session_store._sessions.clear()
    session_store._messages.clear()
