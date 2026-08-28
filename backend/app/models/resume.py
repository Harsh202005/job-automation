"""
SQLAlchemy model for a parsed resume record.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Resume(Base):
    __tablename__ = "resumes"

    # ── Primary key ───────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # ── Timestamps ────────────────────────────────────────────────
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── File metadata ─────────────────────────────────────────────
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)

    # ── Content ───────────────────────────────────────────────────
    raw_text: Mapped[str] = mapped_column(Text, nullable=True)

    # JSONB gives us indexable, query-able JSON storage in Postgres
    parsed_json: Mapped[dict] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<Resume id={self.id} file='{self.original_filename}'>"
