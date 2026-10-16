"""
NammaWeb Reach - Context Builder

Converts retrieved documents into controlled, source-aware
context for the language model.
"""

from __future__ import annotations

from dataclasses import dataclass

from .retriever import RetrievedDocument


@dataclass(frozen=True)
class ContextResult:
    """
    Final context prepared for the LLM.
    """

    context: str
    source_count: int
    pages: list[int]


class ContextBuilder:
    """
    Builds deterministic, source-aware LLM context.
    """

    def __init__(
        self,
        max_sources: int = 4,
        max_characters_per_source: int = 4000,
    ) -> None:

        if max_sources <= 0:
            raise ValueError(
                "max_sources must be greater than zero."
            )

        if max_characters_per_source <= 0:
            raise ValueError(
                "max_characters_per_source must be greater than zero."
            )

        self.max_sources = max_sources
        self.max_characters_per_source = (
            max_characters_per_source
        )

    def build(
        self,
        documents: list[RetrievedDocument],
    ) -> ContextResult:
        """
        Convert retrieved documents into structured context.
        """

        selected = documents[:self.max_sources]

        if not selected:
            return ContextResult(
                context="",
                source_count=0,
                pages=[],
            )

        sections: list[str] = []
        pages: list[int] = []

        for index, result in enumerate(selected, start=1):

            text = result.document.page_content.strip()

            if not text:
                continue

            text = text[:self.max_characters_per_source]

            page_number = result.page_number

            if page_number is not None:
                page_label = str(page_number)

                if page_number not in pages:
                    pages.append(page_number)

            else:
                page_label = "Unknown"

            sections.append(
                "\n".join(
                    [
                        f"--- Source {index} ---",
                        f"Page: {page_label}",
                        "Content:",
                        text,
                    ]
                )
            )

        return ContextResult(
            context="\n\n".join(sections),
            source_count=len(sections),
            pages=pages,
        )

    def build_string(
        self,
        documents: list[RetrievedDocument],
    ) -> str:
        """
        Convenience method returning only the context string.
        """

        return self.build(documents).context