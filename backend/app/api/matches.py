"""
Matches API

  POST /api/matches/compute/{resume_id}  — trigger match computation for a resume
  GET  /api/matches/{resume_id}          — ranked match list with job details
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.matching.matching_service import compute_match, run_matching_for_resume
from app.models.job import Job
from app.models.match import Match
from app.models.resume import Resume

router = APIRouter(prefix="/api/matches", tags=["Matches"])


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/matches/compute/{resume_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/compute/{resume_id}",
    status_code=status.HTTP_200_OK,
    summary="Compute / refresh match scores for a resume against all ingested jobs",
    response_description="Summary of match computation",
)
async def compute_matches(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    job_limit: Annotated[
        int | None,
        Query(
            ge=1,
            le=10_000,
            description="Optionally cap how many jobs are scored (useful for testing).",
        ),
    ] = None,
):
    """
    Runs the matching engine for the specified resume:

    1. Loads the resume's `parsed_json`
    2. Embeds the resume profile text with **all-MiniLM-L6-v2** (local CPU inference)
    3. Embeds every job description and computes cosine similarity
    4. Performs keyword skill-gap analysis (matched / missing skills)
    5. Upserts all scores into the `matches` table

    > **Note:** First call will download the ~90 MB model weights from HuggingFace
    > Hub if not already cached. Subsequent calls use the in-process singleton.
    """
    try:
        summary = await run_matching_for_resume(db, resume_id, job_limit=job_limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Matching failed: {exc}",
        )
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/matches/{resume_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{resume_id}",
    summary="Ranked list of job matches for a resume",
    response_description="Matches sorted by score descending, with job details embedded",
)
async def get_matches(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    min_score: Annotated[
        float,
        Query(ge=0.0, le=1.0, description="Minimum cosine similarity score (0–1)"),
    ] = 0.0,
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """
    Returns matches for *resume_id*, ranked by score descending.

    Each result embeds the full job record so you can render the match list
    without a second request.

    Use `min_score` to filter out low-relevance results (e.g. `min_score=0.4`
    returns only matches with ≥40% semantic similarity).
    """
    # Verify resume exists
    resume_result = await db.execute(
        select(Resume).where(Resume.id == resume_id)
    )
    if resume_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume {resume_id} not found.",
        )

    # Count total matching rows (for pagination metadata)
    from sqlalchemy import func  # noqa: PLC0415

    count_q = (
        select(func.count())
        .select_from(Match)
        .where(Match.resume_id == resume_id, Match.score >= min_score)
    )
    total_result = await db.execute(count_q)
    total = total_result.scalar_one()

    # Fetch matches with joined Job data
    matches_q = (
        select(Match)
        .options(selectinload(Match.job))
        .where(Match.resume_id == resume_id, Match.score >= min_score)
        .order_by(Match.score.desc())
        .offset(offset)
        .limit(limit)
    )
    matches_result = await db.execute(matches_q)
    matches: list[Match] = list(matches_result.scalars().all())

    return {
        "resume_id": str(resume_id),
        "total": total,
        "limit": limit,
        "offset": offset,
        "min_score": min_score,
        "results": [_match_to_dict(m) for m in matches],
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/matches/{resume_id}/job/{job_id}  — single match detail
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{resume_id}/job/{job_id}",
    summary="Retrieve a single match record with full skill gap detail",
)
async def get_single_match(
    resume_id: uuid.UUID,
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Match)
        .options(selectinload(Match.job))
        .where(Match.resume_id == resume_id, Match.job_id == job_id)
    )
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match record not found — run /compute first.",
        )
    return _match_to_dict(match, include_full_description=True)


# ─────────────────────────────────────────────────────────────────────────────
# Serialiser
# ─────────────────────────────────────────────────────────────────────────────

def _match_to_dict(match: Match, include_full_description: bool = False) -> dict:
    job: Job | None = match.job
    job_data: dict = {}
    if job:
        job_data = {
            "id": str(job.id),
            "source": job.source,
            "company": job.company,
            "title": job.title,
            "location": job.location,
            "apply_url": job.apply_url,
            "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        }
        if include_full_description:
            job_data["description"] = job.description

    return {
        "match_id": str(match.id),
        "resume_id": str(match.resume_id),
        "score": match.score,
        "matched_skills": match.matched_skills,
        "missing_skills": match.missing_skills,
        "computed_at": match.computed_at.isoformat(),
        "job": job_data,
    }
