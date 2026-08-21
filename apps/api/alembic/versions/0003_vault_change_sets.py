"""Persist approval-required Vault ChangeSets and revisions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_vault_change_sets"
down_revision: str | Sequence[str] | None = "0002_worksheet_results"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vault_change_sets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("base_revision", sa.String(length=64), nullable=True),
        sa.Column("operations_json", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_vault_change_sets_workspace_id",
        "vault_change_sets",
        ["workspace_id"],
    )
    op.create_index(
        "ix_vault_change_sets_document_id",
        "vault_change_sets",
        ["document_id"],
    )
    op.create_table(
        "vault_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("change_set_id", sa.Uuid(), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("previous_content", sa.Text(), nullable=True),
        sa.Column("applied_content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["change_set_id"], ["vault_change_sets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("change_set_id"),
    )
    op.create_index(
        "ix_vault_revisions_change_set_id",
        "vault_revisions",
        ["change_set_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_vault_revisions_change_set_id", table_name="vault_revisions")
    op.drop_table("vault_revisions")
    op.drop_index("ix_vault_change_sets_document_id", table_name="vault_change_sets")
    op.drop_index("ix_vault_change_sets_workspace_id", table_name="vault_change_sets")
    op.drop_table("vault_change_sets")
