"""
Greenhouse public board API fetcher.

Public endpoint (no auth required):
  GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true

Each job is normalised into a flat dict that maps directly to the Job ORM model.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


def _parse_gh_date(date_str: str | None) -> datetime | None:
    """Parse Greenhouse ISO-8601 date strings; return None if blank/invalid."""
    if not date_str:
        return None
    try:
        # Greenhouse uses format: "2024-01-15T10:00:00.000Z"
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return None


def _extract_location(job: dict[str, Any]) -> str:
    """Pull the display location string from a Greenhouse job object."""
    loc = job.get("location") or {}
    if isinstance(loc, dict):
        return loc.get("name", "") or ""
    return str(loc)


def _normalise(job: dict[str, Any], board_token: str) -> dict[str, Any]:
    """
    Convert a single Greenhouse API job object into our normalised schema.

    Returns a dict with keys matching the Job ORM model fields
    (except `id` and `fetched_at` which are set at write time).
    """
    return {
        "source": "greenhouse",
        "source_job_id": str(job.get("id", "")),
        "company": board_token,  # Greenhouse doesn't include company name in job objects
        "title": (job.get("title") or "").strip(),
        "location": _extract_location(job),
        "description": (job.get("content") or "").strip(),
        "apply_url": (job.get("absolute_url") or "").strip(),
        "posted_at": _parse_gh_date(job.get("updated_at")),
        "raw_json": job,
    }


async def fetch_greenhouse_jobs(board_token: str) -> list[dict[str, Any]]:
    """
    Fetch all open jobs from a Greenhouse board.

    Parameters
    ----------
    board_token : str
        The Greenhouse board token (e.g. "stripe", "airbnb").

    Returns
    -------
    list[dict]
        Normalised job dicts ready for upsert, or an empty list on error.
    """
    url = _BASE_URL.format(token=board_token)
    logger.info("Greenhouse ▸ fetching board_token=%r from %s", board_token, url)

    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            response = await client.get(url, params={"content": "true"})
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Greenhouse HTTP error for board_token=%r: %s %s",
            board_token,
            exc.response.status_code,
            exc.response.text[:200],
        )
        return []
    except httpx.RequestError as exc:
        logger.error("Greenhouse request error for board_token=%r: %s", board_token, exc)
        return []
    except Exception as exc:
        logger.exception("Unexpected error fetching Greenhouse board_token=%r: %s", board_token, exc)
        return []

    jobs_raw: list[dict] = data.get("jobs", [])
    logger.info("Greenhouse ▸ board_token=%r returned %d jobs", board_token, len(jobs_raw))

    normalised: list[dict[str, Any]] = []
    for job in jobs_raw:
        try:
            normalised.append(_normalise(job, board_token))
        except Exception as exc:
            logger.warning("Greenhouse ▸ failed to normalise job id=%s: %s", job.get("id"), exc)

    return normalised
