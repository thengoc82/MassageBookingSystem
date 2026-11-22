# chatbot/scripts/index_knowledge_base.py
import logging
from pathlib import Path

import typer
from chatbot.app.config import Settings
from chatbot.knowledge.chunking import ChunkingConfig
from chatbot.knowledge.document_loader import load_documents
from chatbot.knowledge.embedding_service import SentenceTransformerEmbeddingService
from chatbot.knowledge.ingestion import ingest_document
from chatbot.knowledge.pgvector_store import PgVectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cli = typer.Typer()


def _index_documents(
    root_path: Path,
    vector_store: PgVectorStore,
    chunk_config: ChunkingConfig,
    embedding_service: SentenceTransformerEmbeddingService,
    model_name: str,
    prune: bool = False,
) -> None:
    """Load, chunk, embed, and index all documents."""
    logger.info(f"Loading documents from {root_path}...")
    docs = load_documents(root_path)
    changed = 0
    for doc in docs:
        changed += ingest_document(doc, vector_store, embedding_service, chunk_config, model_name)
    if prune:
        vector_store.prune_source("file", [
            doc.document_id for doc in docs if doc.source == "file"
        ], str(root_path.absolute()))
    logger.info("Indexed %s changed documents; %s unchanged.", changed, len(docs) - changed)


@cli.command()
def index(
    root_dir: str = typer.Option(
        "",
        "--root-dir",
        "-d",
        help="Root directory for knowledge documents. Overrides CHATBOT_KNOWLEDGE_ROOT.",
    ),
    prune: bool = typer.Option(False, "--prune", help="Delete indexed files removed from this source."),
    delete_document: str = typer.Option("", "--delete-document", help="Delete one document by its ID."),
) -> None:
    """Offline indexing command for the knowledge base."""
    settings = Settings()
    knowledge_root = Path(root_dir or settings.knowledge_root)

    chunk_config = ChunkingConfig(
        chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
    )

    if not settings.pg_dsn:
        raise typer.BadParameter("CHATBOT_PG_DSN is required")
    embedding_service = SentenceTransformerEmbeddingService(
        model_name=settings.embedding_model, embedding_dim=settings.embedding_dim
    )

    vector_store = PgVectorStore(
        dsn=settings.pg_dsn,
        embedding_dim=settings.embedding_dim,
        embedding_service=embedding_service,
    )

    try:
        if delete_document:
            vector_store.delete_document(delete_document)
        else:
            _index_documents(
                knowledge_root,
                vector_store,
                chunk_config,
                embedding_service,
                settings.embedding_model,
                prune,
            )
    finally:
        vector_store.close()


if __name__ == "__main__":
    cli()
