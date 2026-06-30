"""
Knowledge Base Search
=====================
What:    Semantic search engine for studio-specific knowledge using pgvector.
Does:    Embeds queries, performs cosine similarity search, adds new knowledge chunks with embeddings.
Why:     Agents need to retrieve relevant product/service information from the studio's knowledge base.
Who:     BaseAgent (via process_message), knowledge management routes.
Depends: sqlalchemy, structlog, src.core.embeddings, src.db.models.knowledge_chunk
"""

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.embeddings import EmbeddingClient
from src.db.models.knowledge_chunk import KnowledgeChunk

log = structlog.get_logger()


class KnowledgeBase:
    """
    Semantische Suche in der Wissensbasis eines Studios.

    Nutzt pgvector für Ähnlichkeitssuche:
    1. Nachricht wird embedded (OpenAI)
    2. Ähnlichste Chunks aus knowledge_chunks werden geladen
    3. Top-K Ergebnisse werden als Kontext zurückgegeben
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._embeddings = EmbeddingClient()

    async def search(
        self,
        query: str,
        studio_id: UUID,
        categories: list[str] | None = None,
        limit: int = 5,
    ) -> list[KnowledgeChunk]:
        """
        Searches for semantically similar chunks for the given query.

        Uses pgvector's cosine distance for similarity ranking.
        
        Args:
            query: Search query (user message or question)
            studio_id: Studio ID for multi-tenant isolation
            categories: Optional list of categories to filter by
            limit: Maximum number of results to return
            
        Returns:
            List of most similar knowledge chunks, ordered by relevance
        """
        try:
            query_embedding = await self._embeddings.embed(query)
        except Exception as exc:
            log.warning(
                "knowledge.search_embedding_failed",
                studio_id=str(studio_id),
                error_type=type(exc).__name__,
            )
            return []

        stmt = (
            select(KnowledgeChunk)
            .where(KnowledgeChunk.studio_id == studio_id)
            .where(KnowledgeChunk.embedding.isnot(None))
        )

        if categories:
            stmt = stmt.where(KnowledgeChunk.category.in_(categories))

        # NOTE: pgvector's <=> operator computes cosine distance (0 = identical, 2 = opposite).
        # Lower distance = higher similarity. We order by distance ASC to get best matches first.
        stmt = stmt.order_by(
            KnowledgeChunk.embedding.cosine_distance(query_embedding)
        ).limit(limit)

        result = await self._session.execute(stmt)
        chunks = result.scalars().all()

        log.info(
            "knowledge.search",
            query_len=len(query),
            studio_id=str(studio_id),
            results=len(chunks),
        )
        return list(chunks)

    async def add_chunk(
        self,
        studio_id: UUID,
        category: str,
        title: str,
        content: str,
        metadata: dict | None = None,
    ) -> KnowledgeChunk:
        """
        Adds a new knowledge chunk with embedding.
        
        Args:
            studio_id: Studio ID for multi-tenant isolation
            category: Category for filtering (e.g., "products", "services", "faq")
            title: Chunk title
            content: Chunk content (will be embedded)
            metadata: Optional metadata (e.g., price, availability)
            
        Returns:
            Created KnowledgeChunk instance
        """
        embedding = await self._embeddings.embed(f"{title}\n\n{content}")

        chunk = KnowledgeChunk(
            studio_id=studio_id,
            category=category,
            title=title,
            content=content,
            embedding=embedding,
            metadata_=metadata,
        )
        self._session.add(chunk)
        log.info("knowledge.chunk_added", title=title, category=category)
        return chunk
