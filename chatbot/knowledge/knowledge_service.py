"""KnowledgeService - high-level interface for the knowledge system.

Provides simple methods for the FAQ tool to query the knowledge base.
Handles embedding of user queries and vector search.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from chatbot.knowledge.embedding_service import EmbeddingService
from chatbot.knowledge.vector_store import VectorStore


@dataclass
class KnowledgeResult:
    """A search result with citation information."""

    chunk_id: str
    source_file: str
    title: str
    heading: str
    content: str
    score: float


class KnowledgeService:
    """High-level service for querying the knowledge base."""

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._vector_store = vector_store
        self._embedding_service = embedding_service or vector_store.get_embedding_service()

    @property
    def vector_store(self) -> VectorStore:
        """Get the underlying vector store."""
        return self._vector_store

    @property
    def embedding_service(self) -> EmbeddingService:
        """Get the embedding service."""
        return self._embedding_service

    def query(self, query_text: str, top_k: int = 5) -> List[KnowledgeResult]:
        """Query the knowledge base with a text query.

        Embeds the query and performs vector search.
        Returns a list of relevant chunks with metadata.
        """
        if not query_text or not query_text.strip():
            return []

        query_embeddings = self._embedding_service.embed_texts([query_text])
        if not query_embeddings:
            return []

        query_vector = np.asarray(query_embeddings[0], dtype=float).tolist()
        results = self._vector_store.search(query_vector, top_k)

        return [
            KnowledgeResult(
                chunk_id=chunk.chunk_id,
                source_file=chunk.source_file,
                title=chunk.title,
                heading=chunk.heading,
                content=chunk.content,
                score=score,
            )
            for chunk, score in results
        ]
