import pytest
import asyncio
from chatbot.scripts.ingest import main as ingest_main
from chatbot.knowledge.knowledge_service import KnowledgeService
from chatbot.knowledge.pgvector_store import PgVectorStore
from chatbot.knowledge.embedding_service import OpenAIEmbeddingService
from chatbot.app.chat_endpoint import ChatEndpoint, ChatRequest

pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_document_ingestion(settings, test_db, temp_knowledge_base):
    """Test the document ingestion process."""
    settings.knowledge_root = str(temp_knowledge_base)
    
    await ingest_main()

    with test_db.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM knowledge_chunks")
        count = cur.fetchone()[0]
        assert count > 0

@pytest.mark.asyncio
async def test_vector_similarity_search(settings, test_db, temp_knowledge_base):
    """Test vector similarity search."""
    settings.knowledge_root = str(temp_knowledge_base)
    await ingest_main()

    embedding_service = OpenAIEmbeddingService(
        api_key=settings.openai_api_key,
        model_name=settings.embedding_model,
        embedding_dim=settings.embedding_dim,
    )
    vector_store = PgVectorStore(
        dsn=settings.pg_dsn,
        embedding_dim=settings.embedding_dim,
        embedding_service=embedding_service,
    )
    knowledge_service = KnowledgeService(vector_store, embedding_service)

    # Test exact match
    results = knowledge_service.query("What are your opening hours?")
    assert len(results) > 0
    assert "9 am to 9 pm" in results[0].content.lower()

    # Test semantic match
    results = knowledge_service.query("When do you guys open?")
    assert len(results) > 0
    assert "9 am to 9 pm" in results[0].content.lower()

    vector_store.close()

@pytest.mark.asyncio
async def test_faq_flow(settings, test_db, temp_knowledge_base):
    """Test the full FAQ flow from question to answer."""
    settings.knowledge_root = str(temp_knowledge_base)
    await ingest_main()

    chat_endpoint = ChatEndpoint(settings=settings)
    await chat_endpoint.initialize()

    request = ChatRequest(
        message="What are your opening hours?",
        session_id="test-session-faq",
        user_id="test-user-faq",
    )
    response = await chat_endpoint.process_message(request)

    assert response.success
    assert "9 am to 9 pm" in response.message.lower()
    
    await chat_endpoint.close()
