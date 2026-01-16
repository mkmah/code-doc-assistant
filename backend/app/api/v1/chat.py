"""Chat endpoint for querying codebases."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.agents.graph import get_query_agent
from app.agents.state import AgentState
from app.core.logging import get_logger
from app.core.security import limiter
from app.models.schemas import ChatRequest
from app.services.redis_session_store import get_redis_session_store

router = APIRouter()
logger = get_logger(__name__)
redis_store = get_redis_session_store()


@router.post("/chat")
@limiter.limit("100/hour")
async def chat(request: Request, chat_request: ChatRequest):
    """Query a codebase with streaming response.

    Rate limited to 100 requests per hour per IP address.

    Args:
        request: FastAPI Request object for rate limiting
        chat_request: Chat request with query and codebase_id

    Returns:
        Streaming SSE response
    """
    # Ensure session exists
    if chat_request.session_id:
        session = await redis_store.get_session(chat_request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        # Create new session
        session = await redis_store.create_session(chat_request.codebase_id)
        chat_request.session_id = session.session_id

    # Initialize agent state
    state = AgentState(
        codebase_id=str(chat_request.codebase_id),
        query=chat_request.query,
        session_id=str(chat_request.session_id) if chat_request.session_id else None,
        context="",
        response="",
    )

    # Run the agent
    agent = get_query_agent()
    final_state = await agent.ainvoke(state)

    final_state = AgentState(**final_state)

    # Check for errors
    if final_state.error:
        return StreamingResponse(
            _error_stream(final_state.error, final_state.error_metadata),
            media_type="text/event-stream",
        )

    # Stream the response
    async def event_generator():
        """Generate SSE events for the chat response."""
        try:
            # Send session_id first (for new sessions or follow-up requests)
            session_data = {"type": "session_id", "session_id": str(chat_request.session_id)}
            yield f"data: {encode_sse(session_data)}\n\n"

            # Stream the response content
            for chunk in final_state.response:
                chunk_data = {"type": "chunk", "content": chunk}
                yield f"data: {encode_sse(chunk_data)}\n\n"

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
                sources_msg = {"type": "sources", "sources": sources_data}
                yield f"data: {encode_sse(sources_msg)}\n\n"

            # Send validation results
            if final_state.validation_results:
                validation_msg = {"type": "validation", "validation": final_state.validation_results}
                yield f"data: {encode_sse(validation_msg)}\n\n"

            # Save conversation turn to Redis session
            await redis_store.save_conversation_turn(
                session_id=chat_request.session_id,
                query=chat_request.query,
                response=final_state.response,
                sources=final_state.sources,
            )

            # Send done event
            done_data = {"type": "done"}
            yield f"data: {encode_sse(done_data)}\n\n"

        except Exception as e:
            logger.error("chat_stream_error", error=str(e), exc_info=True)
            error_data = {"type": "error", "error": "An error occurred"}
            yield f"data: {encode_sse(error_data)}\n\n"

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

    def default_serializer(obj):
        """JSON serializer for objects not serializable by default json code."""
        from uuid import UUID
        if isinstance(obj, UUID):
            return str(obj)
        # Handle Pydantic models
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    return json.dumps(data, default=default_serializer)


async def _error_stream(error_message: str, error_metadata: dict | None = None):
    """Generate an error stream.

    Args:
        error_message: Error message to send
        error_metadata: Optional detailed error information

    Yields:
        SSE events
    """
    error_response = {
        "type": "error",
        "error": error_message,
    }

    # Include error metadata if available (for debugging, not sensitive info)
    if error_metadata:
        error_response["error_type"] = error_metadata.get("error_type")
        error_response["recovery_suggestion"] = error_metadata.get("recovery_suggestion")

    yield f"data: {encode_sse(error_response)}\n\n"
    done_data = {"type": "done"}
    yield f"data: {encode_sse(done_data)}\n\n"
