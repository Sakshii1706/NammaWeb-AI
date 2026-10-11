"""
NammaWeb Reach - RAG Retrieval Evaluation

Evaluates retrieval quality without calling the LLM.
This keeps the evaluation fast and isolates the retriever.

Metrics:
- retrieved pages
- expected page hit
- retrieval latency
- embedding latency
- FAISS latency

Run from C:\\NammaWeb:
    .\\venv\\Scripts\\python.exe scripts\\evaluate_rag.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_PATH))

from reach.ai.rag.embedding_service import EmbeddingService
from reach.ai.rag.faiss_store import FAISSVectorStore
from reach.ai.rag.retriever import Retriever


FAISS_PATH = PROJECT_ROOT / "data" / "faiss_index"
TOP_K = 4


EVALUATION_SET = [
    {
        "id": "Q1",
        "question": "What is social science?",
        "expected_pages": {1},
    },
    {
        "id": "Q2",
        "question": "What are the four core disciplines of Social Science in Grades 9–10?",
        "expected_pages": {4},
    },
    {
        "id": "Q3",
        "question": "What does Geography study?",
        "expected_pages": {5},
    },
    {
        "id": "Q4",
        "question": "What does Political Science study?",
        "expected_pages": {9},
    },
    {
        "id": "Q5",
        "question": "What does Economics study?",
        "expected_pages": {10},
    },
    {
        "id": "Q6",
        "question": "Why is Social Science important for the future?",
        "expected_pages": {11},
    },
]


def build_retriever() -> Retriever:
    embedding_service = EmbeddingService()

    vector_store = FAISSVectorStore(
        index_path=FAISS_PATH,
        embedding_service=embedding_service,
    )

    if not vector_store.exists:
        raise FileNotFoundError(
            f"FAISS index not found at: {FAISS_PATH}"
        )

    vector_store.load()

    return Retriever(
        vector_store=vector_store,
        default_top_k=TOP_K,
    )


def main() -> None:
    print()
    print("=" * 72)
    print("NAMMAWEB AI - RAG RETRIEVAL EVALUATION")
    print("=" * 72)
    print(f"FAISS path : {FAISS_PATH}")
    print(f"Top-K      : {TOP_K}")
    print(f"Questions  : {len(EVALUATION_SET)}")
    print()

    retriever = build_retriever()

    results = []
    total_start = time.perf_counter()

    for item in EVALUATION_SET:
        start = time.perf_counter()

        retrieved = retriever.retrieve(
            query=item["question"],
            top_k=TOP_K,
        )

        elapsed = time.perf_counter() - start

        pages = [
            result.page_number
            for result in retrieved
            if result.page_number is not None
        ]

        expected_pages = item["expected_pages"]

        hit = bool(expected_pages.intersection(pages))

        results.append(
            {
                "id": item["id"],
                "question": item["question"],
                "expected": sorted(expected_pages),
                "retrieved": pages,
                "hit": hit,
                "latency": elapsed,
            }
        )

        status = "PASS" if hit else "MISS"

        print(
            f"{item['id']} | {status:4} | "
            f"expected={sorted(expected_pages)} | "
            f"retrieved={pages} | "
            f"{elapsed:.3f}s"
        )

    total_time = time.perf_counter() - total_start

    hits = sum(1 for result in results if result["hit"])
    total = len(results)
    hit_rate = (hits / total) * 100 if total else 0.0
    avg_latency = (
        sum(result["latency"] for result in results) / total
        if total
        else 0.0
    )

    print()
    print("-" * 72)
    print(f"Retrieval hits : {hits}/{total}")
    print(f"Hit rate       : {hit_rate:.1f}%")
    print(f"Average query  : {avg_latency:.3f}s")
    print(f"Evaluation     : {total_time:.3f}s")
    print("-" * 72)

    if hits == total:
        print("RESULT: RETRIEVAL EVALUATION PASSED")
    else:
        print("RESULT: RETRIEVAL NEEDS INVESTIGATION")

    print("=" * 72)
    print()


if __name__ == "__main__":
    main()
