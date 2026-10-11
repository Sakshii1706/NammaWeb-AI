"""
NammaWeb Reach - RAG Service Smoke Test

Validates the complete standalone RAG pipeline.
"""

import sys
from pathlib import Path


# Allow imports from src/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_PATH))


from reach.ai.rag.embedding_service import EmbeddingService
from reach.ai.rag.faiss_store import FAISSVectorStore
from reach.ai.rag.retriever import Retriever
from reach.ai.rag.context_builder import ContextBuilder
from reach.ai.rag.llm_generator import LLMGenerator
from reach.ai.rag.rag_service import RAGService


def build_rag_service() -> RAGService:
    """
    Construct the complete RAG pipeline.
    """

    embeddings = EmbeddingService()

    vector_store = FAISSVectorStore(
        index_path=PROJECT_ROOT / "data" / "faiss_index",
        embedding_service=embeddings,
    )

    if not vector_store.exists:
        raise FileNotFoundError(
            "FAISS index was not found."
        )

    vector_store.load()

    retriever = Retriever(
        vector_store=vector_store,
        default_top_k=4,
    )

    context_builder = ContextBuilder(
        max_sources=4,
        max_characters_per_source=4000,
    )

    llm_generator = LLMGenerator(
        model="llama3.2:3b",
        temperature=0,
        num_predict=192,
        keep_alive="24h",
    )

    return RAGService(
        retriever=retriever,
        context_builder=context_builder,
        llm_generator=llm_generator,
    )


def main() -> None:

    query = "What is social science?"

    print()
    print("=" * 60)
    print("NAMMAWEB RAG SERVICE TEST")
    print("=" * 60)
    print()
    print(f"Query: {query}")
    print()

    rag = build_rag_service()

    result = rag.ask(query)

    print()
    print("=" * 60)
    print("ANSWER")
    print("=" * 60)
    print(result.answer)
    print()

    print("=" * 60)
    print("RETRIEVAL")
    print("=" * 60)

    print(f"Sources: {result.source_count}")
    print(f"Pages: {result.pages}")

    print()

    for index, source in enumerate(
        result.sources,
        start=1,
    ):
        print(
            f"Source {index}: "
            f"Page {source.page_number}, "
            f"Score {source.score:.4f}"
        )

    print()

    print("=" * 60)
    print("PERFORMANCE")
    print("=" * 60)

    print(
        f"Retrieval: "
        f"{result.retrieval_time:.3f}s"
    )

    print(
        f"Generation: "
        f"{result.generation_time:.3f}s"
    )

    print(
        f"Total: "
        f"{result.total_time:.3f}s"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()
