"""LangGraph agent graph definition."""

from typing import Literal

from langgraph.graph import END, StateGraph

from app.agents.nodes import (
    context_building_node,
    error_handler_node,
    query_analysis_node,
    response_generation_node,
    retrieval_node,
    validation_node,
)
from app.agents.state import AgentState


def create_query_agent() -> StateGraph:
    """Create the query processing agent graph.

    Returns:
        Compiled LangGraph agent
    """
    # Create the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("query_analysis", query_analysis_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("context_building", context_building_node)
    workflow.add_node("response_generation", response_generation_node)
    workflow.add_node("validation", validation_node)

    # Define the flow
    workflow.set_entry_point("query_analysis")
    workflow.add_edge("query_analysis", "retrieval")
    workflow.add_edge("retrieval", "context_building")
    workflow.add_edge("context_building", "response_generation")
    workflow.add_edge("response_generation", "validation")
    workflow.add_edge("validation", END)

    # Compile the graph
    app = workflow.compile()

    return app


# Singleton instance
_query_agent: StateGraph | None = None


def get_query_agent() -> StateGraph:
    """Get the singleton query agent instance."""
    global _query_agent
    if _query_agent is None:
        _query_agent = create_query_agent()
    return _query_agent
