from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from reach.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    workspace_id: Mapped[int] = mapped_column(
        ForeignKey(
            "workspaces.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    channel: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="email",
    )

    subject: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    message_template: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft",
        index=True,
    )

    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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
        back_populates="campaigns",
    )

    recipients: Mapped[list["CampaignRecipient"]] = relationship(
        "CampaignRecipient",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "id",
            name="uq_campaigns_workspace_id_id",
        ),
        Index(
            "ix_campaigns_workspace_status",
            "workspace_id",
            "status",
        ),
    )


class CampaignRecipient(Base):
    __tablename__ = "campaign_recipients"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    campaign_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    workspace_id: Mapped[int] = mapped_column(
        ForeignKey(
            "workspaces.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
        index=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
    )

    provider_recipient_id: Mapped[str | None] = mapped_column(
        String(255),
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

    campaign: Mapped["Campaign"] = relationship(
        "Campaign",
        back_populates="recipients",
        primaryjoin=(
            "and_("
            "CampaignRecipient.campaign_id == Campaign.id, "
            "CampaignRecipient.workspace_id == Campaign.workspace_id"
            ")"
        ),
        foreign_keys="[CampaignRecipient.campaign_id]",
    )

    delivery_attempts: Mapped[list["DeliveryAttempt"]] = relationship(
        "DeliveryAttempt",
        back_populates="campaign_recipient",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "campaign_id"],
            ["campaigns.workspace_id", "campaigns.id"],
            ondelete="CASCADE",
        ),
        Index(
            "ix_campaign_recipients_workspace_status",
            "workspace_id",
            "status",
        ),
        Index(
            "ix_campaign_recipients_campaign_status",
            "campaign_id",
            "status",
        ),
    )


class DeliveryAttempt(Base):
    __tablename__ = "delivery_attempts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    campaign_recipient_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    workspace_id: Mapped[int] = mapped_column(
        ForeignKey(
            "workspaces.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    channel: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
    )

    provider_message_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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

    campaign_recipient: Mapped["CampaignRecipient"] = relationship(
        "CampaignRecipient",
        back_populates="delivery_attempts",
        primaryjoin=(
            "and_("
            "DeliveryAttempt.campaign_recipient_id == CampaignRecipient.id, "
            "DeliveryAttempt.workspace_id == CampaignRecipient.workspace_id"
            ")"
        ),
        foreign_keys="[DeliveryAttempt.campaign_recipient_id]",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "campaign_recipient_id"],
            [
                "campaign_recipients.workspace_id",
                "campaign_recipients.id",
            ],
            ondelete="CASCADE",
        ),
        Index(
            "ix_delivery_attempts_workspace_status",
            "workspace_id",
            "status",
        ),
        Index(
            "ix_delivery_attempts_recipient_created",
            "campaign_recipient_id",
            "created_at",
        ),
    )


from reach.db.identity_models import Workspace  # noqa: E402, F401
