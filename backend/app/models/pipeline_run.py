"""
SQLAlchemy model for automated pipeline execution logs.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

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

    # ── Execution Lifecycle ───────────────────────────────────────────────────
    # Status: "success" | "partial" | "failed"
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        default="partial",
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Metrics per stage ─────────────────────────────────────────────────────
    jobs_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matches_computed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    applications_submitted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    applications_pending: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Errors Logged ─────────────────────────────────────────────────────────
    errors: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        default=list,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    resume = relationship("Resume", lazy="select")

    def __repr__(self) -> str:
        return f"<PipelineRun id={self.id} status={self.status!r} started={self.started_at}>"
