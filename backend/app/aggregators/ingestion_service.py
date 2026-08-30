"""
Ingestion service — coordinates fetching from all configured ATS and Job Board sources
and upserts results into the `jobs` table.

Supported Sources:
- Greenhouse (Public ATS API)
- Lever (Public ATS API)
- Arbeitnow (Free Public Job Board API)
- RemoteOK (Free Public Remote Jobs API)
- Adzuna (Free Developer Job API)
- LinkedIn (Best-effort unauthenticated scraper)
- Naukri (Best-effort unauthenticated scraper)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.aggregators.adzuna import fetch_adzuna_jobs
from app.aggregators.arbeitnow import fetch_arbeitnow_jobs
from app.aggregators.greenhouse import fetch_greenhouse_jobs
from app.aggregators.lever import fetch_lever_jobs
from app.aggregators.linkedin_scraper import scrape_linkedin_jobs
from app.aggregators.naukri_scraper import scrape_naukri_jobs
from app.aggregators.remoteok import fetch_remoteok_jobs
from app.core.config import settings
from app.models.job import Job

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _upsert_jobs(
    db: AsyncSession,
    jobs: list[dict[str, Any]],
    errors: list[str],
) -> tuple[int, int]:
    """
    Upsert a batch of normalised job dicts.

    Returns (new_count, updated_count).
    Uses PostgreSQL's INSERT ... ON CONFLICT DO UPDATE so the whole operation
    is a single round-trip per batch.
    """
    if not jobs:
        return 0, 0

    now = datetime.now(timezone.utc)

    # Stamp fetched_at on every record
    for j in jobs:
        j["fetched_at"] = now

    # Build the upsert statement
    stmt = pg_insert(Job).values(jobs)

    # On conflict: update all mutable fields
    stmt = stmt.on_conflict_do_update(
        constraint="uq_jobs_source_source_job_id",
        set_={
            "title": stmt.excluded.title,
            "company": stmt.excluded.company,
            "location": stmt.excluded.location,
            "description": stmt.excluded.description,
            "apply_url": stmt.excluded.apply_url,
            "posted_at": stmt.excluded.posted_at,
            "fetched_at": stmt.excluded.fetched_at,
            "raw_json": stmt.excluded.raw_json,
        },
    ).returning(Job.id)

    try:
        result = await db.execute(stmt)
        returned_ids = result.scalars().all()

        source_ids = {j["source_job_id"] for j in jobs}
        sources = {j["source"] for j in jobs}

        # Query which of those IDs existed *before* this upsert
        pre_existing = await db.execute(
            select(Job.source_job_id).where(
                Job.source.in_(sources),
                Job.source_job_id.in_(source_ids),
                Job.fetched_at < now,
            )
        )
        pre_existing_ids = set(pre_existing.scalars().all())

        new_count = sum(1 for j in jobs if j["source_job_id"] not in pre_existing_ids)
        updated_count = sum(1 for j in jobs if j["source_job_id"] in pre_existing_ids)
        return new_count, updated_count

    except Exception as exc:
        msg = f"DB upsert error: {exc}"
        logger.exception(msg)
        errors.append(msg)
        await db.rollback()
        return 0, 0


# ─────────────────────────────────────────────────────────────────────────────
# Public APIs
# ─────────────────────────────────────────────────────────────────────────────

async def run_ingestion(db: AsyncSession) -> dict[str, Any]:
    """
    Fetch jobs from all stable ATS and public Job APIs:
    - Greenhouse (configured tokens)
    - Lever (configured slugs)
    - Arbeitnow (open API)
    - RemoteOK (open API)
    - Adzuna (if app_id/app_key are configured)

    Returns
    -------
    dict
        {
            "fetched": int,
            "new": int,
            "updated": int,
            "errors": list[str]
        }
    """
    errors: list[str] = []
    total_new = 0
    total_updated = 0

    gh_tokens: list[str] = settings.greenhouse_board_tokens
    lever_slugs: list[str] = settings.lever_company_slugs

    tasks: list[Any] = []
    labels: list[str] = []

    # 1. Greenhouse
    for token in gh_tokens:
        tasks.append(fetch_greenhouse_jobs(token))
        labels.append(f"greenhouse:{token}")

    # 2. Lever
    for slug in lever_slugs:
        tasks.append(fetch_lever_jobs(slug))
        labels.append(f"lever:{slug}")

    # 3. Arbeitnow (Always available free API)
    tasks.append(fetch_arbeitnow_jobs())
    labels.append("arbeitnow")

    # 4. RemoteOK (Always available free API)
    tasks.append(fetch_remoteok_jobs())
    labels.append("remoteok")

    # 5. Adzuna (if configured)
    if settings.adzuna_app_id and settings.adzuna_app_key:
        tasks.append(
            fetch_adzuna_jobs(
                query=settings.adzuna_query,
                location=settings.adzuna_location,
                app_id=settings.adzuna_app_id,
                app_key=settings.adzuna_app_key,
                country=settings.adzuna_country,
            )
        )
        labels.append("adzuna")

    all_results = await asyncio.gather(*tasks, return_exceptions=True)

    all_jobs: list[dict[str, Any]] = []
    for i, result in enumerate(all_results):
        if isinstance(result, Exception):
            msg = f"Fetch error for {labels[i]}: {result}"
            logger.error(msg)
            errors.append(msg)
        elif isinstance(result, list):
            all_jobs.extend(result)

    total_fetched = len(all_jobs)
    logger.info("Ingestion ▸ %d total jobs fetched across %d sources", total_fetched, len(tasks))

    if all_jobs:
        new_count, updated_count = await _upsert_jobs(db, all_jobs, errors)
        total_new += new_count
        total_updated += updated_count

    summary = {
        "fetched": total_fetched,
        "new": total_new,
        "updated": total_updated,
        "errors": errors,
    }
    logger.info("Ingestion complete: %s", summary)
    return summary


async def run_scraper_ingestion(
    db: AsyncSession,
    query: str | None = None,
    location: str | None = None,
    max_results: int | None = None,
) -> dict[str, Any]:
    """
    Run best-effort unauthenticated web scrapers (LinkedIn + Naukri).
    Kept separate from automated hourly cron runs due to fragility and CAPTCHA limits.

    Parameters
    ----------
    db : AsyncSession
    query : str, optional
    location : str, optional
    max_results : int, optional

    Returns
    -------
    dict
        Ingestion summary with fetched, new, updated, and errors list.
    """
    errors: list[str] = []
    total_new = 0
    total_updated = 0

    search_query = query or settings.scraper_query or "software engineer"
    search_location = location or settings.scraper_location or "pune"
    results_limit = max_results or settings.scraper_max_results or 20

    logger.info(
        "Scraper Ingestion Started ▸ Query='%s', Location='%s', MaxResults=%d",
        search_query,
        search_location,
        results_limit,
    )

    tasks = [
        scrape_linkedin_jobs(query=search_query, location=search_location, max_results=results_limit),
        scrape_naukri_jobs(query=search_query, location=search_location, max_results=results_limit),
    ]
    labels = ["linkedin_scraper", "naukri_scraper"]

    all_results = await asyncio.gather(*tasks, return_exceptions=True)

    all_jobs: list[dict[str, Any]] = []
    for i, result in enumerate(all_results):
        if isinstance(result, Exception):
            msg = f"Scraper error for {labels[i]}: {result}"
            logger.error(msg)
            errors.append(msg)
        elif isinstance(result, list):
            all_jobs.extend(result)

    total_fetched = len(all_jobs)
    logger.info("Scraper Ingestion ▸ %d total scraped jobs found", total_fetched)

    if all_jobs:
        new_count, updated_count = await _upsert_jobs(db, all_jobs, errors)
        total_new += new_count
        total_updated += updated_count

    summary = {
        "fetched": total_fetched,
        "new": total_new,
        "updated": total_updated,
        "errors": errors,
        "query": search_query,
        "location": search_location,
    }
    logger.info("Scraper Ingestion complete: %s", summary)
    return summary
