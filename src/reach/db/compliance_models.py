from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from reach.db.base import Base
from reach.db.identity_models import Workspace


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    contact_key: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="granted",
        index=True,
    )

    source: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    consented_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "channel",
            "contact_key",
            name="uq_consent_workspace_channel_contact",
        ),
        Index(
            "ix_consent_workspace_status",
            "workspace_id",
            "status",
        ),
        Index(
            "ix_consent_workspace_channel_contact",
            "workspace_id",
            "channel",
            "contact_key",
        ),
    )


class SuppressionRecord(Base):
    __tablename__ = "suppression_records"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    contact_key: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    source: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    suppressed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    lifted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "channel",
            "contact_key",
            name="uq_suppression_workspace_channel_contact",
        ),
        Index(
            "ix_suppression_workspace_channel_contact",
            "workspace_id",
            "channel",
            "contact_key",
        ),
        Index(
            "ix_suppression_workspace_channel",
            "workspace_id",
            "channel",
        ),
    )
