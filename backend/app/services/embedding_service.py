"""Embedding service using Jina AI with OpenAI fallback."""

import asyncio

# from datetime import timedelta
import httpx
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class EmbeddingService:
    """Generates embeddings using Jina AI with OpenAI fallback."""

    def __init__(self) -> None:
        print(f"{settings.jina_api_key=}")
        """Initialize the embedding service."""
        self._jina_client = httpx.AsyncClient(
            base_url="https://api.jina.ai/v1",
            headers={"Authorization": f"Bearer {settings.jina_api_key}"},
            timeout=30.0,
        )
        # self._openai_client = (
        #     AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        # )
        self._openai_client = None

    async def generate_embeddings(
        self,
        texts: list[str],
    ) -> list[list[float]]:
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
        except httpx.HTTPStatusError as e:
            error_msg = f"Jina API Error: {e.response.status_code} - {e.response.text}"
            logger.warning("jina_embeddings_http_failed", error=error_msg)

            # Fallback to OpenAI
            if self._openai_client:
                try:
                    logger.info("generating_embeddings_openai_fallback", count=len(texts))
                    embeddings = await self._generate_openai_embeddings(texts)
                    logger.info("embeddings_generated_openai", count=len(embeddings))
                    return embeddings
                except Exception as e2:
                    logger.error("openai_embeddings_failed", error=repr(e2))
                    raise RuntimeError(
                        f"Embedding generation failed. Jina error: {error_msg}. OpenAI error: {repr(e2)}"
                    ) from e2

            raise RuntimeError(
                f"Embedding generation failed. Jina error: {error_msg}. No fallback configured."
            ) from e

        except Exception as e:
            logger.warning("jina_embeddings_failed", error=repr(e))

            # Fallback to OpenAI
            if self._openai_client:
                try:
                    logger.info("generating_embeddings_openai_fallback", count=len(texts))
                    embeddings = await self._generate_openai_embeddings(texts)
                    logger.info("embeddings_generated_openai", count=len(embeddings))
                    return embeddings
                except Exception as e2:
                    logger.error("openai_embeddings_failed", error=repr(e2))
                    raise RuntimeError(
                        f"Embedding generation failed. Jina error: {repr(e)}. OpenAI error: {repr(e2)}"
                    ) from e2

            raise RuntimeError(
                f"Embedding generation failed. Jina error: {repr(e)}. No fallback configured."
            ) from e

    async def _generate_jina_embeddings(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Generate embeddings using Jina AI with rate limiting.

        Uses batch size of 100 with 100ms delays between batches
        to respect API rate limits.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        # Batch size of 100 with rate limit aware delays (100ms between batches)
        batch_size = 100
        all_embeddings = []
        batch_delay_ms = 100  # 100ms delay between batches for rate limiting

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(texts) + batch_size - 1) // batch_size

            logger.info(
                "jina_embedding_batch_start",
                batch_num=batch_num,
                total_batches=total_batches,
                batch_size=len(batch),
            )

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

            logger.info(
                "jina_embedding_batch_complete",
                batch_num=batch_num,
                embeddings_count=len(batch_embeddings),
            )

            # Rate limit aware delay: 100ms between batches (except for last batch)
            if i + batch_size < len(texts):
                await asyncio.sleep(batch_delay_ms / 1000)  # Convert ms to seconds

        return all_embeddings

    async def _generate_openai_embeddings(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Generate embeddings using OpenAI (fallback) with rate limiting.

        Uses batch size of 100 with 100ms delays between batches
        to respect API rate limits.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors

        Raises:
            Exception: If API request fails
        """
        # Batch size of 100 with rate limit aware delays (100ms between batches)
        batch_size = 100
        all_embeddings = []
        batch_delay_ms = 100  # 100ms delay between batches for rate limiting

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(texts) + batch_size - 1) // batch_size

            logger.info(
                "openai_embedding_batch_start",
                batch_num=batch_num,
                total_batches=total_batches,
                batch_size=len(batch),
            )

            response = await self._openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=batch,
            )

            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

            logger.info(
                "openai_embedding_batch_complete",
                batch_num=batch_num,
                embeddings_count=len(batch_embeddings),
            )

            # Rate limit aware delay: 100ms between batches (except for last batch)
            if i + batch_size < len(texts):
                await asyncio.sleep(batch_delay_ms / 1000)  # Convert ms to seconds

        return all_embeddings

    async def generate_query_embedding(self, query: str) -> list[float]:
        """Generate embedding for a single query.

        Args:
            query: Query string

        Returns:
            Embedding vector or None if failed
        """
        embeddings = await self.generate_embeddings([query])
        return embeddings[0]

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
