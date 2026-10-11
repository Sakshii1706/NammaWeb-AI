"""
NammaWeb Reach - Retriever

Retrieval policy layer between the RAG service and the vector store.

Responsibilities:
    - Accept user queries
    - Apply top-k retrieval policy
    - Preserve document metadata
    - Return structured retrieval results
    - Keep vector-store implementation details out of the application layer
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document

from .faiss_store import FAISSVectorStore


@dataclass(frozen=True)
class RetrievedDocument:
    """
    One retrieved document/chunk.

    score:
        FAISS distance/score returned by the vector store.

    page:
        Original zero-based page value stored in the document metadata.

    page_number:
        Human-readable one-based page number.

    metadata:
        Original document metadata.
    """

    document: Document
    score: float
    page: int | None
    page_number: int | None
    metadata: dict[str, Any]


class Retriever:
    """
    Retrieval policy layer.

    The application interacts with this class instead of directly
    interacting with FAISS.
    """

    def __init__(
        self,
        vector_store: FAISSVectorStore,
        default_top_k: int = 4,
    ) -> None:
        if default_top_k <= 0:
            raise ValueError(
                "default_top_k must be greater than zero."
            )

        self.vector_store = vector_store
        self.default_top_k = default_top_k

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[RetrievedDocument]:
        """
        Retrieve the most relevant document chunks.

        Args:
            query: User's natural-language question.
            top_k: Number of chunks to retrieve. Uses the configured
                   default when omitted.

        Returns:
            Structured retrieval results.
        """

        if not query or not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        k = top_k if top_k is not None else self.default_top_k

        if k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        results = self.vector_store.similarity_search(
            query=query,
            k=k,
        )

        retrieved: list[RetrievedDocument] = []

        for document, score in results:
            raw_page = document.metadata.get("page")

            page: int | None = None

            if isinstance(raw_page, int):
                page = raw_page

            elif isinstance(raw_page, str):
                try:
                    page = int(raw_page)
                except ValueError:
                    page = None

            page_number = (
                page + 1
                if page is not None
                else None
            )

            retrieved.append(
                RetrievedDocument(
                    document=document,
                    score=float(score),
                    page=page,
                    page_number=page_number,
                    metadata=dict(document.metadata),
                )
            )

        return retrieved

    def retrieve_documents(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[Document]:
        """
        Convenience method returning only LangChain Documents.
        """

        return [
            result.document
            for result in self.retrieve(
                query=query,
                top_k=top_k,
            )
        ]

    def get_default_top_k(self) -> int:
        """
        Return the configured default retrieval count.
        """

        return self.default_top_k