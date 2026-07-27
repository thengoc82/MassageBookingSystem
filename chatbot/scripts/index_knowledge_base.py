# chatbot/scripts/index_knowledge_base.py
import asyncio
import logging
from pathlib import Path

import typer
from chatbot.app.config import Settings
from chatbot.knowledge.chunking import ChunkingConfig, chunk_document
from chatbot.knowledge.document_loader import load_documents
from chatbot.knowledge.embedding_service import SentenceTransformerEmbeddingService
from chatbot.knowledge.pgvector_store import PgVectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cli = typer.Typer()


async def _index_documents(
    root_path: Path,
    vector_store: PgVectorStore,
    chunk_config: ChunkingConfig,
    embedding_service: SentenceTransformerEmbeddingService,
) -> None:
    """Load, chunk, embed, and index all documents."""
    logger.info(f"Loading documents from {root_path}...")
    docs = load_documents(root_path)
    if not docs:
        logger.warning("No documents found. Exiting.")
        return

    logger.info(f"Found {len(docs)} documents. Chunking...")
    all_chunks = []
    offset = 0
    for doc in docs:
        doc_chunks = chunk_document(doc, chunk_config, source_offset=offset)
        all_chunks.extend(doc_chunks)
        offset += len(doc_chunks)

    logger.info(f"Total chunks created: {len(all_chunks)}. Generating embeddings...")
    contents = [chunk.content for chunk in all_chunks]
    embeddings = embedding_service.embed_texts(contents)

    chunks_with_embeddings = [
        (chunk, embedding.tolist()) for chunk, embedding in zip(all_chunks, embeddings)
    ]

    msg = (
        f"Clearing old data and adding {len(chunks_with_embeddings)} "
        "new chunks to the vector store..."
    )
    logger.info(msg)
    vector_store.clear()
    vector_store.add_chunks(chunks_with_embeddings)
    logger.info("Indexing complete.")


@cli.command()
def index(
    root_dir: str = typer.Option(
        "",
        "--root-dir",
        "-d",
        help="Root directory for knowledge documents. Overrides CHATBOT_KNOWLEDGE_ROOT.",
    )
) -> None:
    """Offline indexing command for the knowledge base."""
    settings = Settings()
    knowledge_root = Path(root_dir or settings.knowledge_root)

    chunk_config = ChunkingConfig(
        chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
    )

    embedding_service = SentenceTransformerEmbeddingService(
        model_name=settings.embedding_model, embedding_dim=settings.embedding_dim
    )

    vector_store = PgVectorStore(
        dsn=settings.pg_dsn,
        embedding_dim=settings.embedding_dim,
        embedding_service=embedding_service,
    )

    try:
        asyncio.run(
            _index_documents(
                knowledge_root,
                vector_store,
                chunk_config,
                embedding_service,
            )
        )
    finally:
        vector_store.close()


if __name__ == "__main__":
    cli()
