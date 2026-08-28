"""
POST /api/resume/upload
Accepts a multipart PDF or DOCX file, runs the parser, saves to DB, returns parsed JSON.
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.models.resume import Resume
from app.parsers.resume_parser import parse_resume, extract_raw_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/resume", tags=["Resume"])

_ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}
_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

async def _save_upload(upload: UploadFile, dest_dir: Path) -> Path:
    """Stream the uploaded file to disk and return its path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or "").suffix.lower() or ".bin"
    unique_name = f"{uuid.uuid4().hex}{suffix}"
    file_path = dest_dir / unique_name

    async with aiofiles.open(file_path, "wb") as out:
        while chunk := await upload.read(1024 * 256):  # 256 KB chunks
            await out.write(chunk)

    return file_path


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    summary="Upload and parse a resume (PDF or DOCX)",
    response_description="Structured parsed resume data + DB record ID",
)
async def upload_resume(
    file: UploadFile = File(..., description="PDF or DOCX resume file"),
    db: AsyncSession = Depends(get_db),
):
    """
    **Upload a resume file** and get back structured JSON:

    - Extracts raw text via pdfplumber (PDF) or python-docx (DOCX)
    - Uses spaCy NER + regex to parse contact info, skills, experience, education
    - Persists the record (raw text + parsed JSON) to PostgreSQL
    - Returns the parsed data along with the generated record `id`
    """
    # ── Validation ───────────────────────────────────────────────────────────
    original_filename = file.filename or "unknown"
    ext = Path(original_filename).suffix.lower()

    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(_ALLOWED_EXTENSIONS)}",
        )

    if file.content_type and file.content_type not in _ALLOWED_TYPES:
        # Warn but don't hard-block — browsers sometimes send wrong MIME types for .docx
        logger.warning("Unexpected content_type '%s' for file '%s'", file.content_type, original_filename)

    # ── Size check (early, before full read) — note: not all clients send Content-Length
    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    # ── Save to disk ─────────────────────────────────────────────────────────
    upload_dir = Path(settings.upload_dir)
    try:
        file_path = await _save_upload(file, upload_dir)
    except Exception as exc:
        logger.exception("Failed to save uploaded file")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file: {exc}",
        ) from exc

    # Size check post-save
    saved_size = file_path.stat().st_size
    if saved_size > max_bytes:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.max_upload_size_mb} MB.",
        )

    # ── Parse ────────────────────────────────────────────────────────────────
    try:
        parsed = parse_resume(file_path)
    except Exception as exc:
        logger.exception("Parsing failed for '%s'", original_filename)
        # Don't delete the file — may be useful for debugging
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Resume parsing failed: {exc}",
        ) from exc

    # ── Extract raw text for storage (already extracted inside parser, but we
    #    re-use the standalone helper to avoid coupling) ──────────────────────
    try:
        raw_text = extract_raw_text(file_path)
    except Exception:
        raw_text = ""

    # ── Persist ──────────────────────────────────────────────────────────────
    try:
        resume_record = Resume(
            file_path=str(file_path.resolve()),
            original_filename=original_filename,
            raw_text=raw_text,
            parsed_json=parsed,
        )
        db.add(resume_record)
        await db.flush()          # Get the generated ID without committing yet
        record_id = str(resume_record.id)
        # Commit happens automatically in get_db() on exit
    except Exception as exc:
        logger.exception("DB insert failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {exc}",
        ) from exc

    return {
        "id": record_id,
        "filename": original_filename,
        **parsed,
    }


@router.get(
    "/{resume_id}",
    summary="Retrieve a previously parsed resume by ID",
)
async def get_resume(resume_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Fetch a stored resume record by its UUID."""
    from sqlalchemy import select  # noqa: PLC0415

    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    return {
        "id": str(record.id),
        "filename": record.original_filename,
        "uploaded_at": record.uploaded_at.isoformat(),
        "file_path": record.file_path,
        **record.parsed_json,
    }
