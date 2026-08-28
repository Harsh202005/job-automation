"""
SQLAlchemy model for a fetched job posting.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Job(Base):
    __tablename__ = "jobs"

    # ── Constraints ───────────────────────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint("source", "source_job_id", name="uq_jobs_source_source_job_id"),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # ── Source metadata ───────────────────────────────────────────────────────
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="ATS source: 'greenhouse' | 'lever' | 'manual'",
    )
    source_job_id: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        index=True,
        comment="Native job ID from the upstream ATS",
    )

    # ── Job details ───────────────────────────────────────────────────────────
    company: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    location: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    apply_url: Mapped[str] = mapped_column(String(2048), nullable=False)

    # ── Timestamps ────────────────────────────────────────────────────────────
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the job was originally posted (from ATS data, may be None)",
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="When we last fetched/upserted this record",
    )

    # ── Raw payload ───────────────────────────────────────────────────────────
    raw_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True,
        comment="Full raw API response for this job posting",
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} source={self.source!r} title={self.title!r}>"
