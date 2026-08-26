import asyncio
import logging
from pathlib import Path

from chatbot.app.config import Settings
from chatbot.knowledge.chunking import chunk_document, ChunkingConfig
from chatbot.knowledge.document_loader import load_documents
from chatbot.knowledge.embedding_service import SentenceTransformerEmbeddingService
from chatbot.knowledge.pgvector_store import PgVectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Load documents, chunk them, embed them, and store them in the vector store."""
    settings = Settings()
    
    # Initialize services
    embedding_service = SentenceTransformerEmbeddingService(
        model_name="all-MiniLM-L6-v2"
    )
    settings.embedding_dim = embedding_service.embedding_dim
    vector_store = PgVectorStore(
        dsn=settings.pg_dsn,
        embedding_dim=settings.embedding_dim,
        embedding_service=embedding_service,
    )
    
    # Load documents
    # Construct path relative to the script's parent directory (project root)
    script_dir = Path(__file__).parent.parent.parent
    knowledge_root = script_dir / settings.knowledge_root
    logger.info(f"Loading documents from {knowledge_root}...")
    documents = load_documents(knowledge_root)
    if not documents:
        logger.warning("No documents found. Nothing to ingest.")
        return

    logger.info(f"Found {len(documents)} documents.")

    # Chunk documents
    chunking_config = ChunkingConfig(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
    chunks = []
    for doc in documents:
        chunks.extend(chunk_document(doc, chunking_config))
    
    logger.info(f"Created {len(chunks)} chunks.")

    # Embed and store chunks
    chunks_with_embeddings = []
    for chunk in chunks:
        embedding = embedding_service.embed_texts([chunk.content])[0]
        chunks_with_embeddings.append((chunk, embedding))
        
    logger.info("Adding chunks to vector store...")
    vector_store.add_chunks(chunks_with_embeddings)
    
    logger.info("Ingestion complete.")
    vector_store.close()

if __name__ == "__main__":
    asyncio.run(main())
