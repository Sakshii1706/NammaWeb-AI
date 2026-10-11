from __future__ import annotations

from sqlalchemy.orm import Session

from reach.db.models import Document, KnowledgeBase


ACTIVE_STATUS = "active"
PROCESSING_STATUS = "processing"
FAILED_STATUS = "failed"
ARCHIVED_STATUS = "archived"


def get_or_create_knowledge_base(
    session: Session,
    workspace_id: int,
    name: str = "NammaWeb Documents",
    description: str = "Documents uploaded to the NammaWeb AI knowledge workspace.",
) -> KnowledgeBase:
    knowledge_base = (
        session.query(KnowledgeBase)
        .filter(
            KnowledgeBase.workspace_id == workspace_id,
            KnowledgeBase.name == name,
        )
        .first()
    )

    if knowledge_base is None:
        knowledge_base = KnowledgeBase(
            workspace_id=workspace_id,
            name=name,
            description=description,
        )
        session.add(knowledge_base)
        session.flush()

    return knowledge_base


def get_knowledge_base_by_id(
    session: Session,
    workspace_id: int,
    knowledge_base_id: int,
) -> KnowledgeBase | None:
    return (
        session.query(KnowledgeBase)
        .filter(
            KnowledgeBase.workspace_id == workspace_id,
            KnowledgeBase.id == knowledge_base_id,
        )
        .first()
    )


def get_document_by_id(
    session: Session,
    workspace_id: int,
    document_id: int,
) -> Document | None:
    return (
        session.query(Document)
        .filter(
            Document.workspace_id == workspace_id,
            Document.id == document_id,
        )
        .first()
    )


def get_document_by_checksum(
    session: Session,
    workspace_id: int,
    knowledge_base_id: int,
    checksum: str,
) -> Document | None:
    return (
        session.query(Document)
        .filter(
            Document.workspace_id == workspace_id,
            Document.knowledge_base_id == knowledge_base_id,
            Document.checksum == checksum,
        )
        .order_by(Document.id.desc())
        .first()
    )


def get_active_document(
    session: Session,
    workspace_id: int,
    knowledge_base_id: int,
) -> Document | None:
    return (
        session.query(Document)
        .filter(
            Document.workspace_id == workspace_id,
            Document.knowledge_base_id == knowledge_base_id,
            Document.status == ACTIVE_STATUS,
        )
        .order_by(Document.id.desc())
        .first()
    )


def list_documents(
    session: Session,
    workspace_id: int,
    knowledge_base_id: int,
) -> list[Document]:
    return (
        session.query(Document)
        .filter(
            Document.workspace_id == workspace_id,
            Document.knowledge_base_id == knowledge_base_id,
        )
        .order_by(Document.id.desc())
        .all()
    )


def create_processing_document(
    session: Session,
    workspace_id: int,
    knowledge_base_id: int,
    filename: str,
    file_path: str,
    checksum: str,
) -> Document:
    document = Document(
        workspace_id=workspace_id,
        knowledge_base_id=knowledge_base_id,
        filename=filename,
        file_path=file_path,
        checksum=checksum,
        page_count=None,
        chunk_count=None,
        status=PROCESSING_STATUS,
    )

    session.add(document)
    session.flush()

    return document


def update_document_processing_result(
    session: Session,
    document: Document,
    page_count: int,
    chunk_count: int,
) -> Document:
    document.page_count = page_count
    document.chunk_count = chunk_count
    document.status = ACTIVE_STATUS

    session.flush()

    return document


def mark_document_failed(
    session: Session,
    document: Document,
) -> Document:
    document.status = FAILED_STATUS

    session.flush()

    return document


def archive_document(
    session: Session,
    document: Document,
) -> Document:
    document.status = ARCHIVED_STATUS

    session.flush()

    return document


def archive_active_documents(
    session: Session,
    workspace_id: int,
    knowledge_base_id: int,
    exclude_document_id: int | None = None,
) -> int:
    query = (
        session.query(Document)
        .filter(
            Document.workspace_id == workspace_id,
            Document.knowledge_base_id == knowledge_base_id,
            Document.status == ACTIVE_STATUS,
        )
    )

    if exclude_document_id is not None:
        query = query.filter(Document.id != exclude_document_id)

    documents = query.all()

    for document in documents:
        document.status = ARCHIVED_STATUS

    session.flush()

    return len(documents)
