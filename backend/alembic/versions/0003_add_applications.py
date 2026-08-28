"""Add applications table

Revision ID: 0003_add_applications
Revises: 0002_add_matches
Create Date: 2026-08-28
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_add_applications"
down_revision: Union[str, None] = "0002_add_matches"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "applications",
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
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # ── Status ────────────────────────────────────────────────────────────
        sa.Column("status", sa.String(length=32), nullable=False),
        # ── Timestamps ────────────────────────────────────────────────────────
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        # ── Diagnostic Fields ─────────────────────────────────────────────────
        sa.Column("screenshot_path", sa.String(length=1024), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        # ── Constraints ───────────────────────────────────────────────────────
        sa.UniqueConstraint("resume_id", "job_id", name="uq_applications_resume_job"),
    )
    op.create_index("ix_applications_id", "applications", ["id"], unique=False)
    op.create_index("ix_applications_resume_id", "applications", ["resume_id"], unique=False)
    op.create_index("ix_applications_job_id", "applications", ["job_id"], unique=False)
    op.create_index("ix_applications_status", "applications", ["status"], unique=False)


def downgrade() -> None:
    op.drop_table("applications")
