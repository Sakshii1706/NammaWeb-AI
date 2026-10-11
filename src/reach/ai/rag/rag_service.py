from __future__ import annotations

from dataclasses import dataclass
import time

from .context_builder import ContextBuilder
from .llm_generator import LLMGenerator
from .retriever import RetrievedDocument, Retriever


@dataclass(frozen=True)
class RAGResponse:
    answer: str
    sources: list[RetrievedDocument]
    pages: list[int]
    source_count: int
    retrieval_time: float
    generation_time: float
    total_time: float


class RAGService:
    def __init__(
        self,
        retriever: Retriever,
        context_builder: ContextBuilder,
        llm_generator: LLMGenerator,
    ) -> None:
        self.retriever = retriever
        self.context_builder = context_builder
        self.llm_generator = llm_generator

    def build_prompt(self, context: str, query: str) -> str:
        return f"""
You are NammaWeb AI, a document question-answering assistant.

Answer the user's question using ONLY the supplied document context.

If the answer is not available in the context, clearly say:
"The information was not found in the document."

Do not use outside knowledge.

Be concise, professional and accurate.

For definition or explanatory questions, give the core definition
and the most important supporting points available in the supplied
context. Prefer 2–4 concise sentences rather than an overly short
one-sentence answer.

Preserve important details from the context. Do not omit the main
subject, relationships, categories, or supporting concepts needed to
answer the question accurately.

Always mention the relevant page number when possible.
Only mention page numbers that are supported by the supplied context.
Do not invent page numbers.

DOCUMENT CONTEXT:
{context}

USER QUESTION:
{query}

ANSWER:
""".strip()

    def ask(
        self,
        query: str,
        top_k: int | None = None,
    ) -> RAGResponse:
        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")

        total_start = time.perf_counter()

        retrieval_start = time.perf_counter()

        sources = self.retriever.retrieve(
            query=query,
            top_k=top_k,
        )

        context_result = self.context_builder.build(sources)

        retrieval_time = (
            time.perf_counter() - retrieval_start
        )

        prompt = self.build_prompt(
            context=context_result.context,
            query=query,
        )

        print(f"[PERFORMANCE] Context characters: {len(context_result.context)}")
        print(f"[PERFORMANCE] Prompt characters: {len(prompt)}")
        print(f"[PERFORMANCE] Query characters: {len(query)}")
        generation_start = time.perf_counter()

        answer = self.llm_generator.generate(prompt)

        generation_time = (
            time.perf_counter() - generation_start
        )

        total_time = (
            time.perf_counter() - total_start
        )

        print()
        print("========== RAG PERFORMANCE ==========")
        print(
            f"Retrieved sources: {len(sources)}"
        )
        print(
            f"Pages: {context_result.pages}"
        )
        print(
            f"Retrieval: {retrieval_time:.3f}s"
        )
        print(
            f"Generation: {generation_time:.3f}s"
        )
        print(
            f"Total: {total_time:.3f}s"
        )
        print("=====================================")

        return RAGResponse(
            answer=answer,
            sources=sources,
            pages=context_result.pages,
            source_count=context_result.source_count,
            retrieval_time=retrieval_time,
            generation_time=generation_time,
            total_time=total_time,
        )

