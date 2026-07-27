"""Tests for document loader."""

import tempfile
from pathlib import Path

from chatbot.knowledge.document_loader import (
    discover_markdown_files,
    load_document,
)


def test_load_document() -> None:
    """Test loading a single Markdown file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("""---
title: Test Document
---

# Test Heading
This is a test document.
""")
        temp_path = Path(f.name)

    try:
        doc = load_document(temp_path)
        assert doc.source_file == str(temp_path)
        assert doc.title == "Test Document"
        assert "Test Heading" in doc.headings
        assert "This is a test document." in doc.content
    finally:
        temp_path.unlink(missing_ok=True)


def test_discover_markdown_files() -> None:
    """Test discovering Markdown files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "subdir").mkdir()
        (root / "file1.md").write_text("# File 1")
        (root / "file2.txt").write_text("Not markdown")
        (root / "subdir" / "file3.md").write_text("# File 3")

        files = discover_markdown_files(root)
        paths = [Path(p) for p in files]

        assert len(paths) == 2
        assert all(p.suffix == ".md" for p in paths)
        assert any(p.name == "file1.md" for p in paths)
        assert any(p.name == "file3.md" for p in paths)


def test_empty_root() -> None:
    """Test with empty root directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        files = discover_markdown_files(Path(tmpdir))
        assert files == []
