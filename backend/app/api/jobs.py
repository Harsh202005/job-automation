"""
Jobs API

  POST /api/jobs/ingest  — trigger ingestion from all configured ATS sources
  GET  /api/jobs         — list jobs with pagination + optional filters
  GET  /api/jobs/{id}    — retrieve a single job by UUID
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.aggregators.ingestion_service import run_ingestion
from app.core.auth import verify_api_key
from app.core.db import get_db
from app.models.job import Job

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/jobs/ingest
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/ingest",
    status_code=status.HTTP_200_OK,
    summary="Trigger job ingestion from all configured ATS sources",
    response_description="Ingestion summary with counts and any non-fatal errors",
)
async def ingest_jobs(
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_api_key),
):
    """
    Pulls job postings from all **Greenhouse** board tokens and **Lever** company
    slugs defined in the environment (`GREENHOUSE_BOARD_TOKENS`, `LEVER_COMPANY_SLUGS`),
    then upserts them into the database.

    Returns a summary:
    ```json
    {
      "fetched": 42,
      "new": 30,
      "updated": 12,
      "errors": []
    }
    ```
    """
    summary = await run_ingestion(db)
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/jobs
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "",
    summary="List jobs with optional filters and pagination",
)
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=200, description="Results per page")] = 20,
    offset: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    company: Annotated[str | None, Query(description="Filter by company name (case-insensitive, partial match)")] = None,
    title: Annotated[str | None, Query(description="Filter by job title (case-insensitive, partial match)")] = None,
    location: Annotated[str | None, Query(description="Filter by location (case-insensitive, partial match)")] = None,
    source: Annotated[str | None, Query(description="Filter by source: 'greenhouse' | 'lever' | 'manual'")] = None,
):
    """
    Returns a paginated list of job postings.

    All filter parameters are **case-insensitive partial matches** (ILIKE).
    """
    # ── Build query ───────────────────────────────────────────────────────────
    query = select(Job)

    if company:
        query = query.where(Job.company.ilike(f"%{company}%"))
    if title:
        query = query.where(Job.title.ilike(f"%{title}%"))
    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))
    if source:
        query = query.where(Job.source == source.lower())

    # Total count (for pagination metadata)
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Paginated data
    data_query = query.order_by(Job.fetched_at.desc()).offset(offset).limit(limit)
    result = await db.execute(data_query)
    jobs = result.scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [_job_to_dict(j) for j in jobs],
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/jobs/{id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{job_id}",
    summary="Retrieve a single job posting by UUID",
)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _job_to_dict(job, include_raw=True)


# ─────────────────────────────────────────────────────────────────────────────
# Serialiser helper
# ─────────────────────────────────────────────────────────────────────────────

def _job_to_dict(job: Job, include_raw: bool = False) -> dict:
    data = {
        "id": str(job.id),
        "source": job.source,
        "source_job_id": job.source_job_id,
        "company": job.company,
        "title": job.title,
        "location": job.location,
        "description": job.description,
        "apply_url": job.apply_url,
        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        "fetched_at": job.fetched_at.isoformat(),
    }
    if include_raw:
        data["raw_json"] = job.raw_json
    return data
