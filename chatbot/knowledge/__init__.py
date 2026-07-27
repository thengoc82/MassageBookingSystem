"""Knowledge system components."""

from chatbot.knowledge.chunking import ChunkingConfig, TextChunk, chunk_document
from chatbot.knowledge.document_loader import (
    LoadedDocument,
    discover_markdown_files,
    load_document,
    load_documents,
)
from chatbot.knowledge.embedding_service import (
    EmbeddingService,
    SentenceTransformerEmbeddingService,
)
from chatbot.knowledge.knowledge_service import KnowledgeResult, KnowledgeService
from chatbot.knowledge.pgvector_store import PgVectorStore
from chatbot.knowledge.vector_store import VectorStore

__all__ = [
    "ChunkingConfig",
    "TextChunk",
    "chunk_document",
    "LoadedDocument",
    "discover_markdown_files",
    "load_document",
    "load_documents",
    "EmbeddingService",
    "SentenceTransformerEmbeddingService",
    "KnowledgeResult",
    "KnowledgeService",
    "PgVectorStore",
    "VectorStore",
]
