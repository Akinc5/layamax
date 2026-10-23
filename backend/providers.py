"""
Abstract provider interfaces.

Every AI / data component is behind an interface so it can be swapped
(Laya ↔ another classifier, OpenAI ↔ Gemini, Qdrant ↔ pgvector, etc.).
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import numpy as np

from schemas import ClassificationResult, RawPost


# ═══════════════════════════════════════════════════════════════════════════
# ── Stream provider ──────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════
class StreamProvider(ABC):
    """Yields raw posts from an authorised data source (X API, mock, etc.)."""

    @abstractmethod
    async def stream(self) -> AsyncIterator[RawPost]:
        """Continuously yield incoming posts."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Gracefully stop the stream."""
        ...


# ═══════════════════════════════════════════════════════════════════════════
# ── Classifier (Laya integration point) ──────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════
class LayaClassifier(ABC):
    """Classify a post into category, sentiment, importance, etc."""

    @abstractmethod
    async def classify(self, text: str, metadata: Dict[str, Any] | None = None) -> ClassificationResult:
        ...

    @abstractmethod
    async def get_categories(self) -> List[str]:
        """Return the current list of classification categories."""
        ...

    @abstractmethod
    async def set_categories(self, categories: List[str]) -> None:
        """Update the classification categories at runtime."""
        ...


# ═══════════════════════════════════════════════════════════════════════════
# ── Embedding provider ───────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════
class EmbeddingProvider(ABC):
    """Generate dense vector embeddings for text."""

    @abstractmethod
    async def embed(self, text: str) -> np.ndarray:
        ...

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...


# ═══════════════════════════════════════════════════════════════════════════
# ── Vector store ─────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════
class VectorStore(ABC):
    """Store and search over embeddings."""

    @abstractmethod
    async def add(self, embedding_id: str, vector: np.ndarray, metadata: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    async def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Return list of (embedding_id, score, metadata)."""
        ...

    @abstractmethod
    async def delete(self, embedding_id: str) -> None:
        ...

    @abstractmethod
    async def count(self) -> int:
        ...


# ═══════════════════════════════════════════════════════════════════════════
# ── LLM provider ────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════
class LLMProvider(ABC):
    """Generate text given a prompt + optional context."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        context: str = "",
        system_prompt: str = "",
        max_tokens: int = 1024,
    ) -> str:
        ...

    async def generate_stream(
        self,
        prompt: str,
        context: str = "",
        system_prompt: str = "",
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        """Stream generated text chunks/tokens."""
        full_text = await self.generate(prompt, context, system_prompt, max_tokens)
        words = full_text.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.015)

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...
