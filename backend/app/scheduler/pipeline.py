"""
Automated Pipeline Scheduler
============================
Orchestrates the complete autonomous job application flow:
  1. Ingestion — fetch latest postings from Greenhouse & Lever ATS
  2. Matching — compute local sentence embeddings and score skill gaps
  3. Application — apply to top-matched jobs via Playwright automation
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.aggregators.ingestion_service import run_ingestion
from app.apply.apply_service import run_apply_batch
from app.matching.matching_service import run_matching_for_resume
from app.models.pipeline_run import PipelineRun

logger = logging.getLogger(__name__)


async def run_full_pipeline(
    db: AsyncSession,
    resume_id: uuid.UUID,
    min_score: float = 0.6,
    limit: int = 10,
) -> PipelineRun:
    """
    Executes the end-to-end job discovery, scoring, and application pipeline.

    Parameters
    ----------
    db : AsyncSession
    resume_id : UUID
        Target candidate resume ID.
    min_score : float
        Minimum match score to qualify for automated application (default 0.6).
    limit : int
        Max applications to process in this run (default 10).

    Returns
    -------
    PipelineRun
        Persisted database record with full metrics and diagnostics.
    """
    run_id = uuid.uuid4()
    started_at = datetime.now(timezone.utc)
    errors: list[dict[str, Any]] = []

    logger.info("Starting automated pipeline run %s for resume %s", run_id, resume_id)

    pipeline_run = PipelineRun(
        id=run_id,
        resume_id=resume_id,
        status="running",
        started_at=started_at,
        jobs_fetched=0,
        matches_computed=0,
        applications_submitted=0,
        applications_pending=0,
        errors=[],
    )
    db.add(pipeline_run)
    await db.commit()

    stage_successes = 0

    # ── Stage 1: Job Ingestion ───────────────────────────────────────────────
    logger.info("Pipeline [%s] Stage 1/3: Running job ingestion from ATS boards...", run_id)
    try:
        ingest_summary = await run_ingestion(db)
        pipeline_run.jobs_fetched = ingest_summary.get("fetched", 0)
        stage_successes += 1
        logger.info(
            "Pipeline [%s] Stage 1 complete: %d jobs fetched (%d new)",
            run_id,
            pipeline_run.jobs_fetched,
            ingest_summary.get("new", 0),
        )
    except Exception as exc:
        logger.exception("Pipeline [%s] Stage 1 (Ingestion) failed: %s", run_id, exc)
        errors.append({"stage": "ingestion", "error": str(exc)})

    # ── Stage 2: Resume Matching ─────────────────────────────────────────────
    logger.info("Pipeline [%s] Stage 2/3: Computing semantic matches for candidate...", run_id)
    try:
        match_summary = await run_matching_for_resume(db, resume_id=resume_id)
        pipeline_run.matches_computed = match_summary.get("matches_computed", 0)
        stage_successes += 1
        logger.info(
            "Pipeline [%s] Stage 2 complete: %d matches computed (top score: %.2f)",
            run_id,
            pipeline_run.matches_computed,
            match_summary.get("top_score", 0.0),
        )
    except Exception as exc:
        logger.exception("Pipeline [%s] Stage 2 (Matching) failed: %s", run_id, exc)
        errors.append({"stage": "matching", "error": str(exc)})

    # ── Stage 3: Apply Automation ────────────────────────────────────────────
    logger.info(
        "Pipeline [%s] Stage 3/3: Running apply automation (min_score=%.2f, limit=%d)...",
        run_id,
        min_score,
        limit,
    )
    try:
        apply_summary = await run_apply_batch(
            db,
            resume_id=resume_id,
            min_score=min_score,
            limit=limit,
        )
        pipeline_run.applications_submitted = apply_summary.get("submitted", 0)
        pipeline_run.applications_pending = apply_summary.get("pending_review", 0)
        stage_successes += 1
        logger.info(
            "Pipeline [%s] Stage 3 complete: %d submitted, %d pending review, %d failed",
            run_id,
            pipeline_run.applications_submitted,
            pipeline_run.applications_pending,
            apply_summary.get("failed", 0),
        )
    except Exception as exc:
        logger.exception("Pipeline [%s] Stage 3 (Application) failed: %s", run_id, exc)
        errors.append({"stage": "application", "error": str(exc)})

    # ── Finalize Metrics & Status ─────────────────────────────────────────────
    finished_at = datetime.now(timezone.utc)
    pipeline_run.finished_at = finished_at
    pipeline_run.errors = errors

    if stage_successes == 3 and not errors:
        pipeline_run.status = "success"
    elif stage_successes > 0:
        pipeline_run.status = "partial"
    else:
        pipeline_run.status = "failed"

    await db.commit()
    await db.refresh(pipeline_run)

    duration = (finished_at - started_at).total_seconds()
    logger.info(
        "Pipeline run %s concluded in %.1fs with status='%s'",
        run_id,
        duration,
        pipeline_run.status,
    )
    return pipeline_run
