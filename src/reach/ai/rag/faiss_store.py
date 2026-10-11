"""
NammaWeb Reach - FAISS Vector Store

Encapsulates FAISS persistence and similarity search.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Sequence

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from .embedding_service import EmbeddingService


class FAISSVectorStore:
    def __init__(
        self,
        index_path: str | Path,
        embedding_service: EmbeddingService,
    ) -> None:
        self.index_path = Path(index_path)
        self.embedding_service = embedding_service
        self._store: FAISS | None = None

    @property
    def index_file(self) -> Path:
        return self.index_path / "index.faiss"

    @property
    def metadata_file(self) -> Path:
        return self.index_path / "index.pkl"

    @property
    def exists(self) -> bool:
        return (
            self.index_file.exists()
            and self.metadata_file.exists()
        )

    def load(self) -> int:
        if not self.exists:
            raise FileNotFoundError(
                f"FAISS index not found at: {self.index_path}"
            )

        start = time.perf_counter()

        # The adapter is an Embeddings object, but it does not load
        # MiniLM until an embedding method is actually called.
        self._store = FAISS.load_local(
            str(self.index_path),
            self.embedding_service.as_langchain_embeddings(),
            allow_dangerous_deserialization=True,
        )

        count = self.vector_count
        elapsed = time.perf_counter() - start
        print(f"[PERFORMANCE] FAISS load: {elapsed:.3f}s")
        print(f"[PERFORMANCE] Existing vectors: {count}")
        return count

    def build(
        self,
        documents: Sequence[Document],
    ) -> int:
        if not documents:
            raise ValueError(
                "Cannot build FAISS index from empty documents."
            )

        start = time.perf_counter()

        self._store = FAISS.from_documents(
            list(documents),
            self.embedding_service.embeddings,
        )

        self.index_path.mkdir(parents=True, exist_ok=True)
        self._store.save_local(str(self.index_path))

        elapsed = time.perf_counter() - start
        count = self.vector_count
        print(f"[PERFORMANCE] FAISS build: {elapsed:.3f}s")
        print(f"[PERFORMANCE] Created vectors: {count}")
        return count

    def similarity_search(
        self,
        query: str,
        k: int = 4,
    ) -> list[tuple[Document, float]]:
        if self._store is None:
            raise RuntimeError(
                "FAISS index is not loaded. "
                "Call load() or build() first."
            )
        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")
        if k <= 0:
            raise ValueError("k must be greater than zero.")

        start = time.perf_counter()
        query_embedding = self.embedding_service.embed_query(query)
        results = self._store.similarity_search_with_score_by_vector(
            query_embedding,
            k=k,
        )
        elapsed = time.perf_counter() - start
        print(f"[PERFORMANCE] FAISS search: {elapsed:.3f}s")
        return results

    @property
    def vector_count(self) -> int:
        if self._store is None:
            return 0
        return self._store.index.ntotal

    @property
    def is_loaded(self) -> bool:
        return self._store is not None
