"""add consent and suppression records

Revision ID: e8b4c6d1a902
Revises: c91a7e4d2b60
"""

from alembic import op
import sqlalchemy as sa


revision = "e8b4c6d1a902"
down_revision = "c91a7e4d2b60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consent_records",
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
            "channel",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "contact_key",
            sa.String(length=320),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "consented_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "notes",
            sa.Text(),
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
            "channel",
            "contact_key",
            name="uq_consent_workspace_channel_contact",
        ),
    )

    op.create_index(
        "ix_consent_records_workspace_id",
        "consent_records",
        ["workspace_id"],
    )

    op.create_index(
        "ix_consent_records_status",
        "consent_records",
        ["status"],
    )

    op.create_index(
        "ix_consent_workspace_status",
        "consent_records",
        ["workspace_id", "status"],
    )

    op.create_index(
        "ix_consent_workspace_channel_contact",
        "consent_records",
        ["workspace_id", "channel", "contact_key"],
    )

    op.create_table(
        "suppression_records",
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
            "channel",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "contact_key",
            sa.String(length=320),
            nullable=False,
        ),
        sa.Column(
            "reason",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "suppressed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "lifted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "notes",
            sa.Text(),
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
            "channel",
            "contact_key",
            name="uq_suppression_workspace_channel_contact",
        ),
    )

    op.create_index(
        "ix_suppression_records_workspace_id",
        "suppression_records",
        ["workspace_id"],
    )

    op.create_index(
        "ix_suppression_records_channel",
        "suppression_records",
        ["channel"],
    )

    op.create_index(
        "ix_suppression_workspace_channel_contact",
        "suppression_records",
        ["workspace_id", "channel", "contact_key"],
    )

    op.create_index(
        "ix_suppression_workspace_channel",
        "suppression_records",
        ["workspace_id", "channel"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_suppression_workspace_channel",
        table_name="suppression_records",
    )

    op.drop_index(
        "ix_suppression_workspace_channel_contact",
        table_name="suppression_records",
    )

    op.drop_index(
        "ix_suppression_records_channel",
        table_name="suppression_records",
    )

    op.drop_index(
        "ix_suppression_records_workspace_id",
        table_name="suppression_records",
    )

    op.drop_table("suppression_records")

    op.drop_index(
        "ix_consent_workspace_channel_contact",
        table_name="consent_records",
    )

    op.drop_index(
        "ix_consent_workspace_status",
        table_name="consent_records",
    )

    op.drop_index(
        "ix_consent_records_status",
        table_name="consent_records",
    )

    op.drop_index(
        "ix_consent_records_workspace_id",
        table_name="consent_records",
    )

    op.drop_table("consent_records")
