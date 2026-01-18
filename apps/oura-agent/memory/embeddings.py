"""Embedding service using Ollama's nomic-embed-text model.

Provides vector embeddings for semantic search in episodic memory.
Uses the cluster Ollama service for generation.
"""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Singleton instance
_embedding_service: Optional["EmbeddingService"] = None


class EmbeddingService:
    """Generate embeddings using Ollama's nomic-embed-text model."""

    DEFAULT_MODEL = "nomic-embed-text"
    DEFAULT_DIM = 768

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = DEFAULT_MODEL,
        embedding_dim: int = DEFAULT_DIM,
    ):
        """Initialize embedding service.

        Args:
            base_url: Base URL for Ollama API
            model: Embedding model name
            embedding_dim: Expected embedding dimension
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.embedding_dim = embedding_dim
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            httpx.HTTPError: If the API request fails
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding, returning zero vector")
            return [0.0] * self.embedding_dim

        try:
            response = await self.client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
            )
            response.raise_for_status()
            data = response.json()
            embedding = data.get("embedding", [])

            if len(embedding) != self.embedding_dim:
                logger.warning(
                    f"Unexpected embedding dimension: {len(embedding)}, "
                    f"expected {self.embedding_dim}"
                )

            return embedding

        except httpx.HTTPError as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in parallel.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        import asyncio

        if not texts:
            return []

        # Run embeddings in parallel for better performance
        return await asyncio.gather(*[self.embed(text) for text in texts])

    def embed_sync(self, text: str) -> list[float]:
        """Synchronous version of embed.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding, returning zero vector")
            return [0.0] * self.embedding_dim

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                )
                response.raise_for_status()
                data = response.json()
                return data.get("embedding", [])

        except httpx.HTTPError as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def test_connection(self) -> bool:
        """Test connection to Ollama service.

        Returns:
            True if connection successful
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()

            # Check if our model is available
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]

            if self.model not in models and f"{self.model}:latest" not in models:
                logger.warning(
                    f"Model {self.model} not found in Ollama. "
                    f"Available models: {models}"
                )
                return False

            logger.info(f"Ollama connection successful, model {self.model} available")
            return True

        except Exception as e:
            logger.error(f"Ollama connection test failed: {e}")
            return False

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


def get_embedding_service(
    base_url: str = "http://localhost:11434",
    model: str = EmbeddingService.DEFAULT_MODEL,
    embedding_dim: int = EmbeddingService.DEFAULT_DIM,
) -> EmbeddingService:
    """Get singleton embedding service instance.

    Args:
        base_url: Ollama base URL
        model: Embedding model name
        embedding_dim: Expected embedding dimension

    Returns:
        EmbeddingService instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(
            base_url=base_url,
            model=model,
            embedding_dim=embedding_dim,
        )
    return _embedding_service
