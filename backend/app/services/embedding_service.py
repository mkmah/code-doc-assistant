"""Embedding service using Jina AI with OpenAI fallback."""

from datetime import timedelta
from typing import Any

import httpx
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class EmbeddingService:
    """Generates embeddings using Jina AI with OpenAI fallback."""

    def __init__(self) -> None:
        """Initialize the embedding service."""
        self._jina_client = httpx.AsyncClient(
            base_url="https://api.jina.ai/v1",
            headers={"Authorization": f"Bearer {settings.jina_api_key}"},
            timeout=timedelta(seconds=30),
        )
        self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def generate_embeddings(
        self,
        texts: list[str],
    ) -> list[list[float]] | None:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors, or None if both services fail

        Raises:
            ValueError: If texts list is empty
        """
        if not texts:
            raise ValueError("Cannot embed empty text list")

        # Try Jina AI first
        try:
            logger.info("generating_embeddings_jina", count=len(texts))
            embeddings = await self._generate_jina_embeddings(texts)
            logger.info("embeddings_generated_jina", count=len(embeddings))
            return embeddings
        except Exception as e:
            logger.warning("jina_embeddings_failed", error=str(e))

            # Fallback to OpenAI
            if self._openai_client:
                try:
                    logger.info("generating_embeddings_openai_fallback", count=len(texts))
                    embeddings = await self._generate_openai_embeddings(texts)
                    logger.info("embeddings_generated_openai", count=len(embeddings))
                    return embeddings
                except Exception as e2:
                    logger.error("openai_embeddings_failed", error=str(e2))

            return None

    async def _generate_jina_embeddings(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Generate embeddings using Jina AI.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        # Batch requests
        batch_size = settings.embedding_batch_size
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            response = await self._jina_client.post(
                "/embeddings",
                json={
                    "model": "jina-embeddings-v4",
                    "input": batch,
                    "encoding_format": "float",
                },
            )
            response.raise_for_status()
            data = response.json()

            batch_embeddings = [item["embedding"] for item in data["data"]]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def _generate_openai_embeddings(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Generate embeddings using OpenAI (fallback).

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors

        Raises:
            Exception: If API request fails
        """
        # Batch requests
        batch_size = settings.embedding_batch_size
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            response = await self._openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=batch,
            )

            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def generate_query_embedding(self, query: str) -> list[float] | None:
        """Generate embedding for a single query.

        Args:
            query: Query string

        Returns:
            Embedding vector or None if failed
        """
        embeddings = await self.generate_embeddings([query])
        return embeddings[0] if embeddings else None

    async def close(self) -> None:
        """Close the HTTP clients."""
        await self._jina_client.aclose()
        if self._openai_client:
            await self._openai_client.close()


# Singleton instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get the singleton embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
