"""
Ingestion service — coordinates fetching from all configured ATS sources
and upserts results into the `jobs` table.

Upsert strategy
---------------
PostgreSQL ON CONFLICT DO UPDATE (via SQLAlchemy's insert().on_conflict_do_update).
- NEW   → INSERT
- CHANGED → UPDATE (all mutable fields + fetched_at)
- UNCHANGED → no-op (excluded by the DO UPDATE's SET clause still touches fetched_at,
  which is acceptable for idempotency)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.aggregators.greenhouse import fetch_greenhouse_jobs
from app.aggregators.lever import fetch_lever_jobs
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
        # PostgreSQL RETURNING gives back ALL affected rows (both inserts and updates).
        # To distinguish new vs updated we compare against pre-existing source_job_ids.
        source_ids = {j["source_job_id"] for j in jobs}
        sources = {j["source"] for j in jobs}

        # Query which of those IDs existed *before* this upsert
        # We do this by checking if fetched_at < now (they were inserted earlier)
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
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def run_ingestion(db: AsyncSession) -> dict[str, Any]:
    """
    Fetch jobs from all configured Greenhouse boards and Lever company boards,
    then upsert them into the database.

    Parameters
    ----------
    db : AsyncSession
        An active SQLAlchemy async session (injected by FastAPI's get_db).

    Returns
    -------
    dict
        {
            "fetched": int,   # total raw jobs pulled from APIs
            "new": int,       # rows inserted for the first time
            "updated": int,   # rows updated (already existed)
            "errors": list[str]  # non-fatal error messages
        }
    """
    errors: list[str] = []
    total_fetched = 0
    total_new = 0
    total_updated = 0

    gh_tokens: list[str] = settings.greenhouse_board_tokens
    lever_slugs: list[str] = settings.lever_company_slugs

    if not gh_tokens and not lever_slugs:
        logger.warning(
            "No sources configured. Set GREENHOUSE_BOARD_TOKENS and/or "
            "LEVER_COMPANY_SLUGS in your .env file."
        )
        errors.append(
            "No sources configured. Set GREENHOUSE_BOARD_TOKENS and/or "
            "LEVER_COMPANY_SLUGS in your .env."
        )
        return {"fetched": 0, "new": 0, "updated": 0, "errors": errors}

    # ── Fetch all sources concurrently ───────────────────────────────────────
    gh_tasks = [fetch_greenhouse_jobs(token) for token in gh_tokens]
    lever_tasks = [fetch_lever_jobs(slug) for slug in lever_slugs]

    all_results = await asyncio.gather(*gh_tasks, *lever_tasks, return_exceptions=True)

    all_jobs: list[dict[str, Any]] = []
    for i, result in enumerate(all_results):
        if isinstance(result, Exception):
            source_label = (
                f"greenhouse:{gh_tokens[i]}" if i < len(gh_tokens)
                else f"lever:{lever_slugs[i - len(gh_tokens)]}"
            )
            msg = f"Fetch error for {source_label}: {result}"
            logger.error(msg)
            errors.append(msg)
        else:
            all_jobs.extend(result)

    total_fetched = len(all_jobs)
    logger.info("Ingestion ▸ %d total jobs fetched across all sources", total_fetched)

    # ── Upsert in one batch ──────────────────────────────────────────────────
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
