"""Markdown document loader.

Recursively discovers Markdown files under a root directory and extracts
structured metadata (title, headings) for each document.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml


@dataclass
class LoadedDocument:
    """A single Markdown document loaded from disk."""

    source_file: str
    title: str
    content: str
    headings: list[str]
    last_updated: datetime
    document_id: str = ""
    category: str | None = None
    shop_id: int | None = None
    language: str = "en"
    source: str = "file"
    active: bool = True


def _extract_title(path: Path, fm_data: dict, content: str) -> str:
    """Extract title from frontmatter, first H1, or filename."""
    title = fm_data.get("title")
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
    raw = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    fm: dict = {}
    content = raw
    if raw.startswith("---\n"):
        parts = raw.split("\n---\n", 1)
        if len(parts) == 2:
            fm = yaml.safe_load(parts[0][4:]) or {}
            if not isinstance(fm, dict):
                raise ValueError(f"Invalid frontmatter in {path}")
            content = parts[1]
    title = _extract_title(path, fm, content)
    headings = _extract_headings(content)
    stat = path.stat()
    last_updated = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    return LoadedDocument(
        source_file=str(path.absolute()),
        title=title,
        content=content,
        headings=headings,
        last_updated=last_updated,
        document_id=str(fm.get("document_id") or path.absolute()),
        category=str(fm["category"]) if fm.get("category") else None,
        shop_id=int(fm["shop_id"]) if fm.get("shop_id") is not None else None,
        language=str(fm.get("language") or "en"),
        source=str(fm.get("source") or "file"),
        active=fm.get("active", True) is not False,
    )


def discover_markdown_files(root: Path) -> list[Path]:
    """Recursively discover all Markdown files under a root directory."""
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.md") if p.is_file())


def load_documents(root: Path) -> list[LoadedDocument]:
    """Load all Markdown documents under a root directory."""
    return [load_document(p) for p in discover_markdown_files(root)]
