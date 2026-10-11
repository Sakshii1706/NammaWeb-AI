from __future__ import annotations

import bcrypt
from dataclasses import dataclass

from sqlalchemy.orm import Session

from reach.db.identity_models import Membership, User, Workspace


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: int
    email: str
    full_name: str
    workspace_id: int
    workspace_name: str
    workspace_slug: str
    role: str


class AuthService:
    """Authentication and workspace membership service."""

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def normalize_email(email: str) -> str:
        normalized = email.strip().lower()

        if not normalized:
            raise ValueError("Email cannot be empty.")

        return normalized

    @staticmethod
    def hash_password(password: str) -> str:
        if not password:
            raise ValueError("Password cannot be empty.")

        password_bytes = password.encode("utf-8")

        hashed = bcrypt.hashpw(
            password_bytes,
            bcrypt.gensalt(),
        )

        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        if not password or not password_hash:
            return False

        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                password_hash.encode("utf-8"),
            )
        except (ValueError, TypeError):
            return False

    def register_user(
        self,
        email: str,
        password: str,
        full_name: str,
        workspace: Workspace,
        role: str = "owner",
    ) -> User:
        email = self.normalize_email(email)
        full_name = full_name.strip()

        if not full_name:
            raise ValueError("Full name cannot be empty.")

        existing_user = (
            self.session.query(User)
            .filter(User.email == email)
            .first()
        )

        if existing_user is not None:
            raise ValueError("A user with this email already exists.")

        user = User(
            email=email,
            password_hash=self.hash_password(password),
            full_name=full_name,
            is_active=True,
        )

        self.session.add(user)
        self.session.flush()

        membership = Membership(
            user_id=user.id,
            workspace_id=workspace.id,
            role=role,
        )

        self.session.add(membership)
        self.session.flush()

        return user

    def authenticate(
        self,
        email: str,
        password: str,
    ) -> AuthenticatedUser | None:
        email = self.normalize_email(email)

        user = (
            self.session.query(User)
            .filter(User.email == email)
            .first()
        )

        if user is None:
            return None

        if not user.is_active:
            return None

        if not self.verify_password(
            password,
            user.password_hash,
        ):
            return None

        membership = (
            self.session.query(Membership)
            .filter(Membership.user_id == user.id)
            .order_by(Membership.id.asc())
            .first()
        )

        if membership is None:
            return None

        workspace = (
            self.session.query(Workspace)
            .filter(Workspace.id == membership.workspace_id)
            .first()
        )

        if workspace is None:
            return None

        return AuthenticatedUser(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            workspace_slug=workspace.slug,
            role=membership.role,
        )

    def get_user(self, user_id: int) -> User | None:
        return (
            self.session.query(User)
            .filter(User.id == user_id)
            .first()
        )

    def get_memberships(
        self,
        user_id: int,
    ) -> list[Membership]:
        return (
            self.session.query(Membership)
            .filter(Membership.user_id == user_id)
            .order_by(Membership.id.asc())
            .all()
        )
