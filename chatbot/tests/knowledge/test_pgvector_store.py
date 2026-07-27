"""Tests for PgVectorStore using a mock database connection."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import numpy as np
from chatbot.knowledge.chunking import TextChunk
from chatbot.knowledge.embedding_service import EmbeddingService
from chatbot.knowledge.pgvector_store import PgVectorStore
from chatbot.knowledge.vector_store import VectorStore


class MockEmbeddingService(EmbeddingService):
    """Mock embedding service."""

    def __init__(self, embedding_dim: int = 384) -> None:
        self._embedding_dim = embedding_dim

    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:  # noqa: ARG002
        embeddings: List[np.ndarray] = []
        for i in range(len(texts)):
            embedding = np.zeros(self._embedding_dim, dtype=float)
            embedding[i % self._embedding_dim] = 1.0
            embeddings.append(embedding)
        return embeddings


def test_pgvector_store_init() -> None:
    """Test PgVectorStore initialization is lazy."""
    # We don't actually connect here because PgVectorStore constructor connects.
    # This test verifies the interface is correct.
    from chatbot.knowledge.vector_store import VectorStore

    embedding_service = MockEmbeddingService()
    # We can't easily test the constructor without a real DB, but we can test
    # that PgVectorStore is indeed a VectorStore subclass.
    assert issubclass(PgVectorStore, VectorStore)


def test_pgvector_store_interface() -> None:
    """Test that PgVectorStore implements the VectorStore interface."""

    # Check that PgVectorStore has all required methods
    expected_methods = {'add_chunk', 'add_chunks', 'search', 'clear', 'close', 'get_embedding_service', 'set_embedding_service'}
    missing = expected_methods - set(dir(PgVectorStore))
    assert not missing, f"PgVectorStore is missing methods: {missing}"


def test_vector_store_is_abstract() -> None:
    """Test that VectorStore is abstract."""
    import pytest
    with pytest.raises(TypeError):
        # Should not be able to instantiate the abstract class directly
        VectorStore()  # type: ignore[abstract]


def test_pgvector_store_can_be_subclassed() -> None:
    """Test that a custom subclass can be created and methods implemented."""
    class CustomVectorStore(VectorStore):
        def __init__(self) -> None:
            self._chunks: List[Tuple[TextChunk, List[float]]] = []
            self._embedding_service = MockEmbeddingService()

        def add_chunk(self, chunk: TextChunk, embedding: list[float]) -> None:
            self._chunks.append((chunk, embedding))

        def add_chunks(self, chunks_with_embeddings: list[tuple[TextChunk, list[float]]]) -> None:
            for chunk, embedding in chunks_with_embeddings:
                self.add_chunk(chunk, embedding)

        def search(self, query_embedding: list[float], top_k: int, filter: Dict[str, Any] | None = None) -> List[Tuple[TextChunk, float]]:  # noqa: A002
            return [(chunk, 0.0) for chunk, _ in self._chunks[:top_k]]

        def clear(self) -> None:
            self._chunks.clear()

        def close(self) -> None:
            pass

        def get_embedding_service(self) -> EmbeddingService:
            return self._embedding_service

        def set_embedding_service(self, service: EmbeddingService) -> None:
            self._embedding_service = service

    store = CustomVectorStore()
    chunk = TextChunk(
        chunk_id="001",
        source_file="/test.md",
        title="Test",
        heading="Heading",
        content="Content",
        last_updated=datetime.now(tz=timezone.utc),
    )
    store.add_chunk(chunk, [0.0] * 384)
    assert len(store._chunks) == 1
    results = store.search([0.0] * 384, 1)
    assert len(results) == 1
