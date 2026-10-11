"""add workspace scoping

Revision ID: 7c4e2b9a1f63
Revises: b93d00a3e04b
Create Date: 2026-09-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c4e2b9a1f63"
down_revision: Union[str, Sequence[str], None] = "b93d00a3e04b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_WORKSPACE_NAME = "NammaWeb Workspace"
DEFAULT_WORKSPACE_SLUG = "nammaweb-default"


def upgrade() -> None:
    # ---------------------------------------------------------
    # 1. Add workspace_id columns as nullable temporarily.
    # ---------------------------------------------------------
    op.add_column(
        "knowledge_bases",
        sa.Column("workspace_id", sa.Integer(), nullable=True),
    )

    op.add_column(
        "documents",
        sa.Column("workspace_id", sa.Integer(), nullable=True),
    )

    # ---------------------------------------------------------
    # 2. Create the default workspace for existing data.
    # ---------------------------------------------------------
    connection = op.get_bind()

    existing_workspace = connection.execute(
        sa.text(
            """
            SELECT id
            FROM workspaces
            WHERE slug = :slug
            """
        ),
        {"slug": DEFAULT_WORKSPACE_SLUG},
    ).fetchone()

    if existing_workspace is None:
        connection.execute(
            sa.text(
                """
                INSERT INTO workspaces (name, slug, created_at, updated_at)
                VALUES (
                    :name,
                    :slug,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "name": DEFAULT_WORKSPACE_NAME,
                "slug": DEFAULT_WORKSPACE_SLUG,
            },
        )

    workspace_row = connection.execute(
        sa.text(
            """
            SELECT id
            FROM workspaces
            WHERE slug = :slug
            """
        ),
        {"slug": DEFAULT_WORKSPACE_SLUG},
    ).fetchone()

    if workspace_row is None:
        raise RuntimeError("Failed to create or locate the default workspace.")

    workspace_id = workspace_row[0]

    # ---------------------------------------------------------
    # 3. Backfill existing KnowledgeBase records.
    # ---------------------------------------------------------
    connection.execute(
        sa.text(
            """
            UPDATE knowledge_bases
            SET workspace_id = :workspace_id
            WHERE workspace_id IS NULL
            """
        ),
        {"workspace_id": workspace_id},
    )

    # ---------------------------------------------------------
    # 4. Backfill existing Documents from their KnowledgeBase.
    # ---------------------------------------------------------
    connection.execute(
        sa.text(
            """
            UPDATE documents
            SET workspace_id = (
                SELECT workspace_id
                FROM knowledge_bases
                WHERE knowledge_bases.id = documents.knowledge_base_id
            )
            WHERE workspace_id IS NULL
            """
        )
    )

    # ---------------------------------------------------------
    # 5. Make KnowledgeBase.workspace_id mandatory and add FK.
    # ---------------------------------------------------------
    with op.batch_alter_table("knowledge_bases") as batch_op:
        batch_op.alter_column(
            "workspace_id",
            existing_type=sa.Integer(),
            nullable=False,
        )

        batch_op.create_foreign_key(
            "fk_knowledge_bases_workspace_id",
            "workspaces",
            ["workspace_id"],
            ["id"],
            ondelete="CASCADE",
        )

        # Needed so Document can enforce the workspace +
        # knowledge-base relationship.
        batch_op.create_unique_constraint(
            "uq_knowledge_bases_workspace_id_id",
            ["workspace_id", "id"],
        )

    # ---------------------------------------------------------
    # 6. Make Document.workspace_id mandatory and add FKs.
    # ---------------------------------------------------------
    with op.batch_alter_table("documents") as batch_op:
        batch_op.alter_column(
            "workspace_id",
            existing_type=sa.Integer(),
            nullable=False,
        )

        batch_op.create_foreign_key(
            "fk_documents_workspace_id",
            "workspaces",
            ["workspace_id"],
            ["id"],
            ondelete="CASCADE",
        )

        # Prevent a document from referencing a KnowledgeBase
        # belonging to another workspace.
        batch_op.create_foreign_key(
            "fk_documents_workspace_kb",
            "knowledge_bases",
            ["workspace_id", "knowledge_base_id"],
            ["workspace_id", "id"],
            ondelete="CASCADE",
        )

    # ---------------------------------------------------------
    # 7. Add indexes for workspace-scoped queries.
    # ---------------------------------------------------------
    op.create_index(
        "ix_knowledge_bases_workspace_id",
        "knowledge_bases",
        ["workspace_id"],
    )

    op.create_index(
        "ix_documents_workspace_id",
        "documents",
        ["workspace_id"],
    )

    op.create_index(
        "ix_documents_workspace_status",
        "documents",
        ["workspace_id", "status"],
    )


def downgrade() -> None:
    # Remove indexes first.
    op.drop_index(
        "ix_documents_workspace_status",
        table_name="documents",
    )

    op.drop_index(
        "ix_documents_workspace_id",
        table_name="documents",
    )

    op.drop_index(
        "ix_knowledge_bases_workspace_id",
        table_name="knowledge_bases",
    )

    # Remove document constraints/column.
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_constraint(
            "fk_documents_workspace_kb",
            type_="foreignkey",
        )

        batch_op.drop_constraint(
            "fk_documents_workspace_id",
            type_="foreignkey",
        )

        batch_op.drop_column("workspace_id")

    # Remove knowledge-base constraints/column.
    with op.batch_alter_table("knowledge_bases") as batch_op:
        batch_op.drop_constraint(
            "uq_knowledge_bases_workspace_id_id",
            type_="unique",
        )

        batch_op.drop_constraint(
            "fk_knowledge_bases_workspace_id",
            type_="foreignkey",
        )

        batch_op.drop_column("workspace_id")
