from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from reach.db.document_repository import (
    ACTIVE_STATUS,
    ARCHIVED_STATUS,
    FAILED_STATUS,
    PROCESSING_STATUS,
    archive_active_documents,
    create_processing_document,
    get_active_document,
    get_document_by_checksum,
    get_document_by_id,
    get_knowledge_base_by_id,
    get_or_create_knowledge_base,
    list_documents,
    mark_document_failed,
    update_document_processing_result,
)
from reach.db.models import Document, KnowledgeBase


@dataclass(frozen=True)
class DocumentUpload:
    """Normalized information about an uploaded document."""

    filename: str
    file_path: Path
    checksum: str


class DocumentService:
    """Application service for workspace-scoped document lifecycle operations."""

    def __init__(
        self,
        session: Session,
        workspace_id: int,
    ):
        if workspace_id < 1:
            raise ValueError("workspace_id must be a positive integer.")

        self.session = session
        self.workspace_id = workspace_id

    def get_or_create_default_knowledge_base(self) -> KnowledgeBase:
        return get_or_create_knowledge_base(
            session=self.session,
            workspace_id=self.workspace_id,
        )

    def get_knowledge_base(
        self,
        knowledge_base_id: int,
    ) -> KnowledgeBase | None:
        return get_knowledge_base_by_id(
            session=self.session,
            workspace_id=self.workspace_id,
            knowledge_base_id=knowledge_base_id,
        )

    def get_document_by_id(
        self,
        document_id: int,
    ) -> Document | None:
        return get_document_by_id(
            session=self.session,
            workspace_id=self.workspace_id,
            document_id=document_id,
        )

    def get_active_document(
        self,
        knowledge_base_id: int,
    ) -> Document | None:
        return get_active_document(
            session=self.session,
            workspace_id=self.workspace_id,
            knowledge_base_id=knowledge_base_id,
        )

    def get_document_by_checksum(
        self,
        knowledge_base_id: int,
        checksum: str,
    ) -> Document | None:
        return get_document_by_checksum(
            session=self.session,
            workspace_id=self.workspace_id,
            knowledge_base_id=knowledge_base_id,
            checksum=checksum,
        )

    def list_documents(
        self,
        knowledge_base_id: int,
    ) -> list[Document]:
        return list_documents(
            session=self.session,
            workspace_id=self.workspace_id,
            knowledge_base_id=knowledge_base_id,
        )

    @staticmethod
    def calculate_checksum(file_path: Path) -> str:
        sha256 = hashlib.sha256()

        with file_path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                sha256.update(chunk)

        return sha256.hexdigest()

    def prepare_processing(
        self,
        knowledge_base_id: int,
        filename: str,
        file_path: Path,
        checksum: str,
    ) -> Document:
        knowledge_base = self.get_knowledge_base(knowledge_base_id)

        if knowledge_base is None:
            raise ValueError(
                f"Knowledge base {knowledge_base_id} does not belong "
                f"to workspace {self.workspace_id}."
            )

        existing_document = self.get_document_by_checksum(
            knowledge_base_id=knowledge_base_id,
            checksum=checksum,
        )

        if existing_document is not None:
            existing_document.filename = filename
            existing_document.file_path = str(file_path)
            existing_document.status = PROCESSING_STATUS

            self.session.flush()

            return existing_document

        return create_processing_document(
            session=self.session,
            workspace_id=self.workspace_id,
            knowledge_base_id=knowledge_base_id,
            filename=filename,
            file_path=str(file_path),
            checksum=checksum,
        )

    def mark_processing_success(
        self,
        document: Document,
        page_count: int,
        chunk_count: int,
    ) -> Document:
        if document.workspace_id != self.workspace_id:
            raise ValueError(
                "Document does not belong to the current workspace."
            )

        result = update_document_processing_result(
            session=self.session,
            document=document,
            page_count=page_count,
            chunk_count=chunk_count,
        )

        archive_active_documents(
            session=self.session,
            workspace_id=self.workspace_id,
            knowledge_base_id=document.knowledge_base_id,
            exclude_document_id=document.id,
        )

        return result

    def mark_processing_failed(
        self,
        document: Document,
    ) -> Document:
        if document.workspace_id != self.workspace_id:
            raise ValueError(
                "Document does not belong to the current workspace."
            )

        return mark_document_failed(
            session=self.session,
            document=document,
        )

    def archive_other_active_documents(
        self,
        knowledge_base_id: int,
        exclude_document_id: int | None = None,
    ) -> int:
        return archive_active_documents(
            session=self.session,
            workspace_id=self.workspace_id,
            knowledge_base_id=knowledge_base_id,
            exclude_document_id=exclude_document_id,
        )

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


__all__ = [
    "ACTIVE_STATUS",
    "ARCHIVED_STATUS",
    "FAILED_STATUS",
    "PROCESSING_STATUS",
    "DocumentService",
    "DocumentUpload",
]
