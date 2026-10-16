from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from reach.auth.auth_service import AuthService
from reach.db.base import Base
from reach.db.identity_models import Membership, Workspace


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


def test_password_hash_and_verify(tmp_path):
    session, _ = make_test_session(tmp_path)

    try:
        auth = AuthService(session)

        password = "StrongPassword123!"
        password_hash = auth.hash_password(password)

        assert password_hash != password
        assert auth.verify_password(password, password_hash)
        assert not auth.verify_password("WrongPassword", password_hash)

    finally:
        session.close()


def test_register_user_creates_user_and_membership(tmp_path):
    session, workspace_id = make_test_session(tmp_path)

    try:
        auth = AuthService(session)

        workspace = session.query(Workspace).filter(
            Workspace.id == workspace_id
        ).first()

        assert workspace is not None

        user = auth.register_user(
            email="Test@Example.com",
            password="StrongPassword123!",
            full_name="Test User",
            workspace=workspace,
        )

        session.commit()

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.is_active is True
        assert user.password_hash != "StrongPassword123!"

        membership = (
            session.query(Membership)
            .filter(
                Membership.user_id == user.id,
                Membership.workspace_id == workspace.id,
            )
            .first()
        )

        assert membership is not None
        assert membership.role == "owner"

    finally:
        session.close()


def test_authenticate_returns_workspace_identity(tmp_path):
    session, workspace_id = make_test_session(tmp_path)

    try:
        auth = AuthService(session)

        workspace = session.query(Workspace).filter(
            Workspace.id == workspace_id
        ).first()

        assert workspace is not None

        auth.register_user(
            email="user@example.com",
            password="StrongPassword123!",
            full_name="Test User",
            workspace=workspace,
        )

        session.commit()

        authenticated = auth.authenticate(
            email="USER@EXAMPLE.COM",
            password="StrongPassword123!",
        )

        assert authenticated is not None
        assert authenticated.email == "user@example.com"
        assert authenticated.full_name == "Test User"
        assert authenticated.workspace_id == workspace.id
        assert authenticated.workspace_name == "Test Workspace"
        assert authenticated.workspace_slug == "test-workspace"
        assert authenticated.role == "owner"

    finally:
        session.close()


def test_wrong_password_is_rejected(tmp_path):
    session, workspace_id = make_test_session(tmp_path)

    try:
        auth = AuthService(session)

        workspace = session.query(Workspace).filter(
            Workspace.id == workspace_id
        ).first()

        assert workspace is not None

        auth.register_user(
            email="user@example.com",
            password="CorrectPassword123!",
            full_name="Test User",
            workspace=workspace,
        )

        session.commit()

        authenticated = auth.authenticate(
            email="user@example.com",
            password="WrongPassword123!",
        )

        assert authenticated is None

    finally:
        session.close()


def test_unknown_user_is_rejected(tmp_path):
    session, _ = make_test_session(tmp_path)

    try:
        auth = AuthService(session)

        authenticated = auth.authenticate(
            email="unknown@example.com",
            password="Password123!",
        )

        assert authenticated is None

    finally:
        session.close()


def test_inactive_user_is_rejected(tmp_path):
    session, workspace_id = make_test_session(tmp_path)

    try:
        auth = AuthService(session)

        workspace = session.query(Workspace).filter(
            Workspace.id == workspace_id
        ).first()

        assert workspace is not None

        user = auth.register_user(
            email="inactive@example.com",
            password="Password123!",
            full_name="Inactive User",
            workspace=workspace,
        )

        user.is_active = False
        session.commit()

        authenticated = auth.authenticate(
            email="inactive@example.com",
            password="Password123!",
        )

        assert authenticated is None

    finally:
        session.close()


def test_duplicate_email_is_rejected(tmp_path):
    session, workspace_id = make_test_session(tmp_path)

    try:
        auth = AuthService(session)

        workspace = session.query(Workspace).filter(
            Workspace.id == workspace_id
        ).first()

        assert workspace is not None

        auth.register_user(
            email="user@example.com",
            password="Password123!",
            full_name="First User",
            workspace=workspace,
        )

        session.commit()

        with pytest.raises(ValueError, match="already exists"):
            auth.register_user(
                email="USER@EXAMPLE.COM",
                password="AnotherPassword123!",
                full_name="Second User",
                workspace=workspace,
            )

    finally:
        session.close()
