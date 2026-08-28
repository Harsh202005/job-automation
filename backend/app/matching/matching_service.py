"""
Matching Service
================
Computes semantic similarity between a resume and job postings using
sentence-transformer embeddings, combined with keyword-based skill gap analysis.

Two-signal scoring:
  1. Semantic score   — cosine similarity of (resume_profile_text, job_description)
  2. Skill gap report — which resume skills appear in the job text and which don't

The final `score` returned is the semantic cosine similarity (0–1). The skill
gap signals are surfaced separately as `matched_skills` / `missing_skills`.
"""
from __future__ import annotations

import asyncio
import logging
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.matching.embedding_service import cosine_similarity, get_embedding
from app.models.job import Job
from app.models.match import Match
from app.models.resume import Resume

logger = logging.getLogger(__name__)

# Thread pool used to run blocking embedding calls off the async event loop
_EMBED_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="embed")

# Common tech buzzwords to look for in job descriptions when the resume
# skills list is sparse. Treated as supplemental skill candidates.
_COMMON_TECH_KEYWORDS: list[str] = [
    "python", "javascript", "typescript", "java", "go", "rust", "c++", "c#",
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "docker", "kubernetes", "aws", "gcp", "azure", "terraform",
    "react", "vue", "angular", "node", "fastapi", "django", "flask",
    "spark", "kafka", "airflow", "dbt", "pandas", "scikit-learn",
    "pytorch", "tensorflow", "git", "linux", "rest", "graphql",
]


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_resume_profile_text(parsed_json: dict[str, Any]) -> str:
    """
    Concatenate the most signal-rich parts of the parsed resume into a single
    text block for embedding:
      - Skills list
      - All experience descriptions + titles + companies
      - Education degrees + institutions
    """
    parts: list[str] = []

    # Skills
    skills: list[str] = parsed_json.get("skills", []) or []
    if skills:
        parts.append("Skills: " + ", ".join(skills))

    # Experience
    for exp in parsed_json.get("experience", []) or []:
        fragments = [
            exp.get("title", ""),
            exp.get("company", ""),
            exp.get("duration", ""),
            exp.get("description", ""),
        ]
        line = " | ".join(f for f in fragments if f)
        if line:
            parts.append(line)

    # Education
    for edu in parsed_json.get("education", []) or []:
        fragments = [edu.get("degree", ""), edu.get("institution", "")]
        line = " | ".join(f for f in fragments if f)
        if line:
            parts.append(line)

    return "\n".join(parts)


def _word_boundary_pattern(skill: str) -> re.Pattern:
    """Return a compiled regex for whole-word (or phrase) skill matching."""
    escaped = re.escape(skill.lower())
    return re.compile(r"(?<!\w)" + escaped + r"(?!\w)")


def _compute_skill_overlap(
    resume_skills: list[str],
    job_description: str,
) -> tuple[list[str], list[str]]:
    """
    Case-insensitive substring / word-boundary match of resume skills against
    the job description text.

    Also performs a reverse pass: scan `_COMMON_TECH_KEYWORDS` in the job
    description to identify skills mentioned there that are absent from the
    resume, surfacing them as `missing_skills`.

    Returns
    -------
    (matched_skills, missing_skills)
    """
    job_text_lower = job_description.lower()

    # ── Forward pass: which resume skills appear in the job text? ────────────
    matched: list[str] = []
    unmatched: list[str] = []

    for skill in resume_skills:
        if not skill:
            continue
        pattern = _word_boundary_pattern(skill)
        if pattern.search(job_text_lower):
            matched.append(skill)
        else:
            unmatched.append(skill)

    # ── Reverse pass: common tech keywords in JD but absent from resume ──────
    resume_skills_lower = {s.lower() for s in resume_skills}
    missing: list[str] = []

    for keyword in _COMMON_TECH_KEYWORDS:
        if keyword in job_text_lower and keyword not in resume_skills_lower:
            missing.append(keyword)

    return matched, missing


async def _embed_async(text: str) -> list[float]:
    """Run get_embedding() in the thread pool so it doesn't block the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_EMBED_EXECUTOR, get_embedding, text)


# ─────────────────────────────────────────────────────────────────────────────
# Public: single-job match computation
# ─────────────────────────────────────────────────────────────────────────────

async def compute_match(
    resume_parsed_json: dict[str, Any],
    job: Job,
) -> dict[str, Any]:
    """
    Compute a match between one resume and one job posting.

    Parameters
    ----------
    resume_parsed_json : dict
        The `parsed_json` dict from a `Resume` record.
    job : Job
        The `Job` ORM record to match against.

    Returns
    -------
    dict
        {
            "score": float,            # cosine similarity, 0–1
            "matched_skills": [str],   # resume skills found in JD
            "missing_skills": [str],   # JD keywords absent from resume
        }
    """
    # Build texts
    profile_text = _build_resume_profile_text(resume_parsed_json)
    job_text = (job.description or "") + " " + (job.title or "")

    # Embed both concurrently — they're independent operations
    resume_vec, job_vec = await asyncio.gather(
        _embed_async(profile_text),
        _embed_async(job_text),
    )

    score = cosine_similarity(resume_vec, job_vec)

    resume_skills: list[str] = resume_parsed_json.get("skills", []) or []
    matched, missing = _compute_skill_overlap(resume_skills, job.description or "")

    return {
        "score": round(score, 6),
        "matched_skills": matched,
        "missing_skills": missing,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public: batch match for a whole resume
# ─────────────────────────────────────────────────────────────────────────────

async def run_matching_for_resume(
    db: AsyncSession,
    resume_id: uuid.UUID,
    job_limit: int | None = None,
) -> dict[str, Any]:
    """
    Score all (or up to `job_limit`) jobs against a resume and upsert results.

    Parameters
    ----------
    db : AsyncSession
    resume_id : UUID
    job_limit : int | None
        Cap the number of jobs processed (useful for large job tables during dev).
        Defaults to None (all jobs).

    Returns
    -------
    dict
        {
            "total_jobs": int,
            "matches_computed": int,
            "top_score": float,
            "errors": list[str],
        }
    """
    errors: list[str] = []

    # ── 1. Fetch the resume ───────────────────────────────────────────────────
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if resume is None:
        raise ValueError(f"Resume {resume_id} not found.")

    parsed_json: dict = resume.parsed_json or {}
    if not parsed_json:
        raise ValueError(f"Resume {resume_id} has no parsed_json — run the parser first.")

    # ── 2. Fetch jobs ─────────────────────────────────────────────────────────
    jobs_query = select(Job)
    if job_limit:
        jobs_query = jobs_query.limit(job_limit)

    jobs_result = await db.execute(jobs_query)
    jobs: list[Job] = list(jobs_result.scalars().all())

    if not jobs:
        logger.warning("No jobs in the database — ingest some first.")
        return {"total_jobs": 0, "matches_computed": 0, "top_score": 0.0, "errors": []}

    logger.info(
        "Computing matches for resume_id=%s against %d jobs …", resume_id, len(jobs)
    )

    # ── 3. Compute matches ────────────────────────────────────────────────────
    # Pre-embed the resume profile once, then reuse it for every job to avoid
    # redundant computation.
    profile_text = _build_resume_profile_text(parsed_json)
    resume_vec = await _embed_async(profile_text)

    now = datetime.now(timezone.utc)
    upsert_rows: list[dict[str, Any]] = []
    top_score = 0.0

    for job in jobs:
        try:
            job_text = (job.description or "") + " " + (job.title or "")
            job_vec = await _embed_async(job_text)

            score = cosine_similarity(resume_vec, job_vec)
            score = round(score, 6)

            resume_skills: list[str] = parsed_json.get("skills", []) or []
            matched, missing = _compute_skill_overlap(resume_skills, job.description or "")

            if score > top_score:
                top_score = score

            upsert_rows.append(
                {
                    "resume_id": resume_id,
                    "job_id": job.id,
                    "score": score,
                    "matched_skills": matched,
                    "missing_skills": missing,
                    "computed_at": now,
                }
            )
        except Exception as exc:
            msg = f"Failed to compute match for job {job.id}: {exc}"
            logger.exception(msg)
            errors.append(msg)

    # ── 4. Batch upsert ───────────────────────────────────────────────────────
    matches_saved = 0
    if upsert_rows:
        try:
            stmt = pg_insert(Match).values(upsert_rows)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_matches_resume_job",
                set_={
                    "score": stmt.excluded.score,
                    "matched_skills": stmt.excluded.matched_skills,
                    "missing_skills": stmt.excluded.missing_skills,
                    "computed_at": stmt.excluded.computed_at,
                },
            )
            await db.execute(stmt)
            matches_saved = len(upsert_rows)
            logger.info("Upserted %d match records.", matches_saved)
        except Exception as exc:
            msg = f"DB upsert error: {exc}"
            logger.exception(msg)
            errors.append(msg)
            await db.rollback()

    return {
        "total_jobs": len(jobs),
        "matches_computed": matches_saved,
        "top_score": round(top_score, 6),
        "errors": errors,
    }
