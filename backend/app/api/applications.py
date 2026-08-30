"""
Applications API

  POST /api/applications/run/{resume_id} — execute batch apply automation
  GET  /api/applications                — list applications with filters & pagination
  GET  /api/applications/{id}/screenshot — download/view application screenshot
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.apply.apply_service import run_apply_batch
from app.core.auth import verify_api_key
from app.core.db import get_db
from app.models.application import Application
from app.models.job import Job

router = APIRouter(prefix="/api/applications", tags=["Applications"])


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/applications/run/{resume_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/run/{resume_id}",
    status_code=status.HTTP_200_OK,
    summary="Trigger automated application batch for a candidate's top matches",
    response_description="Summary of submitted, pending review, and failed applications",
)
async def trigger_apply_batch(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_api_key),
    min_score: Annotated[
        float,
        Query(ge=0.0, le=1.0, description="Minimum match similarity score to apply (default: 0.5)"),
    ] = 0.5,
    limit: Annotated[
        int,
        Query(ge=1, le=50, description="Max number of applications to process in batch"),
    ] = 10,
):
    """
    Launches browser automation using Playwright:
    - **Greenhouse / Lever ATS**: Automatically fills form fields, uploads candidate resume, and submits.
    - **LinkedIn / Indeed / Naukri / Other**: Pre-fills fields, captures a full-page screenshot, and pauses in `pending_review` status for candidate safety.
    """
    try:
        summary = await run_apply_batch(db, resume_id=resume_id, min_score=min_score, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Application automation error: {exc}",
        )
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/applications
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "",
    summary="List all applications with optional status filter & pagination",
)
async def list_applications(
    db: AsyncSession = Depends(get_db),
    status_filter: Annotated[
        str | None,
        Query(alias="status", description="Filter by status: pending_review | submitted | failed | skipped"),
    ] = None,
    resume_id: Annotated[uuid.UUID | None, Query(description="Filter by specific resume ID")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """
    List applications with joined job details and status tracking.
    """
    query = select(Application).options(selectinload(Application.job))

    if status_filter:
        query = query.where(Application.status == status_filter.lower())
    if resume_id:
        query = query.where(Application.resume_id == resume_id)

    # Total count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Paginated data
    data_q = query.order_by(Application.created_at.desc()).offset(offset).limit(limit)
    apps = (await db.execute(data_q)).scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [_application_to_dict(a) for a in apps],
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/applications/{id}/screenshot
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{application_id}/screenshot",
    summary="Retrieve the screenshot for a pending review application",
    response_class=FileResponse,
)
async def get_application_screenshot(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Serves the pre-submit or diagnostic PNG screenshot captured during automation.
    """
    app_res = await db.execute(select(Application).where(Application.id == application_id))
    app_record = app_res.scalar_one_or_none()

    if app_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application record not found.")

    if not app_record.screenshot_path or not Path(app_record.screenshot_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No screenshot available for this application.",
        )

    return FileResponse(
        path=app_record.screenshot_path,
        media_type="image/png",
        filename=f"application_{application_id}.png",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helper Serialiser
# ─────────────────────────────────────────────────────────────────────────────

def _application_to_dict(app: Application) -> dict:
    job: Job | None = app.job
    return {
        "id": str(app.id),
        "resume_id": str(app.resume_id),
        "job_id": str(app.job_id),
        "status": app.status,
        "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
        "created_at": app.created_at.isoformat(),
        "has_screenshot": bool(app.screenshot_path and Path(app.screenshot_path).exists()),
        "error_message": app.error_message,
        "job": {
            "id": str(job.id),
            "company": job.company,
            "title": job.title,
            "location": job.location,
            "source": job.source,
            "apply_url": job.apply_url,
        } if job else None,
    }
