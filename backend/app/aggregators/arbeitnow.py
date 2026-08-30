"""
Arbeitnow Free Public Job Board API Fetcher.
============================================
Free, open developer API with no authentication requirement.
Endpoint: https://www.arbeitnow.com/api/job-board-api
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_API_URL = "https://www.arbeitnow.com/api/job-board-api"


def _parse_arbeitnow_date(date_val: int | str | None) -> datetime | None:
    """Parse Arbeitnow created_at integer timestamp or ISO string."""
    if not date_val:
        return None
    try:
        if isinstance(date_val, (int, float)):
            return datetime.fromtimestamp(date_val, tz=timezone.utc)
        return datetime.fromisoformat(str(date_val).replace("Z", "+00:00"))
    except Exception:
        return None


def _normalise_arbeitnow_job(job: dict[str, Any]) -> dict[str, Any]:
    """Convert an Arbeitnow job dict into our standard Job schema dict."""
    slug = job.get("slug") or str(hash(job.get("url") or job.get("title") or ""))
    location = job.get("location") or ("Remote" if job.get("remote") else "Worldwide")

    return {
        "source": "arbeitnow",
        "source_job_id": str(slug),
        "company": (job.get("company_name") or "Arbeitnow Employer").strip(),
        "title": (job.get("title") or "").strip(),
        "location": str(location).strip(),
        "description": (job.get("description") or "").strip(),
        "apply_url": (job.get("url") or "").strip(),
        "posted_at": _parse_arbeitnow_date(job.get("created_at")),
        "raw_json": job,
    }


async def fetch_arbeitnow_jobs(page: int = 1) -> list[dict[str, Any]]:
    """
    Fetch open jobs from Arbeitnow public JSON API.

    Parameters
    ----------
    page : int
        Results page (default 1).

    Returns
    -------
    list[dict[str, Any]]
        List of normalised job dicts.
    """
    headers = {
        "Accept": "application/json",
        "User-Agent": "AutoApply/1.0 (Job Aggregator; +https://github.com/Harsh202005/job-automation)",
    }

    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            resp = await client.get(_API_URL, params={"page": page}, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        raw_items = data.get("data") or []
        normalised = [_normalise_arbeitnow_job(j) for j in raw_items if j.get("title")]
        logger.info("Arbeitnow ▸ Fetched %d jobs successfully", len(normalised))
        return normalised

    except Exception as exc:
        logger.error("Arbeitnow API fetch error: %s", exc)
        return []
