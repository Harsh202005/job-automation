"""
SQLAlchemy model for job applications.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Application(Base):
    __tablename__ = "applications"

    # ── Constraints ───────────────────────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint("resume_id", "job_id", name="uq_applications_resume_job"),
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

    # ── Application State ─────────────────────────────────────────────────────
    # Status enum values: "pending_review" | "submitted" | "failed" | "skipped"
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="Application status: pending_review | submitted | failed | skipped",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the application was successfully submitted",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Artifacts & Diagnostics ───────────────────────────────────────────────
    screenshot_path: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="Path to pre-submit screenshot for manual review",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Details if failed or why flagged for manual review",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    resume = relationship("Resume", lazy="select")
    job = relationship("Job", lazy="select")

    def __repr__(self) -> str:
        return f"<Application id={self.id} job_id={self.job_id} status={self.status!r}>"
