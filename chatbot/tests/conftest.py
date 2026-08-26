import pytest
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from chatbot.app.config import Settings

@pytest.fixture(scope="session")
def settings():
    """Returns a settings object for the tests."""
    return Settings()

@pytest.fixture(scope="session")
def db_connection(settings):
    """Yields a database connection."""
    try:
        conn = psycopg2.connect(settings.pg_dsn)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        yield conn
        conn.close()
    except psycopg2.OperationalError as e:
        pytest.skip(f"PostgreSQL connection failed: {e}. Make sure the database is running and the DSN is correct.")

@pytest.fixture(scope="function")
def test_db(db_connection):
    """Creates a clean test database for each test function."""
    with db_connection.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS knowledge_chunks;")
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("""
            CREATE TABLE knowledge_chunks (
                chunk_id TEXT PRIMARY KEY,
                source_file TEXT NOT NULL,
                title TEXT NOT NULL,
                heading TEXT NOT NULL,
                content TEXT NOT NULL,
                last_updated TIMESTAMPTZ NOT NULL,
                embedding VECTOR(1536) NOT NULL
            );
        """)
    yield db_connection

@pytest.fixture(scope="function")
def temp_knowledge_base(tmp_path):
    """Creates a temporary knowledge base directory with a dummy file."""
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    faq_file = knowledge_dir / "faq.md"
    faq_file.write_text("""
# Frequently Asked Questions

## What are your opening hours?
We are open from 9 AM to 9 PM every day.

## What is the cancellation policy?
You can cancel up to 24 hours before your appointment for a full refund.
""")
    return knowledge_dir
