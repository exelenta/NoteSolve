"""Persist asynchronous AI note edit jobs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_agent_edit_jobs"
down_revision: str | Sequence[str] | None = "0003_vault_change_sets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_edit_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("source_change_set_id", sa.Uuid(), nullable=False),
        sa.Column("result_change_set_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["result_change_set_id"], ["vault_change_sets.id"]),
        sa.ForeignKeyConstraint(["source_change_set_id"], ["vault_change_sets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_edit_jobs_workspace_id",
        "agent_edit_jobs",
        ["workspace_id"],
    )
    op.create_index(
        "ix_agent_edit_jobs_source_change_set_id",
        "agent_edit_jobs",
        ["source_change_set_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_edit_jobs_source_change_set_id", table_name="agent_edit_jobs")
    op.drop_index("ix_agent_edit_jobs_workspace_id", table_name="agent_edit_jobs")
    op.drop_table("agent_edit_jobs")
