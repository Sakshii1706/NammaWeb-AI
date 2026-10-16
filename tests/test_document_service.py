from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from reach.db.base import Base
from reach.db.identity_models import Workspace
from reach.db.document_repository import (
    ACTIVE_STATUS,
    FAILED_STATUS,
    PROCESSING_STATUS,
    ARCHIVED_STATUS,
)
from reach.services.document_service import DocumentService


def make_test_session(tmp_path) -> tuple[Session, int]:
    database_path = tmp_path / "test.db"

    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(bind=engine)

    session = Session(engine)

    workspace = Workspace(
        name="Test Workspace",
        slug="test-workspace",
    )

    session.add(workspace)
    session.commit()
    session.refresh(workspace)

    return session, workspace.id


def make_service(tmp_path) -> tuple[Session, DocumentService]:
    session, workspace_id = make_test_session(tmp_path)
    service = DocumentService(
        session=session,
        workspace_id=workspace_id,
    )
    return session, service


def test_prepare_processing_creates_processing_document(tmp_path):
    session, service = make_service(tmp_path)

    try:
        knowledge_base = service.get_or_create_default_knowledge_base()

        document = service.prepare_processing(
            knowledge_base_id=knowledge_base.id,
            filename="test.pdf",
            file_path=Path("test.pdf"),
            checksum="checksum-1",
        )

        assert document.id is not None
        assert document.workspace_id == service.workspace_id
        assert document.knowledge_base_id == knowledge_base.id
        assert document.filename == "test.pdf"
        assert document.status == PROCESSING_STATUS

    finally:
        session.close()


def test_mark_processing_failed_changes_status_to_failed(tmp_path):
    session, service = make_service(tmp_path)

    try:
        knowledge_base = service.get_or_create_default_knowledge_base()

        document = service.prepare_processing(
            knowledge_base_id=knowledge_base.id,
            filename="test.pdf",
            file_path=Path("test.pdf"),
            checksum="checksum-1",
        )

        service.mark_processing_failed(document)
        session.commit()

        refreshed = service.get_document_by_id(document.id)

        assert refreshed is not None
        assert refreshed.status == FAILED_STATUS

    finally:
        session.close()


def test_mark_processing_success_activates_document(tmp_path):
    session, service = make_service(tmp_path)

    try:
        knowledge_base = service.get_or_create_default_knowledge_base()

        document = service.prepare_processing(
            knowledge_base_id=knowledge_base.id,
            filename="test.pdf",
            file_path=Path("test.pdf"),
            checksum="checksum-1",
        )

        service.mark_processing_success(
            document=document,
            page_count=12,
            chunk_count=90,
        )

        session.commit()

        refreshed = service.get_document_by_id(document.id)

        assert refreshed is not None
        assert refreshed.status == ACTIVE_STATUS
        assert refreshed.page_count == 12
        assert refreshed.chunk_count == 90

    finally:
        session.close()


def test_success_archives_previous_active_document(tmp_path):
    session, service = make_service(tmp_path)

    try:
        knowledge_base = service.get_or_create_default_knowledge_base()

        first_document = service.prepare_processing(
            knowledge_base_id=knowledge_base.id,
            filename="first.pdf",
            file_path=Path("first.pdf"),
            checksum="checksum-1",
        )

        service.mark_processing_success(
            document=first_document,
            page_count=10,
            chunk_count=50,
        )

        session.commit()

        second_document = service.prepare_processing(
            knowledge_base_id=knowledge_base.id,
            filename="second.pdf",
            file_path=Path("second.pdf"),
            checksum="checksum-2",
        )

        service.mark_processing_success(
            document=second_document,
            page_count=12,
            chunk_count=60,
        )

        session.commit()

        first_refreshed = service.get_document_by_id(first_document.id)
        second_refreshed = service.get_document_by_id(second_document.id)

        assert first_refreshed is not None
        assert second_refreshed is not None

        assert first_refreshed.status == ARCHIVED_STATUS
        assert second_refreshed.status == ACTIVE_STATUS

    finally:
        session.close()


def test_failed_document_does_not_archive_previous_active_document(tmp_path):
    session, service = make_service(tmp_path)

    try:
        knowledge_base = service.get_or_create_default_knowledge_base()

        first_document = service.prepare_processing(
            knowledge_base_id=knowledge_base.id,
            filename="first.pdf",
            file_path=Path("first.pdf"),
            checksum="checksum-1",
        )

        service.mark_processing_success(
            document=first_document,
            page_count=10,
            chunk_count=50,
        )

        session.commit()

        second_document = service.prepare_processing(
            knowledge_base_id=knowledge_base.id,
            filename="second.pdf",
            file_path=Path("second.pdf"),
            checksum="checksum-2",
        )

        service.mark_processing_failed(second_document)
        session.commit()

        first_refreshed = service.get_document_by_id(first_document.id)
        second_refreshed = service.get_document_by_id(second_document.id)

        assert first_refreshed is not None
        assert second_refreshed is not None

        assert first_refreshed.status == ACTIVE_STATUS
        assert second_refreshed.status == FAILED_STATUS

    finally:
        session.close()


def test_workspace_cannot_access_another_workspace_document(tmp_path):
    session, workspace_a_id = make_test_session(tmp_path)

    try:
        workspace_b = Workspace(
            name="Workspace B",
            slug="workspace-b",
        )

        session.add(workspace_b)
        session.commit()
        session.refresh(workspace_b)

        service_a = DocumentService(
            session=session,
            workspace_id=workspace_a_id,
        )

        service_b = DocumentService(
            session=session,
            workspace_id=workspace_b.id,
        )

        kb_a = service_a.get_or_create_default_knowledge_base()

        document_a = service_a.prepare_processing(
            knowledge_base_id=kb_a.id,
            filename="workspace-a.pdf",
            file_path=Path("workspace-a.pdf"),
            checksum="workspace-a-checksum",
        )

        service_a.mark_processing_success(
            document=document_a,
            page_count=5,
            chunk_count=20,
        )

        session.commit()

        assert service_a.get_document_by_id(document_a.id) is not None

        assert service_b.get_document_by_id(document_a.id) is None

        assert service_b.get_document_by_checksum(
            knowledge_base_id=kb_a.id,
            checksum="workspace-a-checksum",
        ) is None

    finally:
        session.close()


def test_workspace_cannot_use_another_workspace_knowledge_base(tmp_path):
    session, workspace_a_id = make_test_session(tmp_path)

    try:
        workspace_b = Workspace(
            name="Workspace B",
            slug="workspace-b",
        )

        session.add(workspace_b)
        session.commit()
        session.refresh(workspace_b)

        service_a = DocumentService(
            session=session,
            workspace_id=workspace_a_id,
        )

        service_b = DocumentService(
            session=session,
            workspace_id=workspace_b.id,
        )

        kb_a = service_a.get_or_create_default_knowledge_base()

        try:
            service_b.prepare_processing(
                knowledge_base_id=kb_a.id,
                filename="unauthorized.pdf",
                file_path=Path("unauthorized.pdf"),
                checksum="unauthorized-checksum",
            )

            assert False, "Expected workspace isolation error."

        except ValueError as exc:
            assert "does not belong" in str(exc)

    finally:
        session.close()
