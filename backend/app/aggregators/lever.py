"""
Lever public postings API fetcher.

Public endpoint (no auth required):
  GET https://api.lever.co/v0/postings/{company_slug}?mode=json

Each posting is normalised into a flat dict that maps directly to the Job ORM model.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.lever.co/v0/postings/{slug}"


def _parse_lever_ts(ts: int | None) -> datetime | None:
    """Lever timestamps are Unix milliseconds; convert to UTC datetime."""
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _extract_location(posting: dict[str, Any]) -> str:
    """Pull location from categories.location or location field."""
    categories = posting.get("categories") or {}
    if isinstance(categories, dict):
        loc = categories.get("location", "") or categories.get("team", "")
        if loc:
            return loc
    return (posting.get("location") or "").strip()


def _build_description(posting: dict[str, Any]) -> str:
    """
    Lever descriptions are split into descriptionPlain, lists (bullets), etc.
    Concatenate them into a single text blob.
    """
    parts: list[str] = []

    if posting.get("descriptionPlain"):
        parts.append(posting["descriptionPlain"].strip())

    for item in posting.get("lists", []):
        if item.get("text"):
            parts.append(f"\n{item['text']}")
        for content in item.get("content", "").split("<br>"):
            clean = content.strip()
            if clean:
                parts.append(f"  • {clean}")

    if posting.get("additionalPlain"):
        parts.append(posting["additionalPlain"].strip())

    return "\n".join(parts)


def _normalise(posting: dict[str, Any], company_slug: str) -> dict[str, Any]:
    """
    Convert a single Lever posting object into our normalised schema.
    """
    return {
        "source": "lever",
        "source_job_id": posting.get("id", ""),
        "company": company_slug,
        "title": (posting.get("text") or "").strip(),
        "location": _extract_location(posting),
        "description": _build_description(posting),
        "apply_url": (posting.get("applyUrl") or posting.get("hostedUrl") or "").strip(),
        "posted_at": _parse_lever_ts(posting.get("createdAt")),
        "raw_json": posting,
    }


async def fetch_lever_jobs(company_slug: str) -> list[dict[str, Any]]:
    """
    Fetch all open postings from a Lever company board.

    Parameters
    ----------
    company_slug : str
        The Lever company slug (e.g. "netflix", "linear").

    Returns
    -------
    list[dict]
        Normalised job dicts ready for upsert, or an empty list on error.
    """
    url = _BASE_URL.format(slug=company_slug)
    logger.info("Lever ▸ fetching company_slug=%r from %s", company_slug, url)

    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            response = await client.get(url, params={"mode": "json"})
            response.raise_for_status()
            postings_raw: list[dict] = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Lever HTTP error for company_slug=%r: %s %s",
            company_slug,
            exc.response.status_code,
            exc.response.text[:200],
        )
        return []
    except httpx.RequestError as exc:
        logger.error("Lever request error for company_slug=%r: %s", company_slug, exc)
        return []
    except Exception as exc:
        logger.exception("Unexpected error fetching Lever company_slug=%r: %s", company_slug, exc)
        return []

    logger.info("Lever ▸ company_slug=%r returned %d postings", company_slug, len(postings_raw))

    normalised: list[dict[str, Any]] = []
    for posting in postings_raw:
        try:
            normalised.append(_normalise(posting, company_slug))
        except Exception as exc:
            logger.warning("Lever ▸ failed to normalise posting id=%s: %s", posting.get("id"), exc)

    return normalised
