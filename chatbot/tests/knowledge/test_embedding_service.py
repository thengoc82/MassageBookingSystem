"""Tests for embedding service."""

from typing import List

import numpy as np
from chatbot.knowledge.embedding_service import (
    EmbeddingService,
)


class MockEmbeddingService(EmbeddingService):
    """Mock embedding service for testing."""

    def __init__(self, embedding_dim: int = 384) -> None:
        self._embedding_dim = embedding_dim

    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        embeddings = []
        for i, text in enumerate(texts):
            # Create a deterministic mock embedding
            embedding = np.zeros(self._embedding_dim, dtype=float)
            embedding[i % self._embedding_dim] = 1.0
            embeddings.append(embedding)
        return embeddings


def test_mock_embedding_service() -> None:
    """Test the mock embedding service."""
    service = MockEmbeddingService(embedding_dim=10)
    texts = ["hello", "world"]
    embeddings = service.embed_texts(texts)

    assert len(embeddings) == 2
    assert all(emb.shape == (10,) for emb in embeddings)
    assert embeddings[0][0] == 1.0
    assert embeddings[1][1] == 1.0


def test_embedding_service_is_abstract() -> None:
    """Test that EmbeddingService is abstract."""
    import pytest
    with pytest.raises(TypeError):
        # Should not be able to instantiate the abstract class directly
        EmbeddingService()  # type: ignore[abstract]


def test_embedding_service_can_be_subclassed() -> None:
    """Test that a concrete subclass works."""
    service = MockEmbeddingService()
    assert isinstance(service, EmbeddingService)
    embeddings = service.embed_texts(["test"])
    assert len(embeddings) == 1
