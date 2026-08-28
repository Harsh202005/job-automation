"""Add matches table

Revision ID: 0002_add_matches
Revises: 0001_initial
Create Date: 2026-08-28
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_add_matches"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "matches",
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
        # ── Score ─────────────────────────────────────────────────────────────
        sa.Column("score", sa.Float(), nullable=False),
        # ── Skill gap ─────────────────────────────────────────────────────────
        sa.Column(
            "matched_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="'[]'::jsonb",
        ),
        sa.Column(
            "missing_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="'[]'::jsonb",
        ),
        # ── Timestamp ─────────────────────────────────────────────────────────
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        # ── Constraints ───────────────────────────────────────────────────────
        sa.UniqueConstraint("resume_id", "job_id", name="uq_matches_resume_job"),
    )
    op.create_index("ix_matches_id", "matches", ["id"], unique=False)
    op.create_index("ix_matches_resume_id", "matches", ["resume_id"], unique=False)
    op.create_index("ix_matches_job_id", "matches", ["job_id"], unique=False)
    # Descending index on score for fast "top matches" queries
    op.create_index(
        "ix_matches_score_desc",
        "matches",
        [sa.text("score DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("matches")
