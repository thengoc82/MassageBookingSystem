"""Embedding service interface and implementation.

Uses sentence-transformers to generate embeddings.
The service is configurable and replaceable.
"""

from abc import ABC, abstractmethod
from typing import cast

import numpy as np


class EmbeddingService(ABC):
    """Abstract base class for embedding services."""

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings for a list of texts."""
        raise NotImplementedError


class SentenceTransformerEmbeddingService(EmbeddingService):
    """Embedding service using sentence-transformers."""

    def __init__(self, model_name: str, embedding_dim: int) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "SentenceTransformer is not installed. "
                "Please run `pip install sentence-transformers`."
            ) from e

        self._model = SentenceTransformer(model_name)
        self._embedding_dim = embedding_dim

    def embed_texts(self, texts: list[str]) -> list[np.ndarray]:
        """Embed a list of texts using the configured model."""
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return cast(list[np.ndarray], embeddings)
