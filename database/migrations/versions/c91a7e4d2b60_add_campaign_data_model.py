"""add campaign data model

Revision ID: c91a7e4d2b60
Revises: 7c4e2b9a1f63
Create Date: 2026-09-26
"""

from alembic import op
import sqlalchemy as sa


revision = "c91a7e4d2b60"
down_revision = "7c4e2b9a1f63"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "channel",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "subject",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "message_template",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "scheduled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "cancelled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "id",
            name="uq_campaigns_workspace_id_id",
        ),
    )

    op.create_index(
        "ix_campaigns_workspace_id",
        "campaigns",
        ["workspace_id"],
    )

    op.create_index(
        "ix_campaigns_status",
        "campaigns",
        ["status"],
    )

    op.create_index(
        "ix_campaigns_workspace_status",
        "campaigns",
        ["workspace_id", "status"],
    )

    op.create_table(
        "campaign_recipients",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "campaign_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "full_name",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "email",
            sa.String(length=320),
            nullable=True,
        ),
        sa.Column(
            "phone",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "provider_recipient_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "campaign_id"],
            ["campaigns.workspace_id", "campaigns.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_campaign_recipients_campaign_id",
        "campaign_recipients",
        ["campaign_id"],
    )

    op.create_index(
        "ix_campaign_recipients_workspace_id",
        "campaign_recipients",
        ["workspace_id"],
    )

    op.create_index(
        "ix_campaign_recipients_email",
        "campaign_recipients",
        ["email"],
    )

    op.create_index(
        "ix_campaign_recipients_phone",
        "campaign_recipients",
        ["phone"],
    )

    op.create_index(
        "ix_campaign_recipients_status",
        "campaign_recipients",
        ["status"],
    )

    op.create_index(
        "ix_campaign_recipients_workspace_status",
        "campaign_recipients",
        ["workspace_id", "status"],
    )

    op.create_index(
        "ix_campaign_recipients_campaign_status",
        "campaign_recipients",
        ["campaign_id", "status"],
    )

    op.create_table(
        "delivery_attempts",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "campaign_recipient_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "provider",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "channel",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "provider_message_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "attempted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "campaign_recipient_id"],
            [
                "campaign_recipients.workspace_id",
                "campaign_recipients.id",
            ],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_delivery_attempts_campaign_recipient_id",
        "delivery_attempts",
        ["campaign_recipient_id"],
    )

    op.create_index(
        "ix_delivery_attempts_workspace_id",
        "delivery_attempts",
        ["workspace_id"],
    )

    op.create_index(
        "ix_delivery_attempts_status",
        "delivery_attempts",
        ["status"],
    )

    op.create_index(
        "ix_delivery_attempts_workspace_status",
        "delivery_attempts",
        ["workspace_id", "status"],
    )

    op.create_index(
        "ix_delivery_attempts_recipient_created",
        "delivery_attempts",
        ["campaign_recipient_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_delivery_attempts_recipient_created",
        table_name="delivery_attempts",
    )

    op.drop_index(
        "ix_delivery_attempts_workspace_status",
        table_name="delivery_attempts",
    )

    op.drop_index(
        "ix_delivery_attempts_status",
        table_name="delivery_attempts",
    )

    op.drop_index(
        "ix_delivery_attempts_workspace_id",
        table_name="delivery_attempts",
    )

    op.drop_index(
        "ix_delivery_attempts_campaign_recipient_id",
        table_name="delivery_attempts",
    )

    op.drop_table("delivery_attempts")

    op.drop_index(
        "ix_campaign_recipients_campaign_status",
        table_name="campaign_recipients",
    )

    op.drop_index(
        "ix_campaign_recipients_workspace_status",
        table_name="campaign_recipients",
    )

    op.drop_index(
        "ix_campaign_recipients_status",
        table_name="campaign_recipients",
    )

    op.drop_index(
        "ix_campaign_recipients_phone",
        table_name="campaign_recipients",
    )

    op.drop_index(
        "ix_campaign_recipients_email",
        table_name="campaign_recipients",
    )

    op.drop_index(
        "ix_campaign_recipients_workspace_id",
        table_name="campaign_recipients",
    )

    op.drop_index(
        "ix_campaign_recipients_campaign_id",
        table_name="campaign_recipients",
    )

    op.drop_table("campaign_recipients")

    op.drop_index(
        "ix_campaigns_workspace_status",
        table_name="campaigns",
    )

    op.drop_index(
        "ix_campaigns_status",
        table_name="campaigns",
    )

    op.drop_index(
        "ix_campaigns_workspace_id",
        table_name="campaigns",
    )

    op.drop_table("campaigns")
