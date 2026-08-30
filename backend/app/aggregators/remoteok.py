"""
RemoteOK Free Public Job Board API Fetcher.
===========================================
Free public developer endpoint for global remote tech jobs.
Endpoint: https://remoteok.com/api
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_API_URL = "https://remoteok.com/api"


def _parse_remoteok_date(date_val: str | None) -> datetime | None:
    """Parse RemoteOK date string (ISO 8601 or timestamp)."""
    if not date_val:
        return None
    try:
        return datetime.fromisoformat(date_val.replace("Z", "+00:00"))
    except Exception:
        return None


def _normalise_remoteok_job(job: dict[str, Any]) -> dict[str, Any]:
    """Convert a RemoteOK job dict into our standard Job schema dict."""
    job_id = str(job.get("id") or hash(job.get("url") or job.get("position") or ""))
    company = (job.get("company") or "RemoteOK Company").strip()
    title = (job.get("position") or "").strip()
    location = (job.get("location") or "Remote (Worldwide)").strip()
    apply_url = (job.get("apply_url") or job.get("url") or f"https://remoteok.com/remote-jobs/{job_id}").strip()

    return {
        "source": "remoteok",
        "source_job_id": job_id,
        "company": company,
        "title": title,
        "location": location,
        "description": (job.get("description") or "").strip(),
        "apply_url": apply_url,
        "posted_at": _parse_remoteok_date(job.get("date")),
        "raw_json": job,
    }


async def fetch_remoteok_jobs() -> list[dict[str, Any]]:
    """
    Fetch global remote tech jobs from RemoteOK public JSON API.

    Returns
    -------
    list[dict[str, Any]]
        List of normalised job dicts.
    """
    # RemoteOK blocks default Python / httpx user-agents with HTTP 429/403
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 AutoApply/1.0",
    }

    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            resp = await client.get(_API_URL, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        if not isinstance(data, list):
            logger.warning("RemoteOK returned unexpected non-list payload: %s", type(data))
            return []

        # The first item in RemoteOK JSON response is a legal disclaimer notice — skip it
        job_items = [
            item for item in data
            if isinstance(item, dict) and item.get("position") and item.get("id")
        ]

        normalised = [_normalise_remoteok_job(j) for j in job_items]
        logger.info("RemoteOK ▸ Fetched %d remote jobs successfully", len(normalised))
        return normalised

    except Exception as exc:
        logger.error("RemoteOK API fetch error: %s", exc)
        return []
