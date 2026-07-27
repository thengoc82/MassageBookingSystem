"""Tests for the offline indexing command."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from chatbot.scripts.index_knowledge_base import cli
from typer.testing import CliRunner


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    """Mock SentenceTransformerEmbeddingService."""
    return MagicMock()


@pytest.fixture
def mock_vector_store() -> MagicMock:
    """Mock PgVectorStore."""
    store = MagicMock()
    store.clear = MagicMock()
    store.add_chunks = MagicMock()
    store.close = MagicMock()
    return store


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_index_command(
    runner: CliRunner, mock_embedding_service: MagicMock, mock_vector_store: MagicMock
) -> None:
    """Test that index command processes documents and writes them to the store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "doc.md").write_text(
            """---
title: Test FAQ
---

# Heading

Some content here.
"""
        )

        with (
            patch(
                "chatbot.scripts.index_knowledge_base.SentenceTransformerEmbeddingService",
                return_value=mock_embedding_service,
            ),
            patch(
                "chatbot.scripts.index_knowledge_base.PgVectorStore",
                return_value=mock_vector_store,
            ),
        ):
            mock_embedding_service.embed_texts.return_value = np.array([[0.1] * 384], dtype=float)
            result = runner.invoke(cli, ["--root-dir", str(root)])

    assert result.exit_code == 0, result.output
    mock_vector_store.clear.assert_called_once()
    mock_vector_store.add_chunks.assert_called_once()
    mock_vector_store.close.assert_called_once()


def test_index_command_empty_dir(
    runner: CliRunner, mock_embedding_service: MagicMock, mock_vector_store: MagicMock
) -> None:
    """Test index command with empty directory exits cleanly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with (
            patch(
                "chatbot.scripts.index_knowledge_base.SentenceTransformerEmbeddingService",
                return_value=mock_embedding_service,
            ),
            patch(
                "chatbot.scripts.index_knowledge_base.PgVectorStore",
                return_value=mock_vector_store,
            ),
        ):
            result = runner.invoke(cli, ["--root-dir", tmpdir])

    assert result.exit_code == 0, result.output
    mock_vector_store.clear.assert_not_called()
    mock_vector_store.add_chunks.assert_not_called()
    mock_vector_store.close.assert_called_once()
