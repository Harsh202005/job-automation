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
from datetime import datetime, timezone
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.matching.embedding_service import cosine_similarity, get_embedding, get_embeddings_batch
from app.models.job import Job
from app.models.match import Match
from app.models.resume import Resume

logger = logging.getLogger(__name__)

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
    """Concatenate signal-rich parts of the parsed resume."""
    parts: list[str] = []

    skills: list[str] = parsed_json.get("skills", []) or []
    if skills:
        parts.append("Skills: " + ", ".join(skills))

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

    for edu in parsed_json.get("education", []) or []:
        fragments = [edu.get("degree", ""), edu.get("institution", "")]
        line = " | ".join(f for f in fragments if f)
        if line:
            parts.append(line)

    return "\n".join(parts)


def _compute_skill_overlap(
    resume_skills: list[str],
    job_description: str,
) -> tuple[list[str], list[str]]:
    """Case-insensitive skill matching and missing skill gap analysis."""
    job_text_lower = job_description.lower()

    matched: list[str] = []
    unmatched: list[str] = []

    for skill in resume_skills:
        if not skill:
            continue
        skill_lower = skill.strip().lower()
        if re.search(r"(?<!\w)" + re.escape(skill_lower) + r"(?!\w)", job_text_lower):
            matched.append(skill.strip())
        else:
            unmatched.append(skill.strip())

    missing: list[str] = []
    resume_skills_lower = {s.lower() for s in resume_skills}
    for keyword in _COMMON_TECH_KEYWORDS:
        if keyword in resume_skills_lower:
            continue
        if re.search(r"(?<!\w)" + re.escape(keyword) + r"(?!\w)", job_text_lower):
            missing.append(keyword)

    return matched, missing


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def compute_match(
    resume_parsed_json: dict[str, Any],
    job: Job,
) -> dict[str, Any]:
    """Compute a match between one resume and one job posting."""
    profile_text = _build_resume_profile_text(resume_parsed_json)
    job_text = (job.description or "") + " " + (job.title or "")

    vectors = await asyncio.to_thread(get_embeddings_batch, [profile_text, job_text])
    resume_vec, job_vec = vectors[0], vectors[1]

    score = cosine_similarity(resume_vec, job_vec)
    resume_skills: list[str] = resume_parsed_json.get("skills", []) or []
    matched, missing = _compute_skill_overlap(resume_skills, job.description or "")

    return {
        "score": round(score, 6),
        "matched_skills": matched,
        "missing_skills": missing,
    }


async def run_matching_for_resume(
    db: AsyncSession,
    resume_id: uuid.UUID,
    job_limit: int | None = None,
) -> dict[str, Any]:
    """
    High-speed vectorized match computation for all jobs in the database.
    Processes all embeddings in parallel matrix batches.
    """
    errors: list[str] = []

    # 1. Fetch resume
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if resume is None:
        raise ValueError(f"Resume {resume_id} not found.")

    parsed_json: dict = resume.parsed_json or {}
    if not parsed_json:
        raise ValueError(f"Resume {resume_id} has no parsed_json — run the parser first.")

    # 2. Fetch jobs
    jobs_query = select(Job)
    if job_limit:
        jobs_query = jobs_query.limit(job_limit)

    jobs_result = await db.execute(jobs_query)
    jobs: list[Job] = list(jobs_result.scalars().all())

    if not jobs:
        return {"total_jobs": 0, "matches_computed": 0, "top_score": 0.0, "errors": []}

    # 3. Vectorized Batch Embedding
    profile_text = _build_resume_profile_text(parsed_json)
    job_texts = [(j.description or "") + " " + (j.title or "") for j in jobs]
    all_texts = [profile_text] + job_texts

    all_vectors = await asyncio.to_thread(get_embeddings_batch, all_texts)
    resume_vec = np.array(all_vectors[0], dtype=np.float32)
    job_matrix = np.array(all_vectors[1:], dtype=np.float32)

    # Matrix cosine similarity (all jobs at once via vectorized dot product)
    scores = np.dot(job_matrix, resume_vec)
    scores = np.clip(scores, 0.0, 1.0)

    now = datetime.now(timezone.utc)
    upsert_rows: list[dict[str, Any]] = []
    resume_skills: list[str] = parsed_json.get("skills", []) or []
    top_score = float(np.max(scores)) if len(scores) > 0 else 0.0

    for i, job in enumerate(jobs):
        score = float(scores[i])
        matched, missing = _compute_skill_overlap(resume_skills, job.description or "")
        upsert_rows.append(
            {
                "resume_id": resume_id,
                "job_id": job.id,
                "score": round(score, 6),
                "matched_skills": matched,
                "missing_skills": missing,
                "computed_at": now,
            }
        )

    # 4. Batch upsert
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
