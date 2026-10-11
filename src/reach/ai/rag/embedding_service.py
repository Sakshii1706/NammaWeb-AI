"""
NammaWeb Reach - Embedding Service

Lazy embedding model abstraction used by RAG and FAISS.
"""

from __future__ import annotations

import time
from typing import Sequence

from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings


class LazyEmbeddingAdapter(Embeddings):
    """
    LangChain-compatible lazy adapter.

    FAISS receives an Embeddings object, so LangChain does not emit the
    embedding_function warning. The actual Hugging Face model is still
    loaded only when embed_query() or embed_documents() is called.
    """

    def __init__(self, embedding_service: "EmbeddingService") -> None:
        self.embedding_service = embedding_service

    def embed_query(self, text: str) -> list[float]:
        return self.embedding_service.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embedding_service.embed_documents(texts)


class EmbeddingService:
    """Lazy-loaded embedding service."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        self.model_name = model_name
        self._embeddings: HuggingFaceEmbeddings | None = None

    @property
    def embeddings(self) -> HuggingFaceEmbeddings:
        if self._embeddings is None:
            start = time.perf_counter()
            self._embeddings = HuggingFaceEmbeddings(
                model_name=self.model_name
            )
            elapsed = time.perf_counter() - start
            print(
                f"[PERFORMANCE] Embedding model loading: "
                f"{elapsed:.3f}s"
            )
        return self._embeddings

    def embed_query(self, query: str) -> list[float]:
        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")
        return self.embeddings.embed_query(query)

    def embed_documents(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        if not texts:
            return []
        return self.embeddings.embed_documents(list(texts))

    def get_dimensions(self) -> int:
        vector = self.embed_query("dimension check")
        return len(vector)

    def get_model_name(self) -> str:
        return self.model_name

    def as_langchain_embeddings(self) -> LazyEmbeddingAdapter:
        """Return a LangChain Embeddings adapter without loading the model."""
        return LazyEmbeddingAdapter(self)
