"""Store structured worksheet analysis results."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_worksheet_results"
down_revision: str | Sequence[str] | None = "0001_day1_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "worksheet_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["pipeline_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id"),
    )
    op.create_index("ix_worksheet_results_workspace_id", "worksheet_results", ["workspace_id"])
    op.create_index(
        "ix_worksheet_results_document_id", "worksheet_results", ["document_id"], unique=True
    )
    op.create_index("ix_worksheet_results_job_id", "worksheet_results", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_worksheet_results_job_id", table_name="worksheet_results")
    op.drop_index("ix_worksheet_results_document_id", table_name="worksheet_results")
    op.drop_index("ix_worksheet_results_workspace_id", table_name="worksheet_results")
    op.drop_table("worksheet_results")
