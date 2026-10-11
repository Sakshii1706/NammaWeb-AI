"""
NammaWeb Reach - RAG Generation Evaluation

Evaluates end-to-end grounded generation:
    question -> retrieval -> context -> Llama -> answer

Checks:
- expected document page retrieved
- expected answer terms
- grounded refusal for an out-of-document question
- retrieval/generation/total latency

This is a lightweight deterministic baseline, not a full semantic judge.

Run from C:\\NammaWeb:
    .\\venv\\Scripts\\python.exe .\\scripts\\evaluate_generation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from reach.ai.rag.embedding_service import EmbeddingService
from reach.ai.rag.faiss_store import FAISSVectorStore
from reach.ai.rag.retriever import Retriever
from reach.ai.rag.context_builder import ContextBuilder
from reach.ai.rag.llm_generator import LLMGenerator
from reach.ai.rag.rag_service import RAGService


FAISS_PATH = PROJECT_ROOT / "data" / "faiss_index"
TOP_K = 4

REFUSAL = "the information was not found in the document"

EVALUATION_SET = [
    {
        "id": "G1",
        "question": "What is social science?",
        "expected_pages": {1},
        "required_groups": [
            {"social science"},
            {"systematic", "study"},
            {"human society", "society"},
        ],
        "expect_refusal": False,
    },
    {
        "id": "G2",
        "question": "What are the four core disciplines of Social Science in Grades 9–10?",
        "expected_pages": {4},
        "required_groups": [
            {"geography"},
            {"history"},
            {"political science"},
            {"economics"},
        ],
        "expect_refusal": False,
    },
    {
        "id": "G3",
        "question": "What does Geography study?",
        "expected_pages": {5},
        "required_groups": [
            {"geography"},
            {"location", "distribution", "places"},
            {"environment", "surroundings"},
        ],
        "expect_refusal": False,
    },
    {
        "id": "G4",
        "question": "What does Political Science study?",
        "expected_pages": {9},
        "required_groups": [
            {"political science"},
            {"governance"},
            {"power", "government", "institutions"},
        ],
        "expect_refusal": False,
    },
    {
        "id": "G5",
        "question": "What does Economics study?",
        "expected_pages": {10},
        "required_groups": [
            {"economics"},
            {"resources"},
            {"goods", "services", "produced", "distributed"},
        ],
        "expect_refusal": False,
    },
    {
        "id": "G6",
        "question": "What is the capital of Japan?",
        "expected_pages": set(),
        "required_groups": [],
        "expect_refusal": True,
    },
]


def build_rag_service() -> RAGService:
    embeddings = EmbeddingService()

    vector_store = FAISSVectorStore(
        index_path=FAISS_PATH,
        embedding_service=embeddings,
    )

    if not vector_store.exists:
        raise FileNotFoundError(
            f"FAISS index not found at: {FAISS_PATH}"
        )

    vector_store.load()

    retriever = Retriever(
        vector_store=vector_store,
        default_top_k=TOP_K,
    )

    context_builder = ContextBuilder(
        max_sources=TOP_K,
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


def group_matches(answer: str, group: set[str]) -> bool:
    normalized = answer.lower()
    return any(term.lower() in normalized for term in group)


def main() -> None:
    print()
    print("=" * 76)
    print("NAMMAWEB AI - RAG GENERATION EVALUATION")
    print("=" * 76)
    print(f"FAISS path : {FAISS_PATH}")
    print(f"Top-K      : {TOP_K}")
    print(f"Questions  : {len(EVALUATION_SET)}")
    print()

    rag = build_rag_service()

    passed = 0

    for item in EVALUATION_SET:
        print()
        print("-" * 76)
        print(f"{item['id']}: {item['question']}")
        print("-" * 76)

        result = rag.ask(
            query=item["question"],
            top_k=TOP_K,
        )

        retrieved_pages = [
            source.page_number
            for source in result.sources
            if source.page_number is not None
        ]

        answer = result.answer.strip()
        answer_lower = answer.lower()

        if item["expect_refusal"]:
            page_ok = True
            content_ok = REFUSAL in answer_lower
            test_description = "grounded refusal"
        else:
            page_ok = bool(
                item["expected_pages"].intersection(
                    retrieved_pages
                )
            )

            groups = item["required_groups"]
            matched_groups = [
                group_matches(answer, group)
                for group in groups
            ]
            content_ok = all(matched_groups)
            test_description = (
                f"term groups {sum(matched_groups)}/{len(groups)}"
            )

        overall = page_ok and content_ok

        if overall:
            passed += 1

        print(f"Retrieved pages : {retrieved_pages}")
        print(f"Page check      : {'PASS' if page_ok else 'FAIL'}")
        print(
            f"Content check   : "
            f"{'PASS' if content_ok else 'FAIL'} "
            f"({test_description})"
        )
        print(f"Overall         : {'PASS' if overall else 'FAIL'}")
        print(
            f"Timing          : retrieval={result.retrieval_time:.3f}s | "
            f"generation={result.generation_time:.3f}s | "
            f"total={result.total_time:.3f}s"
        )
        print()
        print("ANSWER:")
        print(answer)

    total = len(EVALUATION_SET)
    rate = (passed / total) * 100 if total else 0.0

    print()
    print("=" * 76)
    print("GENERATION EVALUATION SUMMARY")
    print("=" * 76)
    print(f"Passed    : {passed}/{total}")
    print(f"Pass rate : {rate:.1f}%")

    if passed == total:
        print("RESULT    : GENERATION EVALUATION PASSED")
    else:
        print("RESULT    : REVIEW FAILED CASES ABOVE")

    print("=" * 76)
    print()


if __name__ == "__main__":
    main()

