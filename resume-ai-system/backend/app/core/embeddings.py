"""
Embeddings — used by the Similarity Score module.

Two providers:
  - "local"  → sentence-transformers/all-MiniLM-L6-v2 (default, free, fast, ~80MB)
  - "openai" → text-embedding-3-small (1536d, paid)

The local model is loaded lazily on first use because sentence-transformers
takes ~3s to import and we don't want to pay that cost at startup.
"""
from __future__ import annotations

import logging
from typing import Sequence

import numpy as np

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingProvider:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._local_model = None
        self._openai = None

    async def embed(self, texts: Sequence[str]) -> np.ndarray:
        """Return an (N, D) float32 numpy array of L2-normalized embeddings."""
        if not texts:
            return np.zeros((0, 384), dtype=np.float32)

        if self.settings.embedding_model == "openai":
            return await self._embed_openai(texts)
        return self._embed_local(texts)

    def _embed_local(self, texts: Sequence[str]) -> np.ndarray:
        if self._local_model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading local embedding model: %s", self.settings.local_embedding_model_name)
            self._local_model = SentenceTransformer(self.settings.local_embedding_model_name)
        embs = self._local_model.encode(
            list(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return embs.astype(np.float32)

    async def _embed_openai(self, texts: Sequence[str]) -> np.ndarray:
        if self._openai is None:
            from openai import AsyncOpenAI

            self._openai = AsyncOpenAI(api_key=self.settings.openai_api_key)
        resp = await self._openai.embeddings.create(
            model=self.settings.openai_embedding_model,
            input=list(texts),
        )
        arr = np.array([d.embedding for d in resp.data], dtype=np.float32)
        # L2-normalize so cosine == dot product
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return arr / norms


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cosine similarity matrix between rows of a (M,D) and b (N,D).

    Assumes both are L2-normalized — embed() guarantees this.
    Returns (M, N).
    """
    if a.size == 0 or b.size == 0:
        return np.zeros((a.shape[0], b.shape[0]), dtype=np.float32)
    return a @ b.T


_provider: EmbeddingProvider | None = None


def get_embeddings() -> EmbeddingProvider:
    global _provider
    if _provider is None:
        _provider = EmbeddingProvider()
    return _provider
