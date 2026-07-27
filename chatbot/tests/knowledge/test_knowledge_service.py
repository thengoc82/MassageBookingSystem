"""Tests for KnowledgeService."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import numpy as np
from chatbot.knowledge.chunking import TextChunk
from chatbot.knowledge.embedding_service import EmbeddingService
from chatbot.knowledge.knowledge_service import KnowledgeResult, KnowledgeService
from chatbot.knowledge.vector_store import VectorStore


class MockEmbeddingService(EmbeddingService):
    """Mock embedding service."""

    def __init__(self, embedding_dim: int = 384) -> None:
        self._embedding_dim = embedding_dim

    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        embeddings = []
        for i, text in enumerate(texts):
            embedding = np.zeros(self._embedding_dim, dtype=float)
            embedding[i % self._embedding_dim] = 1.0
            embeddings.append(embedding)
        return embeddings


class MockVectorStore(VectorStore):
    """Mock vector store for testing."""

    def __init__(self, embedding_service: EmbeddingService) -> None:
        self._chunks: List[Tuple[TextChunk, float]] = []
        self._embedding_service = embedding_service

    def add_chunk(self, chunk: TextChunk, embedding: list[float]) -> None:
        self._chunks.append((chunk, 0.0))

    def add_chunks(self, chunks_with_embeddings: list[tuple[TextChunk, list[float]]]) -> None:
        for chunk, _ in chunks_with_embeddings:
            self._chunks.append((chunk, 0.0))

    def search(self, query_embedding: list[float], top_k: int, filter: Dict[str, Any] | None = None) -> List[Tuple[TextChunk, float]]:  # noqa: A002
        return self._chunks[:top_k]

    def clear(self) -> None:
        self._chunks.clear()

    def close(self) -> None:
        pass

    def get_embedding_service(self) -> EmbeddingService:
        return self._embedding_service

    def set_embedding_service(self, service: EmbeddingService) -> None:
        self._embedding_service = service


def test_knowledge_service_init() -> None:
    """Test KnowledgeService initialization."""
    embedding_service = MockEmbeddingService()
    vector_store = MockVectorStore(embedding_service)
    service = KnowledgeService(vector_store, embedding_service)

    assert service.vector_store == vector_store
    assert service.embedding_service == embedding_service


def test_knowledge_service_uses_vector_store_embedding_service() -> None:
    """Test that KnowledgeService uses vector store's embedding service if not provided."""
    embedding_service = MockEmbeddingService()
    vector_store = MockVectorStore(embedding_service)
    service = KnowledgeService(vector_store)

    assert service.embedding_service == embedding_service


def test_knowledge_service_query() -> None:
    """Test knowledge service query."""
    chunk = TextChunk(
        chunk_id="001",
        source_file="/test.md",
        title="Test Doc",
        heading="Heading 1",
        content="Test content",
        last_updated=datetime.now(tz=timezone.utc),
    )
    embedding_service = MockEmbeddingService()
    vector_store = MockVectorStore(embedding_service)
    vector_store.add_chunk(chunk, [0.0] * 384)
    service = KnowledgeService(vector_store, embedding_service)

    results = service.query("test query", top_k=1)
    assert len(results) == 1
    assert isinstance(results[0], KnowledgeResult)
    assert results[0].chunk_id == "001"
    assert results[0].source_file == "/test.md"
    assert results[0].title == "Test Doc"
    assert results[0].heading == "Heading 1"


def test_knowledge_service_empty_query() -> None:
    """Test knowledge service with empty query."""
    embedding_service = MockEmbeddingService()
    vector_store = MockVectorStore(embedding_service)
    service = KnowledgeService(vector_store, embedding_service)

    results = service.query("", top_k=1)
    assert results == []


def test_knowledge_service_query_with_top_k() -> None:
    """Test knowledge service with top_k parameter."""
    chunks = [
        TextChunk(
            chunk_id=f"{i:03d}",
            source_file="/test.md",
            title="Test Doc",
            heading=f"Heading {i}",
            content=f"Content {i}",
            last_updated=datetime.now(tz=timezone.utc),
        )
        for i in range(5)
    ]
    embedding_service = MockEmbeddingService()
    vector_store = MockVectorStore(embedding_service)
    for chunk in chunks:
        vector_store.add_chunk(chunk, [0.0] * 384)
    service = KnowledgeService(vector_store, embedding_service)

    results = service.query("test", top_k=3)
    assert len(results) == 3


def test_citation_includes_required_fields() -> None:
    """Test that KnowledgeResult includes all citation fields."""
    chunk = TextChunk(
        chunk_id="001",
        source_file="/faq.md",
        title="FAQ",
        heading="Opening Hours",
        content="We are open from 10am to 10pm",
        last_updated=datetime.now(tz=timezone.utc),
    )
    embedding_service = MockEmbeddingService()
    vector_store = MockVectorStore(embedding_service)
    vector_store.add_chunk(chunk, [0.0] * 384)
    service = KnowledgeService(vector_store, embedding_service)

    results = service.query("hours", top_k=1)
    assert len(results) == 1
    result = results[0]
    assert result.source_file == "/faq.md"
    assert result.title == "FAQ"
    assert result.heading == "Opening Hours"
    assert result.content == "We are open from 10am to 10pm"
    assert result.chunk_id == "001"
    assert isinstance(result.score, float)
