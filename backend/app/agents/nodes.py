"""LangGraph agent nodes for query processing."""

from typing import Any

from app.agents.state import AgentState
from app.core.logging import get_logger
from app.services.llm_service import get_llm_service
from app.services.retrieval_service import get_retrieval_service

logger = get_logger(__name__)


async def query_analysis_node(state: AgentState) -> AgentState:
    """Analyze the user's query to understand intent.

    Args:
        state: Current agent state

    Returns:
        Updated state
    """
    logger.info(
        "query_analysis",
        query=state.query[:100],
        codebase_id=state.codebase_id,
    )

    # For MVP, we skip complex intent analysis
    # In a full implementation, this would classify:
    # - Code understanding questions
    # - Bug finding requests
    # - Architecture questions
    # - Specific component queries

    state.step = "analyzed"
    return state


async def retrieval_node(state: AgentState) -> AgentState:
    """Retrieve relevant code chunks using vector search.

    Args:
        state: Current agent state

    Returns:
        Updated state with retrieved chunks
    """
    retrieval_service = get_retrieval_service()

    chunks, sources = await retrieval_service.retrieve_code(
        query=state.query,
        codebase_id=state.codebase_id,
        top_k=5,
    )

    state.retrieved_chunks = chunks
    state.sources = sources
    state.step = "retrieved"

    logger.info(
        "retrieval_complete",
        chunks_count=len(chunks),
        sources_count=len(sources),
    )

    return state


async def context_building_node(state: AgentState) -> AgentState:
    """Build formatted context from retrieved chunks.

    Args:
        state: Current agent state

    Returns:
        Updated state with formatted context
    """
    context_parts = []

    for chunk in state.retrieved_chunks:
        metadata = chunk["metadata"]
        context_parts.append(
            f"File: {metadata['file_path']} (Lines {metadata['line_start']}-{metadata['line_end']})\n"
            f"```{metadata['language']}\n"
            f"{chunk['content']}\n"
            f"```"
        )

    state.context = "\n\n".join(context_parts)
    state.step = "context_built"

    logger.info(
        "context_built",
        context_length=len(state.context),
    )

    return state


async def response_generation_node(state: AgentState) -> AgentState:
    """Generate response using Claude LLM.

    Args:
        state: Current agent state

    Returns:
        Updated state with generated response
    """
    llm_service = get_llm_service()

    response_parts = []
    async for chunk in llm_service.generate_response(
        query=state.query,
        context=state.context,
        session_history=None,  # TODO: Load from session store
    ):
        response_parts.append(chunk)

    state.response = "".join(response_parts)
    state.step = "responded"

    logger.info(
        "response_generated",
        response_length=len(state.response),
    )

    return state


async def validation_node(state: AgentState) -> AgentState:
    """Validate the generated response and extract citations.

    Args:
        state: Current agent state

    Returns:
        Updated state with validated sources
    """
    # Extract citations from response (already done in retrieval)
    # For MVP, we keep the sources from retrieval
    # In a full implementation, this would:
    # - Verify citations actually exist in the codebase
    # - Check response accuracy
    # - Detect hallucinations

    state.step = "validated"

    logger.info("response_validated")

    return state


async def error_handler_node(state: AgentState, error: Exception) -> AgentState:
    """Handle errors in the agent pipeline.

    Args:
        state: Current agent state
        error: The error that occurred

    Returns:
        Updated state with error information
    """
    logger.error(
        "agent_error",
        step=state.step,
        error=str(error),
    )

    state.error = f"An error occurred while processing your query: {str(error)}"
    state.step = "error"

    return state
