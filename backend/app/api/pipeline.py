"""
Pipeline Automation & Trigger API
=================================
  POST /api/pipeline/run/{resume_id} — execute full autonomous cycle (ingest -> match -> apply)
  GET  /api/pipeline/runs            — list historical pipeline execution runs
"""
from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.models.pipeline_run import PipelineRun
from app.models.resume import Resume
from app.scheduler.pipeline import run_full_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/pipeline", tags=["Pipeline"])


def verify_pipeline_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    """
    Validates API key for scheduled/remote triggers.
    If PIPELINE_API_KEY is configured in settings/env, requires exact match.
    """
    expected_key = settings.pipeline_api_key.strip()
    if expected_key:
        if not x_api_key or x_api_key != expected_key:
            logger.warning("Unauthorized pipeline trigger attempt (invalid X-API-Key).")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized: Invalid or missing X-API-Key header.",
                headers={"WWW-Authenticate": "ApiKey"},
            )


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/pipeline/run/{resume_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/run/{resume_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_pipeline_api_key)],
    summary="Trigger the complete autonomous pipeline (Ingest -> Match -> Apply)",
    response_description="Detailed pipeline run execution summary",
)
async def trigger_full_pipeline(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    min_score: Annotated[
        float,
        Query(ge=0.0, le=1.0, description="Minimum match score threshold for applying (default 0.6)"),
    ] = 0.6,
    limit: Annotated[
        int,
        Query(ge=1, le=50, description="Maximum applications to attempt in this run"),
    ] = 10,
):
    """
    Executes the end-to-end cycle:
    1. **Ingestion**: Fetches fresh postings from configured ATS boards (Greenhouse + Lever).
    2. **Matching**: Computes dense sentence embeddings and evaluates skill gap.
    3. **Application**: Submits qualifying ATS applications & captures portal screenshots.
    4. **Audit**: Persists execution metrics in `pipeline_runs` table.
    """
    # Verify resume exists
    resume_res = await db.execute(select(Resume).where(Resume.id == resume_id))
    if resume_res.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume with ID '{resume_id}' not found.",
        )

    try:
        run_record = await run_full_pipeline(
            db=db,
            resume_id=resume_id,
            min_score=min_score,
            limit=limit,
        )
        return _pipeline_run_to_dict(run_record)
    except Exception as exc:
        logger.exception("Pipeline trigger failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution error: {exc}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/pipeline/runs
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/runs",
    summary="List recent pipeline execution runs with metrics and diagnostics",
)
async def list_pipeline_runs(
    db: AsyncSession = Depends(get_db),
    resume_id: Annotated[uuid.UUID | None, Query(description="Filter by specific resume ID")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """
    List historical pipeline runs with status breakdown and error logs.
    """
    query = select(PipelineRun)
    if resume_id:
        query = query.where(PipelineRun.resume_id == resume_id)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    data_q = query.order_by(PipelineRun.started_at.desc()).offset(offset).limit(limit)
    runs = (await db.execute(data_q)).scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [_pipeline_run_to_dict(r) for r in runs],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helper Serialiser
# ─────────────────────────────────────────────────────────────────────────────

def _pipeline_run_to_dict(run: PipelineRun) -> dict:
    duration_s = (
        (run.finished_at - run.started_at).total_seconds()
        if run.finished_at and run.started_at
        else None
    )
    return {
        "id": str(run.id),
        "resume_id": str(run.resume_id),
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "duration_seconds": round(duration_s, 2) if duration_s is not None else None,
        "jobs_fetched": run.jobs_fetched,
        "matches_computed": run.matches_computed,
        "applications_submitted": run.applications_submitted,
        "applications_pending": run.applications_pending,
        "errors": run.errors or [],
    }
