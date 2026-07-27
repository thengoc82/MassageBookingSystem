"""PgVectorStore implementation using PostgreSQL with pgvector extension."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

import psycopg2
from pgvector.psycopg2 import register_vector

from chatbot.knowledge.chunking import TextChunk
from chatbot.knowledge.embedding_service import EmbeddingService
from chatbot.knowledge.vector_store import VectorStore

logger = logging.getLogger(__name__)


class PgVectorStore(VectorStore):
    """Vector store implementation using PostgreSQL with pgvector."""

    def __init__(
        self,
        dsn: str,
        embedding_dim: int,
        embedding_service: EmbeddingService,
        *,
        table_name: str = "knowledge_chunks",
    ) -> None:
        self._dsn = dsn
        self._embedding_dim = embedding_dim
        self._embedding_service = embedding_service
        self._table_name = table_name
        self._conn = psycopg2.connect(dsn)
        self._conn.autocommit = False
        register_vector(self._conn)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create the pgvector extension and the table if they don't exist."""
        with self._conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._table_name} (
                    chunk_id TEXT PRIMARY KEY,
                    source_file TEXT NOT NULL,
                    title TEXT NOT NULL,
                    heading TEXT NOT NULL,
                    content TEXT NOT NULL,
                    last_updated TIMESTAMPTZ NOT NULL,
                    embedding VECTOR({self._embedding_dim}) NOT NULL
                )
                """
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS {self._table_name}_embedding_idx "
                f"ON {self._table_name} USING ivfflat (embedding vector_cosine_ops)"
            )
        self._conn.commit()

    def add_chunk(self, chunk: TextChunk, embedding: list[float]) -> None:
        """Insert a single chunk with its embedding."""
        self.add_chunks([(chunk, embedding)])

    def add_chunks(self, chunks_with_embeddings: list[tuple[TextChunk, list[float]]]) -> None:
        """Insert multiple chunks with their embeddings in a batch."""
        if not chunks_with_embeddings:
            return

        with self._conn.cursor() as cur:
            for chunk, embedding in chunks_with_embeddings:
                cur.execute(
                    f"""
                    INSERT INTO {self._table_name}
                        (chunk_id, source_file, title, heading, content, last_updated, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        source_file = EXCLUDED.source_file,
                        title = EXCLUDED.title,
                        heading = EXCLUDED.heading,
                        content = EXCLUDED.content,
                        last_updated = EXCLUDED.last_updated,
                        embedding = EXCLUDED.embedding
                    """,
                    (
                        chunk.chunk_id,
                        chunk.source_file,
                        chunk.title,
                        chunk.heading,
                        chunk.content,
                        chunk.last_updated,
                        json.dumps(embedding),
                    ),
                )
        self._conn.commit()

    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        filter: Dict[str, Any] | None = None,  # noqa: A002
    ) -> list[tuple[TextChunk, float]]:
        """Search for similar chunks using cosine similarity."""
        where_clauses = []
        params: List[Any] = [json.dumps(query_embedding), top_k]
        if filter:
            if "title" in filter:
                where_clauses.append("title = %s")
                params.append(filter["title"])
            if "source_file" in filter:
                where_clauses.append("source_file = %s")
                params.append(filter["source_file"])

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        sql = f"""
            SELECT chunk_id, source_file, title, heading, content, last_updated,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM {self._table_name}
            {where_sql}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        results: list[tuple[TextChunk, float]] = []
        for row in rows:
            chunk_id, source_file, title, heading, content, last_updated, similarity = row
            chunk = TextChunk(
                chunk_id=chunk_id,
                source_file=source_file,
                title=title,
                heading=heading,
                content=content,
                last_updated=last_updated,
            )
            results.append((chunk, similarity))
        return results

    def clear(self) -> None:
        """Clear all data from the store."""
        with self._conn.cursor() as cur:
            cur.execute(f"DELETE FROM {self._table_name}")
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()

    def get_embedding_service(self) -> EmbeddingService:
        """Get the configured embedding service."""
        return self._embedding_service

    def set_embedding_service(self, service: EmbeddingService) -> None:
        """Set the embedding service to use."""
        self._embedding_service = service
