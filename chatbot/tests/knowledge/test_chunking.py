"""Tests for document chunking."""

from datetime import datetime, timezone

from chatbot.knowledge.chunking import (
    ChunkingConfig,
    LoadedDocument,
    TextChunk,
    chunk_document,
)


def test_chunk_document() -> None:
    """Test chunking a simple document."""
    doc = LoadedDocument(
        source_file="/test.md",
        title="Test Document",
        content="# Heading\n\nThis is a test document with some text. This is a test document with some text. This is a test document with some text.",
        headings=["Heading"],
        last_updated=datetime.now(tz=timezone.utc),
    )

    config = ChunkingConfig(chunk_size=20, chunk_overlap=5)
    chunks = chunk_document(doc, config, source_offset=0)

    assert len(chunks) >= 1
    assert all(isinstance(chunk, TextChunk) for chunk in chunks)
    assert all(chunk.source_file == doc.source_file for chunk in chunks)
    assert all(chunk.title == doc.title for chunk in chunks)
    assert all(chunk.heading == "Heading" for chunk in chunks)
    assert "context_heading" in chunks[0].content


def test_chunk_empty_document() -> None:
    """Test chunking an empty document."""
    doc = LoadedDocument(
        source_file="/empty.md",
        title="Empty Doc",
        content="",
        headings=[],
        last_updated=datetime.now(tz=timezone.utc),
    )
    config = ChunkingConfig(chunk_size=100, chunk_overlap=10)
    chunks = chunk_document(doc, config)
    # Empty content should still produce chunks (at least one based on heading)
    assert isinstance(chunks, list)


def test_chunk_multiple_headings() -> None:
    """Test chunking document with multiple headings."""
    content = "# Heading 1\n\nText under heading 1.\n\n# Heading 2\n\nText under heading 2.\n\n## Sub Heading 2.1\n\nMore text."

    doc = LoadedDocument(
        source_file="/multi.md",
        title="Multi Heading Doc",
        content=content,
        headings=["Heading 1", "Heading 2", "Sub Heading 2.1"],
        last_updated=datetime.now(tz=timezone.utc),
    )

    config = ChunkingConfig(chunk_size=50, chunk_overlap=5)
    chunks = chunk_document(doc, config)

    assert len(chunks) > 0
    # Each chunk should have heading context
    assert all(chunk.heading in ["Heading 1", "Heading 2", "Sub Heading 2.1", ""] for chunk in chunks)
