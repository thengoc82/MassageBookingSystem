"""Incremental ingestion of Markdown FAQ and business documents."""

from dataclasses import replace
from hashlib import sha256
import json

import numpy as np

from chatbot.knowledge.chunking import ChunkingConfig, chunk_document
from chatbot.knowledge.document_loader import LoadedDocument
from chatbot.knowledge.embedding_service import EmbeddingService
from chatbot.knowledge.pgvector_store import PgVectorStore


def ingest_document(
    document: LoadedDocument,
    store: PgVectorStore,
    embeddings: EmbeddingService,
    config: ChunkingConfig,
    model_name: str,
) -> bool:
    """Return True when the document changed and was indexed."""
    document_id = document.document_id or document.source_file
    normalized = "\n".join(line.rstrip() for line in document.content.replace("\r\n", "\n").split("\n")).strip()
    normalized = "\n\n".join(part for part in normalized.split("\n\n") if part.strip())
    document = replace(document, document_id=document_id, content=normalized)
    fingerprint = sha256(json.dumps({
        "title": document.title, "content": normalized, "category": document.category,
        "shop_id": document.shop_id, "language": document.language,
        "source": document.source, "active": document.active,
        "chunk_size": config.chunk_size, "chunk_overlap": config.chunk_overlap,
        "embedding_model": model_name,
    }, sort_keys=True).encode()).hexdigest()
    if store.document_hash(document_id) == fingerprint:
        return False
    chunks = [replace(chunk, content_hash=fingerprint) for chunk in chunk_document(document, config)]
    vectors = embeddings.embed_texts([chunk.content for chunk in chunks]) if chunks else []
    if len(vectors) != len(chunks):
        raise ValueError("Embedding provider returned an unexpected number of vectors")
    store.replace_document(document_id, [
        (chunk, np.asarray(vector, dtype=float).tolist())
        for chunk, vector in zip(chunks, vectors)
    ])
    return True
