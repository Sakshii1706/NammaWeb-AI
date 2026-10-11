"""
NammaWeb Reach - PDF Document Loader

Small local PDF loader using pypdf and LangChain core Documents.
This avoids the deprecated langchain-community PyPDFLoader import.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from pypdf import PdfReader


class PDFDocumentLoader:
    """Extract one LangChain Document per PDF page."""

    def __init__(self, pdf_path: str | Path) -> None:
        self.pdf_path = Path(pdf_path)

    def load(self) -> list[Document]:
        if not self.pdf_path.exists():
            raise FileNotFoundError(
                f"PDF not found: {self.pdf_path}"
            )

        reader = PdfReader(str(self.pdf_path))
        total_pages = len(reader.pages)
        documents: list[Document] = []

        for page_index, page in enumerate(reader.pages):
            text = page.extract_text() or ""

            documents.append(
                Document(
                    page_content=text,
                    metadata={
                        "source": str(self.pdf_path),
                        "page": page_index,
                        "page_number": page_index + 1,
                        "page_label": str(page_index + 1),
                        "total_pages": total_pages,
                    },
                )
            )

        return documents
