from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

from chatbot.knowledge.chunking import ChunkingConfig
from chatbot.knowledge.document_loader import LoadedDocument, load_document
from chatbot.knowledge.ingestion import ingest_document


def test_frontmatter_business_metadata(tmp_path: Path) -> None:
    path = tmp_path / "service.md"
    path.write_text("""---
document_id: service-full-body
title: Full Body Massage
category: services
shop_id: 2
language: en
source: shop-guide
active: false
---
# Full Body Massage
Provides a full body treatment.
""")
    doc = load_document(path)
    assert (doc.document_id, doc.category, doc.shop_id, doc.language, doc.source, doc.active) == (
        "service-full-body", "services", 2, "en", "shop-guide", False
    )


def test_ingest_skips_duplicates_and_replaces_updated_chunks() -> None:
    doc = LoadedDocument(
        source_file="/service.md", title="Full Body Massage",
        content="# Service\nProvides a full body treatment.",
        headings=["Service"], last_updated=datetime.now(timezone.utc),
        document_id="service-full-body", category="services",
    )
    store = MagicMock()
    store.document_hash.return_value = None
    embedding = MagicMock()
    embedding.embed_texts.side_effect = lambda texts: np.ones((len(texts), 3))
    config = ChunkingConfig(chunk_size=100, chunk_overlap=10)

    assert ingest_document(doc, store, embedding, config, "model")
    document_id, items = store.replace_document.call_args.args
    assert document_id == "service-full-body"
    assert items[0][0].category == "services"
    assert len(items[0][1]) == 3
    first_id = items[0][0].chunk_id
    store.document_hash.return_value = items[0][0].content_hash
    assert not ingest_document(doc, store, embedding, config, "model")
    assert embedding.embed_texts.call_count == 1

    store.document_hash.return_value = items[0][0].content_hash
    updated = LoadedDocument(**{**doc.__dict__, "content": "# Service\nA changed treatment."})
    assert ingest_document(updated, store, embedding, config, "model")
    assert store.replace_document.call_count == 2
    assert store.replace_document.call_args.args[1][0][0].chunk_id == first_id


def test_pgvector_search_params_include_filters_and_both_vectors() -> None:
    from chatbot.knowledge.pgvector_store import PgVectorStore

    store = PgVectorStore("postgresql://unused", 3, MagicMock())
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = []
    store._connect = MagicMock(return_value=connection)

    assert store.search([0.1, 0.2, 0.3], 4, {"shop_id": 2, "language": "en"}) == []
    statement, params = cursor.execute.call_args.args
    assert statement.count("%s") == len(params) == 5
    assert params[1:3] == [2, "en"]
    assert params[-1] == 4
    assert "shop_id = %s OR shop_id IS NULL" in statement
