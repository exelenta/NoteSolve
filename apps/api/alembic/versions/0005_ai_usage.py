"""Track token usage for analysis and agent edit jobs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_ai_usage"
down_revision: str | Sequence[str] | None = "0004_agent_edit_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for column in ("input_tokens", "output_tokens", "total_tokens"):
        op.add_column(
            "worksheet_results",
            sa.Column(column, sa.Integer(), nullable=False, server_default="0"),
        )
        op.add_column(
            "agent_edit_jobs",
            sa.Column(column, sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    for column in ("total_tokens", "output_tokens", "input_tokens"):
        op.drop_column("agent_edit_jobs", column)
        op.drop_column("worksheet_results", column)
