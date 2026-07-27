"""VectorStore interface definition.

Defines the contract for storing and retrieving vector embeddings.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from chatbot.knowledge.chunking import TextChunk
from chatbot.knowledge.embedding_service import EmbeddingService


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    def add_chunk(self, chunk: TextChunk, embedding: list[float]) -> None:
        """Store a single chunk with its embedding."""
        raise NotImplementedError

    @abstractmethod
    def add_chunks(self, chunks_with_embeddings: list[tuple[TextChunk, list[float]]]) -> None:
        """Store multiple chunks with their embeddings in a batch."""
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        filter: Dict[str, Any] | None = None,
    ) -> list[tuple[TextChunk, float]]:
        """Search for similar chunks using vector similarity.

        Returns list of (chunk, similarity_score).
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """Clear all data from the store."""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Clean up resources."""
        raise NotImplementedError

    @abstractmethod
    def get_embedding_service(self) -> EmbeddingService:
        """Get the configured embedding service."""
        raise NotImplementedError

    @abstractmethod
    def set_embedding_service(self, service: EmbeddingService) -> None:
        """Set the embedding service to use."""
        raise NotImplementedError
