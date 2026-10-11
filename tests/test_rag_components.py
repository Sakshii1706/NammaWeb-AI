"""
NammaWeb AI - Fast RAG Component Tests

These tests do not load Hugging Face models or Ollama.
They validate deterministic behavior in the RAG building blocks.

Run from the project root:
    .\venv\Scripts\python.exe .\tests\test_rag_components.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from langchain_core.documents import Document

from reach.ai.rag.context_builder import ContextBuilder
from reach.ai.rag.rag_service import RAGService
from reach.ai.rag.retriever import RetrievedDocument


class DummyRetriever:
    def retrieve(self, query: str, top_k: int | None = None):
        return []


class DummyContextBuilder:
    def build(self, documents):
        raise AssertionError("build() should not be called in prompt-only tests")


class DummyLLM:
    pass


class TestContextBuilder(unittest.TestCase):
    def test_empty_context(self):
        builder = ContextBuilder()
        result = builder.build([])

        self.assertEqual(result.context, "")
        self.assertEqual(result.source_count, 0)
        self.assertEqual(result.pages, [])

    def test_builds_sources_and_one_based_pages(self):
        builder = ContextBuilder(
            max_sources=2,
            max_characters_per_source=100,
        )

        documents = [
            RetrievedDocument(
                document=Document(
                    page_content="First source content",
                    metadata={"page": 0},
                ),
                score=0.1,
                page=0,
                page_number=1,
                metadata={"page": 0},
            ),
            RetrievedDocument(
                document=Document(
                    page_content="Second source content",
                    metadata={"page": 3},
                ),
                score=0.2,
                page=3,
                page_number=4,
                metadata={"page": 3},
            ),
        ]

        result = builder.build(documents)

        self.assertEqual(result.source_count, 2)
        self.assertEqual(result.pages, [1, 4])
        self.assertIn("Source 1", result.context)
        self.assertIn("Page: 1", result.context)
        self.assertIn("Source 2", result.context)
        self.assertIn("Page: 4", result.context)


class TestRAGPrompt(unittest.TestCase):
    def setUp(self):
        self.service = RAGService(
            retriever=DummyRetriever(),
            context_builder=DummyContextBuilder(),
            llm_generator=DummyLLM(),
        )

    def test_prompt_contains_grounding_instruction(self):
        prompt = self.service.build_prompt(
            context="Page: 1\nContent: Social Science studies society.",
            query="What is social science?",
        )

        self.assertIn("ONLY the supplied document context", prompt)
        self.assertIn("Do not use outside knowledge", prompt)
        self.assertIn(
            "The information was not found in the document.",
            prompt,
        )

    def test_prompt_contains_completeness_instruction(self):
        prompt = self.service.build_prompt(
            context="Page: 5\nContent: Geography studies places and environment.",
            query="What does Geography study?",
        )

        self.assertIn("most important supporting points", prompt)
        self.assertIn("2–4 concise sentences", prompt)
        self.assertIn("Do not omit the main", prompt)

    def test_prompt_contains_question_and_context(self):
        prompt = self.service.build_prompt(
            context="Page: 5\nContent: Geography studies places.",
            query="What does Geography study?",
        )

        self.assertIn("Geography studies places", prompt)
        self.assertIn("What does Geography study?", prompt)


if __name__ == "__main__":
    unittest.main(verbosity=2)

