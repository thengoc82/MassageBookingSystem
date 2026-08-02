"""Markdown document loader.

Recursively discovers Markdown files under a root directory and extracts
structured metadata (title, headings) for each document.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from frontmatter import Frontmatter


@dataclass
class LoadedDocument:
    """A single Markdown document loaded from disk."""

    source_file: str
    title: str
    content: str
    headings: list[str]
    last_updated: datetime


def _extract_title(path: Path, fm_data: dict, content: str) -> str:
    """Extract title from frontmatter, first H1, or filename."""
    title = fm_data.get("title", "")
    if isinstance(title, str) and title.strip():
        return title.strip()

    for line in content.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()

    return path.stem


def _extract_headings(content: str) -> list[str]:
    """Return all markdown headings in order."""
    headings: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                headings.append(heading)
    return headings


def load_document(path: Path) -> LoadedDocument:
    """Load a single Markdown file from disk."""
    post_data = Frontmatter.read_file(path)
    metadata = post_data["attributes"]
    content = post_data["body"]

    title = _extract_title(path, metadata, content)
    headings = _extract_headings(content)
    stat = path.stat()
    last_updated = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    return LoadedDocument(
        source_file=str(path),
        title=title,
        content=content,
        headings=headings,
        last_updated=last_updated,
    )


def discover_markdown_files(root: Path) -> list[Path]:
    """Recursively discover all Markdown files under a root directory."""
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.md") if p.is_file())


def load_documents(root: Path) -> list[LoadedDocument]:
    """Load all Markdown documents under a root directory."""
    return [load_document(p) for p in discover_markdown_files(root)]
