"""PgVectorStore implementation using PostgreSQL with pgvector extension."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List

import psycopg2
from psycopg2 import sql
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
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name):
            raise ValueError("Invalid knowledge table name")
        self._table_name = table_name
        # Lazy: don't connect at startup. App can boot without PostgreSQL;
        # DB-backed methods (search, add, clear) will fail loudly if called
        # and the DB is unreachable, with the underlying psycopg2 error.
        self._conn: psycopg2.extensions.connection | None = None

    def _connect(self) -> psycopg2.extensions.connection:
        """Open the connection on first use and ensure the schema exists."""
        if self._conn is not None and not self._conn.closed:
            return self._conn
        self._conn = psycopg2.connect(self._dsn)
        self._conn.autocommit = False
        try:
            self._ensure_schema()
            register_vector(self._conn)
        except Exception:
            self._conn.close()
            self._conn = None
            raise
        return self._conn

    def _ensure_schema(self) -> None:
        """Create the pgvector extension and the table if they don't exist."""
        assert self._conn is not None, "connect before _ensure_schema"
        table = sql.Identifier(self._table_name)
        with self._conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(
                sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    chunk_id TEXT PRIMARY KEY,
                    source_file TEXT NOT NULL,
                    title TEXT NOT NULL,
                    heading TEXT NOT NULL,
                    content TEXT NOT NULL,
                    last_updated TIMESTAMPTZ NOT NULL,
                    embedding VECTOR({}) NOT NULL
                )
                """).format(table, sql.Literal(self._embedding_dim))
            )
            for column, definition in (
                ("document_id", "TEXT"), ("category", "TEXT"),
                ("shop_id", "INTEGER"), ("language", "TEXT NOT NULL DEFAULT 'en'"),
                ("source", "TEXT NOT NULL DEFAULT 'file'"),
                ("active", "BOOLEAN NOT NULL DEFAULT TRUE"),
                ("content_hash", "TEXT NOT NULL DEFAULT ''"),
            ):
                cur.execute(
                    sql.SQL("ALTER TABLE {} ADD COLUMN IF NOT EXISTS {} {}").format(
                        table, sql.Identifier(column), sql.SQL(definition)
                    )
                )
            cur.execute(sql.SQL("UPDATE {} SET document_id = source_file WHERE document_id IS NULL").format(table))
            cur.execute(
                sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} USING ivfflat (embedding vector_cosine_ops)").format(
                    sql.Identifier(self._table_name + "_embedding_idx"), table
                )
            )
        self._conn.commit()

    def add_chunk(self, chunk: TextChunk, embedding: list[float]) -> None:
        """Insert a single chunk with its embedding."""
        self.add_chunks([(chunk, embedding)])

    def add_chunks(self, chunks_with_embeddings: list[tuple[TextChunk, list[float]]]) -> None:
        """Insert multiple chunks with their embeddings in a batch."""
        if not chunks_with_embeddings:
            return

        conn = self._connect()
        try:
            with conn.cursor() as cur:
                self._insert_chunks(cur, chunks_with_embeddings)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _insert_chunks(self, cur: Any, items: list[tuple[TextChunk, list[float]]]) -> None:
        statement = sql.SQL("""
            INSERT INTO {} (chunk_id, source_file, title, heading, content,
                last_updated, embedding, document_id, category, shop_id,
                language, source, active, content_hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s::vector, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (chunk_id) DO UPDATE SET
                source_file = EXCLUDED.source_file, title = EXCLUDED.title,
                heading = EXCLUDED.heading, content = EXCLUDED.content,
                last_updated = EXCLUDED.last_updated, embedding = EXCLUDED.embedding,
                document_id = EXCLUDED.document_id, category = EXCLUDED.category,
                shop_id = EXCLUDED.shop_id, language = EXCLUDED.language,
                source = EXCLUDED.source, active = EXCLUDED.active,
                content_hash = EXCLUDED.content_hash
        """).format(sql.Identifier(self._table_name))
        for chunk, embedding in items:
            if len(embedding) != self._embedding_dim:
                raise ValueError("Embedding dimension does not match configured vector size")
            cur.execute(statement, (
                chunk.chunk_id, chunk.source_file, chunk.title, chunk.heading,
                chunk.content, chunk.last_updated, json.dumps(embedding),
                chunk.document_id or chunk.source_file, chunk.category, chunk.shop_id,
                chunk.language, chunk.source, chunk.active, chunk.content_hash,
            ))

    def document_hash(self, document_id: str) -> str | None:
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute(sql.SQL("SELECT content_hash FROM {} WHERE document_id = %s LIMIT 1").format(
                sql.Identifier(self._table_name)), (document_id,))
            row = cur.fetchone()
        return row[0] if row else None

    def replace_document(self, document_id: str, items: list[tuple[TextChunk, list[float]]]) -> None:
        """Replace one document atomically, including chunks removed by an edit."""
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                paths = []
                if items:
                    path = items[0][0].source_file
                    paths = [path, os.path.relpath(path)]
                cur.execute(sql.SQL(
                    "DELETE FROM {} WHERE document_id = %s OR source_file = ANY(%s)"
                ).format(sql.Identifier(self._table_name)), (document_id, paths))
                self._insert_chunks(cur, items)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def delete_document(self, document_id: str) -> None:
        self.replace_document(document_id, [])

    def prune_source(self, source: str, document_ids: list[str], root: str) -> None:
        """Delete removed files under one directory without touching other roots."""
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute(sql.SQL(
                "DELETE FROM {} WHERE source = %s AND source_file LIKE %s ESCAPE '\\' "
                "AND NOT (document_id = ANY(%s))"
            ).format(sql.Identifier(self._table_name)), (
                source, root.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_").rstrip("/") + "/%",
                document_ids,
            ))
        conn.commit()

    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        filter: Dict[str, Any] | None = None,  # noqa: A002
    ) -> list[tuple[TextChunk, float]]:
        """Search for similar chunks using cosine similarity."""
        if len(query_embedding) != self._embedding_dim:
            raise ValueError("Query embedding dimension does not match configured vector size")
        where_clauses = ["active = TRUE"]
        params: List[Any] = [json.dumps(query_embedding)]
        allowed = {"document_id", "category", "shop_id", "language", "source", "source_file", "title", "active"}
        if filter:
            unknown = set(filter) - allowed
            if unknown:
                raise ValueError(f"Unsupported knowledge filter: {sorted(unknown)}")
            for key, value in filter.items():
                if key == "active":
                    if value is False:
                        where_clauses = ["active = FALSE"]
                    continue
                if key == "shop_id":
                    where_clauses.append("(shop_id = %s OR shop_id IS NULL)")
                    params.append(value)
                    continue
                where_clauses.append(f"{key} = %s")
                params.append(value)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        statement = f"""
            SELECT chunk_id, source_file, title, heading, content, last_updated,
                   document_id, category, shop_id, language, source, active, content_hash,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM {self._table_name}
            {where_sql}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        params.extend([json.dumps(query_embedding), top_k])
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute(statement, params)
            rows = cur.fetchall()

        results: list[tuple[TextChunk, float]] = []
        for row in rows:
            (chunk_id, source_file, title, heading, content, last_updated,
             document_id, category, shop_id, language, source, active,
             content_hash, similarity) = row
            chunk = TextChunk(
                chunk_id=chunk_id,
                source_file=source_file,
                title=title,
                heading=heading,
                content=content,
                last_updated=last_updated,
                document_id=document_id, category=category, shop_id=shop_id,
                language=language, source=source, active=active,
                content_hash=content_hash,
            )
            results.append((chunk, similarity))
        return results

    def clear(self) -> None:
        """Clear all data from the store."""
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {self._table_name}")
        conn.commit()

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
