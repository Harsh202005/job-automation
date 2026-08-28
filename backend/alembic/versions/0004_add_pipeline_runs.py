"""Add pipeline_runs table

Revision ID: 0004_add_pipeline_runs
Revises: 0003_add_applications
Create Date: 2026-08-28
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_add_pipeline_runs"
down_revision: Union[str, None] = "0003_add_applications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pipeline_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        # ── Foreign keys ──────────────────────────────────────────────────────
        sa.Column(
            "resume_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resumes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # ── Status & Timestamps ───────────────────────────────────────────────
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        # ── Metrics ───────────────────────────────────────────────────────────
        sa.Column("jobs_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matches_computed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("applications_submitted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("applications_pending", sa.Integer(), nullable=False, server_default="0"),
        # ── Diagnostics & Errors ──────────────────────────────────────────────
        sa.Column(
            "errors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_index("ix_pipeline_runs_id", "pipeline_runs", ["id"], unique=False)
    op.create_index("ix_pipeline_runs_resume_id", "pipeline_runs", ["resume_id"], unique=False)
    op.create_index("ix_pipeline_runs_status", "pipeline_runs", ["status"], unique=False)
    op.create_index("ix_pipeline_runs_started_at", "pipeline_runs", ["started_at"], unique=False)


def downgrade() -> None:
    op.drop_table("pipeline_runs")
