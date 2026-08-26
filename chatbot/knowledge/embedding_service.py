"""Embedding service interface and implementation.

Uses sentence-transformers to generate embeddings.
The service is configurable and replaceable.
"""

from abc import ABC, abstractmethod
from typing import cast

import numpy as np


from sentence_transformers import SentenceTransformer
from openai import OpenAI


class EmbeddingService(ABC):
    """Abstract base class for embedding services."""

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Get the embedding dimension."""
        raise NotImplementedError

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        raise NotImplementedError


import logging

logger = logging.getLogger(__name__)

class OpenAIEmbeddingService(EmbeddingService):
    """Embedding service using OpenAI's API."""

    def __init__(self, api_key: str, model_name: str, embedding_dim: int) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model_name = model_name
        self._embedding_dim = embedding_dim

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        from sentence_transformers import SentenceTransformer

class SentenceTransformerEmbeddingService(EmbeddingService):
    """Embedding service using a local sentence-transformer model."""

    def __init__(self, model_name: str) -> None:
        self._model = SentenceTransformer(model_name)
        self._embedding_dim = self._model.get_sentence_embedding_dimension()

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return [embedding.tolist() for embedding in embeddings]


