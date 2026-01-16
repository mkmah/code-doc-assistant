"""LLM service for interacting with Anthropic Claude."""

from collections.abc import AsyncIterator
from typing import Any

from anthropic import AsyncAnthropic

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import Source

settings = get_settings()
logger = get_logger(__name__)


class LLMService:
    """Service for generating responses using Claude."""

    def __init__(self) -> None:
        """Initialize the LLM service."""
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def generate_response(
        self,
        query: str,
        context: str,
        session_history: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        """Generate a streaming response to a query.

        Args:
            query: User's question
            context: Retrieved code context
            session_history: Previous messages in the conversation

        Yields:
            Response chunks as they are generated
        """
        # Build system prompt
        system_prompt = """You are an expert code documentation assistant. Your role is to help developers understand codebases by analyzing the provided code.

CONTEXT:
{context}

INSTRUCTIONS:
1. Answer based ONLY on the provided code
2. Cite specific files and line numbers
3. Explain technical concepts clearly
4. If uncertain, say "I don't see this in the provided code"
5. For "how does X work" questions, trace through the code execution
6. Format code references as: `file_path:line_start-line_end`
"""

        # Build messages
        messages = []

        # Add session history
        if session_history:
            for msg in session_history[-5:]:  # Last 5 messages for context
                if msg["role"] in ["user", "assistant"]:
                    messages.append(
                        {
                            "role": msg["role"],
                            "content": msg["content"],
                        }
                    )

        # Add current query
        messages.append({"role": "user", "content": query})

        # Call Claude API with streaming
        logger.info(
            "llm_request",
            query=query[:100],
            context_length=len(context),
            history_count=len(messages),
        )

        async with self._client.messages.stream(
            model="glm-4.6",
            max_tokens=4096,
            system=system_prompt.format(context=context[:50000]),  # Limit context size
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

        logger.info("llm_response_complete")

    async def generate_response_sync(
        self,
        query: str,
        context: str,
        session_history: list[dict[str, Any]] | None = None,
    ) -> tuple[str, list[Source]]:
        """Generate a non-streaming response (for debugging/testing).

        Args:
            query: User's question
            context: Retrieved code context
            session_history: Previous messages

        Returns:
            Tuple of (response_text, citations)
        """
        response_parts = []
        async for chunk in self.generate_response(query, context, session_history):
            response_parts.append(chunk)

        response = "".join(response_parts)

        # Extract citations from response
        citations = self._extract_citations(response)

        return response, citations

    def _extract_citations(self, response: str) -> list[Source]:
        """Extract code citations from response text.

        Looks for patterns like `path/to/file:line_start-line_end`

        Args:
            response: Response text

        Returns:
            List of extracted sources
        """
        import re

        citation_pattern = r"`([^:`]+):(\d+)-(\d+)`"
        matches = re.findall(citation_pattern, response)

        sources = []
        for match in matches:
            try:
                sources.append(
                    Source(
                        file_path=match[0],
                        line_start=int(match[1]),
                        line_end=int(match[2]),
                    )
                )
            except (ValueError, IndexError):
                continue

        return sources

    async def close(self) -> None:
        """Close the LLM client."""
        await self._client.close()


# Singleton instance
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """Get the singleton LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
