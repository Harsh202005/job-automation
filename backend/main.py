"""
JobAutomate — FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.applications import router as applications_router
from app.api.jobs import router as jobs_router
from app.api.matches import router as matches_router
from app.api.pipeline import router as pipeline_router
from app.api.resume import router as resume_router
from app.core.config import settings
from app.core.db import engine
from app.models import Application, Job, Match, PipelineRun, Resume  # noqa: F401 — ensure ALL models are imported before create_all

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan: create tables on startup (use Alembic in production) ────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.db import Base  # noqa: PLC0415

    async with engine.begin() as conn:
        logger.info("Running create_all (dev mode — use Alembic in prod)")
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
    logger.info("Database engine disposed.")


# ── Application ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description=(
        "Open-source job-application automation tool.\n\n"
        "Modules: Resume Parser · Job Aggregator · Matching Engine · Apply Automation (Playwright)"
    ),
    version="0.4.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(resume_router)
app.include_router(jobs_router)
app.include_router(matches_router)
app.include_router(applications_router)
app.include_router(pipeline_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "app": settings.app_name}
