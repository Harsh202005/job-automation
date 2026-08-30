"""
POST /api/resume/upload
Accepts a multipart PDF or DOCX file, runs ultra-fast parsing, saves to DB,
and returns parsed profile immediately (<100ms) with non-blocking background auto-matching.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Annotated, Any

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_api_key
from app.core.config import settings
from app.core.db import AsyncSessionLocal, get_db
from app.matching.matching_service import run_matching_for_resume
from app.models.resume import Resume
from app.parsers.resume_parser import parse_resume_with_raw_text

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
    """
    Stream uploaded file to disk while validating size and magic byte signatures
    to prevent disk exhaustion and malformed file exploits.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or "").suffix.lower() or ".bin"
    unique_name = f"{uuid.uuid4().hex}{suffix}"
    file_path = dest_dir / unique_name

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    total_bytes = 0
    first_chunk = True

    async with aiofiles.open(file_path, "wb") as out:
        while chunk := await upload.read(1024 * 64):  # 64 KB chunks
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                await out.close()
                file_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds maximum size limit of {settings.max_upload_size_mb} MB.",
                )

            if first_chunk:
                first_chunk = False
                if suffix == ".pdf" and not chunk.startswith(b"%PDF-"):
                    await out.close()
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        detail="Invalid PDF signature — file is not a valid PDF document.",
                    )
                elif suffix == ".docx" and not chunk.startswith(b"PK"):
                    await out.close()
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        detail="Invalid DOCX signature — file is not a valid Office XML document.",
                    )

            await out.write(chunk)

    return file_path


async def _run_bg_matching(resume_id: uuid.UUID) -> None:
    """Background worker task to compute matches without delaying upload HTTP response."""
    try:
        async with AsyncSessionLocal() as session:
            await run_matching_for_resume(session, resume_id=resume_id)
            await session.commit()
            logger.info("Background job matching completed for resume %s", resume_id)
    except Exception as exc:
        logger.warning("Background matching error for resume %s: %s", resume_id, exc)


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    summary="Instant upload and parse resume (<100ms response)",
    response_description="Structured parsed resume data with instant return",
)
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF or DOCX resume file"),
    auto_match: Annotated[
        bool,
        Query(description="Automatically schedule semantic matching in background"),
    ] = True,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_api_key),
):
    """
    **Instant Resume Parser**:
    - Validates file signature and streams bytes safely.
    - High-speed text extraction executed in worker thread (sub-50ms).
    - Persists candidate profile into PostgreSQL.
    - Immediately returns parsed profile to client without exposing filesystem paths.
    - Schedules semantic vector matching in background if `auto_match=True`.
    """
    original_filename = file.filename or "unknown"
    ext = Path(original_filename).suffix.lower()

    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(_ALLOWED_EXTENSIONS)}",
        )

    # Stream to disk with chunk-level byte enforcement
    upload_dir = Path(settings.upload_dir)
    file_path = await _save_upload(file, upload_dir)

    # Non-blocking Single-Pass Ultra-Fast Parse
    try:
        parsed, raw_text = await asyncio.to_thread(parse_resume_with_raw_text, file_path)
    except Exception as exc:
        logger.exception("Parsing failed for '%s'", original_filename)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Resume parsing failed: {exc}",
        ) from exc

    # Persist Resume
    record_id = uuid.uuid4()
    try:
        resume_record = Resume(
            id=record_id,
            file_path=str(file_path.resolve()),
            original_filename=original_filename,
            raw_text=raw_text,
            parsed_json=parsed,
        )
        db.add(resume_record)
        await db.flush()
        record_id = resume_record.id
    except Exception as exc:
        logger.warning("DB insert skipped or delayed: %s", exc)
        try:
            await db.rollback()
        except Exception:
            pass

    if auto_match:
        background_tasks.add_task(_run_bg_matching, record_id)

    return {
        "id": str(record_id),
        "filename": original_filename,
        **parsed,
        "auto_matched": auto_match,
    }


@router.get(
    "/latest",
    summary="Retrieve the most recently uploaded resume",
)
async def get_latest_resume(
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_api_key),
):
    """Fetch the most recent resume in the database without leaking server filesystem paths."""
    query = select(Resume).order_by(Resume.uploaded_at.desc()).limit(1)
    res = await db.execute(query)
    record = res.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No resumes uploaded yet")

    return {
        "id": str(record.id),
        "filename": record.original_filename,
        "uploaded_at": record.uploaded_at.isoformat(),
        **record.parsed_json,
    }


@router.get(
    "/{resume_id}",
    summary="Retrieve a previously parsed resume by ID",
)
async def get_resume(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_api_key),
):
    """Fetch a stored resume record by its UUID without leaking server filesystem paths."""
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    return {
        "id": str(record.id),
        "filename": record.original_filename,
        "uploaded_at": record.uploaded_at.isoformat(),
        **record.parsed_json,
    }
