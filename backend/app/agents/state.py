"""LangGraph agent state definition."""

from dataclasses import dataclass, field
from typing import Any

from app.models.schemas import Source


@dataclass
class AgentState:
    """State for the query processing agent."""

    # Input
    codebase_id: str
    query: str
    session_id: str | None = None

    # Intermediate
    retrieved_chunks: list[dict[str, Any]] = field(default_factory=list)
    context: str = ""
    sources: list[Source] = field(default_factory=list)

    # Output
    response: str = ""
    error: str | None = None

    # Metadata
    step: str = "start"  # Current step in the pipeline
