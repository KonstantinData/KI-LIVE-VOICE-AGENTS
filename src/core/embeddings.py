"""
OpenAI Embedding Client
=======================
What:    Wrapper around OpenAI's text embedding API.
Does:    Creates vector embeddings for text using text-embedding-3-small (1536 dimensions).
Why:     Required for semantic search in the knowledge base; separates embedding logic from knowledge search.
Who:     KnowledgeBase (for query and chunk embeddings).
Depends: openai, structlog, src.api.config
"""

import structlog
from openai import AsyncOpenAI

from src.api.config import get_settings

log = structlog.get_logger()
settings = get_settings()


class EmbeddingClient:
    """
    Wrapper um die OpenAI Embeddings API.

    Nutzt text-embedding-3-small (1536 Dimensionen, günstig, bewährt).
    """

    def __init__(self) -> None:
        self._client = (
            AsyncOpenAI(api_key=settings.openai_api_key)
            if settings.openai_api_key
            else None
        )
        self._model = settings.openai_embedding_model

    async def embed(self, text: str) -> list[float]:
        """
        Creates an embedding vector for the given text.
        
        Args:
            text: Text to embed (max ~8000 tokens for text-embedding-3-small)
            
        Returns:
            1536-dimensional embedding vector
        """
        if self._client is None:
            raise RuntimeError("OPENAI_API_KEY is required for embeddings")
        response = await self._client.embeddings.create(
            model=self._model,
            input=text,
        )
        log.debug("embedding.created", model=self._model, text_len=len(text))
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Creates embedding vectors for multiple texts at once.
        
        More efficient than calling embed() multiple times.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of 1536-dimensional embedding vectors
        """
        if self._client is None:
            raise RuntimeError("OPENAI_API_KEY is required for embeddings")
        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [item.embedding for item in response.data]
