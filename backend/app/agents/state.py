"""LangGraph agent state definition."""

from typing import Any

from pydantic import BaseModel, Field

from app.models.schemas import Source


class AgentState(BaseModel):
    """State for the query processing agent."""

    # Input
    codebase_id: str = Field(..., description="Codebase ID")
    query: str = Field(..., description="User query")
    session_id: str | None = Field(default=None, description="Session ID")

    # Query analysis metadata
    query_analysis: dict[str, Any] = Field(
        default_factory=dict,
        description="Query intent classification and extracted entities",
    )

    # Intermediate
    retrieved_chunks: list[dict[str, Any]] = Field(default_factory=list)
    context: str = Field(..., description="Formatted context")
    sources: list[Source] = Field(default_factory=list)
    session_history: list[dict[str, str]] = Field(
        default_factory=list,
        description="Formatted conversation history (last 10 turns)",
    )

    # Output
    response: str = Field(..., description="Generated response")
    error: str | None = Field(default=None, description="Error message")
    error_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Detailed error information including type, recovery suggestions, and technical details",
    )

    # Validation results
    validation_results: dict[str, Any] = Field(
        default_factory=dict,
        description="Validation metrics including citation verification, hallucination detection, and quality scores",
    )

    # Metadata
    step: str = Field(default="start", description="Current step in the pipeline")
