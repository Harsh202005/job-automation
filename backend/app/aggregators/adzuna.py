"""
Adzuna Public Job API Fetcher.
==============================
Aggregates job listings across multiple regional boards (including Indeed).
API docs: https://developer.adzuna.com/

Endpoint:
  GET https://api.adzuna.com/v1/api/jobs/{country}/search/{page}?app_id={app_id}&app_key={app_key}&what={query}&where={location}&content-type=application/json
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"


def _parse_adzuna_date(date_str: str | None) -> datetime | None:
    """Parse Adzuna ISO-8601 date string e.g. '2024-03-01T12:00:00Z'."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return None


def _normalise_adzuna_job(job: dict[str, Any]) -> dict[str, Any]:
    """Convert an Adzuna API job result into our standard Job schema dict."""
    company_obj = job.get("company") or {}
    company_name = company_obj.get("display_name") or "Adzuna Employer"

    location_obj = job.get("location") or {}
    location_name = location_obj.get("display_name") or ""

    return {
        "source": "adzuna",
        "source_job_id": str(job.get("id") or hash(job.get("redirect_url", ""))),
        "company": company_name.strip(),
        "title": (job.get("title") or "").strip(),
        "location": location_name.strip() or "India",
        "description": (job.get("description") or "").strip(),
        "apply_url": (job.get("redirect_url") or "").strip(),
        "posted_at": _parse_adzuna_date(job.get("created")),
        "raw_json": job,
    }


async def fetch_adzuna_jobs(
    query: str = "software engineer",
    location: str = "pune",
    app_id: str = "",
    app_key: str = "",
    country: str = "in",
    page: int = 1,
) -> list[dict[str, Any]]:
    """
    Fetch job postings from the official Adzuna Job Search API.

    Parameters
    ----------
    query : str
        Search keyword (e.g. 'software engineer', 'python').
    location : str
        Target location (e.g. 'pune', 'bangalore', 'mumbai').
    app_id : str
        Adzuna developer App ID.
    app_key : str
        Adzuna developer App Key.
    country : str
        Country code (e.g. 'in' for India, 'us' for USA, 'gb' for UK).
    page : int
        Results page number (default 1).

    Returns
    -------
    list[dict[str, Any]]
        List of normalised job dicts.
    """
    if not app_id or not app_key:
        logger.info("Adzuna API credentials not configured — skipping Adzuna fetch.")
        return []

    url = _BASE_URL.format(country=country.lower(), page=page)
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": query,
        "where": location,
        "content-type": "application/json",
        "results_per_page": 50,
    }

    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        raw_results = data.get("results") or []
        normalised = [_normalise_adzuna_job(j) for j in raw_results if j.get("title")]
        logger.info(
            "Adzuna [%s / %s] ▸ Fetched %d jobs successfully",
            query,
            location,
            len(normalised),
        )
        return normalised

    except httpx.HTTPStatusError as exc:
        logger.error("Adzuna API HTTP error %s: %s", exc.response.status_code, exc.response.text)
        return []
    except Exception as exc:
        logger.error("Adzuna API unexpected fetch error: %s", exc)
        return []
