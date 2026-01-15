"""Chat endpoint for querying codebases."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.agents.graph import get_query_agent
from app.agents.state import AgentState
from app.core.logging import get_logger
from app.models.schemas import ChatRequest, Source
from app.services.session_store import get_session_store

router = APIRouter()
logger = get_logger(__name__)
session_store = get_session_store()


@router.post("/chat")
async def chat(request: ChatRequest):
    """Query a codebase with streaming response.

    Args:
        request: Chat request with query and codebase_id

    Returns:
        Streaming SSE response
    """
    # Ensure session exists
    if request.session_id:
        session = await session_store.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        # Create new session
        session = await session_store.create_session(request.codebase_id)
        request.session_id = session.session_id

    # Initialize agent state
    state = AgentState(
        codebase_id=str(request.codebase_id),
        query=request.query,
        session_id=request.session_id,
    )

    # Run the agent
    agent = get_query_agent()
    final_state = await agent.ainvoke(state)

    # Check for errors
    if final_state.error:
        return StreamingResponse(
            _error_stream(final_state.error),
            media_type="text/event-stream",
        )

    # Stream the response
    async def event_generator():
        """Generate SSE events for the chat response."""
        try:
            # Stream the response content
            for chunk in final_state.response:
                yield f"data: {encode_sse({{'type': 'chunk', 'content': chunk}})}\n\n"

            # Send sources
            if final_state.sources:
                sources_data = [
                    {
                        "file_path": s.file_path,
                        "line_start": s.line_start,
                        "line_end": s.line_end,
                        "snippet": s.snippet,
                    }
                    for s in final_state.sources
                ]
                yield f"data: {encode_sse({{'type': 'sources', 'sources': sources_data}})}\n\n"

            # Save messages to session
            await session_store.add_message(
                session_id=request.session_id,
                role="user",
                content=request.query,
            )

            await session_store.add_message(
                session_id=request.session_id,
                role="assistant",
                content=final_state.response,
                citations=final_state.sources,
            )

            # Send done event
            yield f"data: {encode_sse({{'type': 'done'}})}\n\n"

        except Exception as e:
            logger.error("chat_stream_error", error=str(e))
            yield f"data: {encode_sse({{'type': 'error', 'error': 'An error occurred'}})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


def encode_sse(data: dict) -> str:
    """Encode data for SSE.

    Args:
        data: Data dictionary to encode

    Returns:
        JSON string for SSE
    """
    import json
    from uuid import UUID

    def default_serializer(obj):
        """JSON serializer for objects not serializable by default json code."""
        if isinstance(obj, UUID):
            return str(obj)
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    return json.dumps(data, default=default_serializer).replace("\n", "\\n")


async def _error_stream(error_message: str):
    """Generate an error stream.

    Args:
        error_message: Error message to send

    Yields:
        SSE events
    """
    yield f"data: {encode_sse({'type': 'error', 'error': error_message})}\n\n"
    yield f"data: {encode_sse({'type': 'done'})}\n\n"
