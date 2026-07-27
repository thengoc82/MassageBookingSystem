"""Indexing command for the knowledge system.

Loads Markdown files, chunks them, generates embeddings, and stores in the vector store.
This is an offline operation and should not be run during chatbot runtime.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from chatbot.app.config import Settings
from chatbot.knowledge.chunking import ChunkingConfig, chunk_document
from chatbot.knowledge.document_loader import load_documents
from chatbot.knowledge.embedding_service import SentenceTransformerEmbeddingService
from chatbot.knowledge.pgvector_store import PgVectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def index_knowledge(settings: Settings) -> int:
    """Index knowledge documents into the vector store.

    Returns the number of chunks indexed.
    """
    root = Path(settings.knowledge_root)
    logger.info("Loading documents from %s", root)
    documents = load_documents(root)
    logger.info("Loaded %d documents", len(documents))

    if not documents:
        logger.warning("No documents found. Nothing to index.")
        return 0

    chunking_config = ChunkingConfig(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    embedding_service = SentenceTransformerEmbeddingService(
        model_name=settings.embedding_model,
        embedding_dim=settings.embedding_dim,
    )

    vector_store = PgVectorStore(
        dsn=settings.pg_dsn,
        embedding_dim=settings.embedding_dim,
        embedding_service=embedding_service,
    )

    try:
        logger.info("Clearing existing data from vector store")
        vector_store.clear()

        all_chunks = []
        offset = 0
        for doc in documents:
            chunks = chunk_document(doc, chunking_config, source_offset=offset)
            logger.info("Chunked %s into %d chunks", doc.source_file, len(chunks))
            all_chunks.extend(chunks)
            offset += len(chunks)

        if not all_chunks:
            logger.warning("No chunks generated. Nothing to index.")
            return 0

        logger.info("Generating embeddings for %d chunks", len(all_chunks))
        texts = [chunk.content for chunk in all_chunks]
        embeddings = embedding_service.embed_texts(texts)

        logger.info("Storing chunks and embeddings in vector store")
        chunks_with_embeddings = list(zip(all_chunks, [emb.tolist() for emb in embeddings]))
        vector_store.add_chunks(chunks_with_embeddings)

        logger.info("Successfully indexed %d chunks", len(all_chunks))
        return len(all_chunks)
    finally:
        vector_store.close()


def main() -> int:
    """Main entry point for the indexing command."""
    parser = argparse.ArgumentParser(description="Index knowledge documents into the vector store")
    parser.add_argument(
        "--knowledge-root",
        type=str,
        help="Root directory containing Markdown knowledge files",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        help="Maximum chunk size in characters",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        help="Overlap between chunks in characters",
    )
    parser.add_argument(
        "--embedding-model",
        type=str,
        help="Name of the sentence-transformers model to use",
    )
    parser.add_argument(
        "--embedding-dim",
        type=int,
        help="Embedding dimension",
    )
    parser.add_argument(
        "--pg-dsn",
        type=str,
        help="PostgreSQL DSN for the vector store",
    )

    args = parser.parse_args()

    settings = Settings()
    if args.knowledge_root:
        settings.knowledge_root = args.knowledge_root
    if args.chunk_size:
        settings.chunk_size = args.chunk_size
    if args.chunk_overlap:
        settings.chunk_overlap = args.chunk_overlap
    if args.embedding_model:
        settings.embedding_model = args.embedding_model
    if args.embedding_dim:
        settings.embedding_dim = args.embedding_dim
    if args.pg_dsn:
        settings.pg_dsn = args.pg_dsn

    count = index_knowledge(settings)
    logger.info("Indexing complete. %d chunks indexed.", count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
