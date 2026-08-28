"""
SQLAlchemy model for a resume ↔ job match score record.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Match(Base):
    __tablename__ = "matches"

    # ── Constraints ───────────────────────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint("resume_id", "job_id", name="uq_matches_resume_job"),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # ── Foreign keys ──────────────────────────────────────────────────────────
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Score ─────────────────────────────────────────────────────────────────
    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Cosine similarity between resume profile embedding and job description embedding (0-1)",
    )

    # ── Skill gap analysis ────────────────────────────────────────────────────
    matched_skills: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Resume skills found (case-insensitive substring) in the job description",
    )
    missing_skills: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Job description skill keywords NOT found in the resume",
    )

    # ── Timestamp ─────────────────────────────────────────────────────────────
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── ORM relationships (lazy by default, no N+1 risk for our endpoints) ───
    resume = relationship("Resume", lazy="select")
    job = relationship("Job", lazy="select")

    def __repr__(self) -> str:
        return (
            f"<Match resume={self.resume_id} job={self.job_id} score={self.score:.3f}>"
        )
