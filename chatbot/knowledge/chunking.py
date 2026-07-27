"""Recursive markdown chunking.

Splits documents into overlapping chunks sized by configurable limits.
Heading context is preserved by prepending the current heading to each chunk.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from langchain_text_splitters import RecursiveCharacterTextSplitter

from chatbot.knowledge.document_loader import LoadedDocument


@dataclass
class TextChunk:
    """A single chunk of text with heading context."""

    chunk_id: str
    source_file: str
    title: str
    heading: str
    content: str
    last_updated: datetime


@dataclass
class ChunkingConfig:
    """Chunking configuration."""

    chunk_size: int = 500
    chunk_overlap: int = 50


def _build_splitter(config: ChunkingConfig) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        length_function=len,
        is_separator_regex=False,
    )


def _slugify(text: str) -> str:
    """Create a stable, filename-safe slug from arbitrary text."""
    import re

    slug = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return slug or "chunk"


def chunk_document(
    document: LoadedDocument,
    config: ChunkingConfig,
    *,
    source_offset: int = 0,
) -> list[TextChunk]:
    """Split a loaded document into chunks with heading context.

    source_offset ensures globally unique chunk ids across multiple documents.
    """
    splitter = _build_splitter(config)
    lines = document.content.splitlines()
    chunks: list[TextChunk] = []

    sections: list[tuple[str, str]] = []
    current_heading = ""
    current_lines: list[str] = []
    for line in lines:
        if line.strip().startswith("#"):
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines)))
            current_heading = line.strip().lstrip("#").strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_heading, "\n".join(current_lines)))

    for heading, body in sections:
        if not body.strip():
            continue
        parts = splitter.split_text(body)
        for part in parts:
            context_heading = (
                heading
                or (document.headings[0] if document.headings else document.title)
            )
            chunk_id = f"{source_offset + len(chunks):05d}-{_slugify(document.title)}-{_slugify(context_heading)}"
            content = f"{context_heading}\n\n{part}" if context_heading else part
            chunks.append(
                TextChunk(
                    chunk_id=chunk_id,
                    source_file=document.source_file,
                    title=document.title,
                    heading=context_heading,
                    content=content,
                    last_updated=document.last_updated,
                )
            )
    return chunks
