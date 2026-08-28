"""
Apply Automation Service
========================
Orchestrates Playwright browser automation to apply to matched jobs in batch.
Reuses browser instance across jobs while maintaining clean page contexts.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.apply.greenhouse_applier import GreenhouseApplier
from app.apply.lever_applier import LeverApplier
from app.apply.manual_review_applier import ManualReviewApplier
from app.models.application import Application
from app.models.job import Job
from app.models.match import Match
from app.models.resume import Resume

logger = logging.getLogger(__name__)

# Screenshot storage location: storage/screenshots/
_SCREENSHOT_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "screenshots"

# Applier singletons
_GREENHOUSE_APPLIER = GreenhouseApplier()
_LEVER_APPLIER = LeverApplier()
_MANUAL_APPLIER = ManualReviewApplier()


def _get_applier(source: str):
    """Route to appropriate applier strategy based on job source."""
    src = (source or "").lower()
    if src == "greenhouse":
        return _GREENHOUSE_APPLIER
    if src == "lever":
        return _LEVER_APPLIER
    return _MANUAL_APPLIER


async def run_apply_batch(
    db: AsyncSession,
    resume_id: uuid.UUID,
    min_score: float = 0.5,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Execute automated applications for top-matched jobs for a candidate.

    Parameters
    ----------
    db : AsyncSession
    resume_id : UUID
    min_score : float
        Minimum match score threshold (default 0.5).
    limit : int
        Max applications to process in this batch (default 10).

    Returns
    -------
    dict
        {
            "attempted": int,
            "submitted": int,
            "pending_review": int,
            "failed": int,
            "applications": list[dict],
        }
    """
    # ── 1. Fetch Resume ───────────────────────────────────────────────────────
    resume_res = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = resume_res.scalar_one_or_none()
    if resume is None:
        raise ValueError(f"Resume {resume_id} not found.")

    parsed_json = resume.parsed_json or {}
    resume_file = resume.file_path or ""

    # ── 2. Fetch Eligible Matches (not already applied) ───────────────────────
    # Subquery for job IDs already in applications table for this resume
    existing_app_q = select(Application.job_id).where(Application.resume_id == resume_id)
    existing_job_ids = (await db.execute(existing_app_q)).scalars().all()

    query = (
        select(Match)
        .options(selectinload(Match.job))
        .where(
            Match.resume_id == resume_id,
            Match.score >= min_score,
            Match.job_id.not_in(existing_job_ids) if existing_job_ids else True,
        )
        .order_by(Match.score.desc())
        .limit(limit)
    )

    matches = (await db.execute(query)).scalars().all()
    if not matches:
        logger.info("No unapplied matches with score >= %.2f for resume %s", min_score, resume_id)
        return {
            "attempted": 0,
            "submitted": 0,
            "pending_review": 0,
            "failed": 0,
            "applications": [],
        }

    logger.info("Starting apply batch for %d jobs (resume_id=%s)", len(matches), resume_id)
    _SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    summary = {
        "attempted": len(matches),
        "submitted": 0,
        "pending_review": 0,
        "failed": 0,
        "applications": [],
    }

    # ── 3. Launch Playwright Browser ──────────────────────────────────────────
    from playwright.async_api import async_playwright  # noqa: PLC0415

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        )

        for match in matches:
            job: Job = match.job
            app_id = str(uuid.uuid4())
            applier = _get_applier(job.source)

            page = await context.new_page()
            try:
                result = await applier.apply(
                    job=job,
                    resume_parsed_json=parsed_json,
                    resume_file_path=resume_file,
                    page=page,
                    screenshot_dir=_SCREENSHOT_DIR,
                    application_id=app_id,
                )
            except Exception as exc:
                logger.exception("Unexpected error during application to %s", job.apply_url)
                result = {
                    "status": "failed",
                    "screenshot_path": None,
                    "error_message": f"Unexpected execution error: {exc}",
                }
            finally:
                await page.close()

            # Record metrics
            status = result["status"]
            if status == "submitted":
                summary["submitted"] += 1
            elif status == "pending_review":
                summary["pending_review"] += 1
            else:
                summary["failed"] += 1

            # ── 4. Upsert Application Record in DB ────────────────────────────
            now = datetime.now(timezone.utc)
            app_record = Application(
                id=uuid.UUID(app_id),
                resume_id=resume_id,
                job_id=job.id,
                status=status,
                submitted_at=now if status == "submitted" else None,
                screenshot_path=result.get("screenshot_path"),
                error_message=result.get("error_message"),
                created_at=now,
            )

            # Upsert
            stmt = pg_insert(Application).values(
                id=app_record.id,
                resume_id=app_record.resume_id,
                job_id=app_record.job_id,
                status=app_record.status,
                submitted_at=app_record.submitted_at,
                screenshot_path=app_record.screenshot_path,
                error_message=app_record.error_message,
                created_at=app_record.created_at,
            ).on_conflict_do_update(
                constraint="uq_applications_resume_job",
                set_={
                    "status": app_record.status,
                    "submitted_at": app_record.submitted_at,
                    "screenshot_path": app_record.screenshot_path,
                    "error_message": app_record.error_message,
                },
            )
            await db.execute(stmt)
            await db.commit()

            summary["applications"].append(
                {
                    "application_id": app_id,
                    "job_id": str(job.id),
                    "company": job.company,
                    "title": job.title,
                    "source": job.source,
                    "status": status,
                    "error_message": result.get("error_message"),
                    "has_screenshot": bool(result.get("screenshot_path")),
                }
            )

        await context.close()
        await browser.close()

    logger.info("Apply batch finished: %s", summary)
    return summary
