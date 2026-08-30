"""
Application configuration — reads from environment variables / .env file.
"""
from __future__ import annotations

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(v: str | list[str]) -> list[str]:
    """Parse a comma-separated string into a list, stripping whitespace."""
    if isinstance(v, list):
        return [item.strip() for item in v if item.strip()]
    return [item.strip() for item in v.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────────────
    app_name: str = "JobAutomate"
    debug: bool = False

    # ── Database ─────────────────────────────────────────────────
    # Example: postgresql+asyncpg://user:password@localhost:5432/jobautomate
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/jobautomate"

    # ── File Storage ─────────────────────────────────────────────
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 10

    # ── Job Aggregators: ATS ─────────────────────────────────────
    # Comma-separated list of Greenhouse board tokens, e.g.:
    #   GREENHOUSE_BOARD_TOKENS=stripe,airbnb,notion
    greenhouse_board_tokens: list[str] = []

    # Comma-separated list of Lever company slugs, e.g.:
    #   LEVER_COMPANY_SLUGS=netflix,linear,vercel
    lever_company_slugs: list[str] = []

    # ── Job Aggregators: Adzuna API ──────────────────────────────
    # Free developer API keys from https://developer.adzuna.com/
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = "in"
    adzuna_query: str = "software engineer"
    adzuna_location: str = "pune"

    # ── Job Aggregators: Best-Effort Scrapers ────────────────────
    scraper_query: str = "software engineer"
    scraper_location: str = "pune"
    scraper_max_results: int = 20

    # Timeout (seconds) for outbound HTTP requests to ATS APIs
    http_timeout_seconds: float = 15.0

    # ── Pipeline & Security ────────────────────────────────────────
    # API key required to trigger automated pipeline execution via cron
    pipeline_api_key: str = ""

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            import re
            # Render / Heroku / Supabase default scheme conversion
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
            # asyncpg doesn't support 'sslmode' query param — remove it to prevent connection hangs
            if "sslmode=" in v:
                v = re.sub(r"[?&]sslmode=[^&]*", "", v)
                if "?" not in v and "&" in v:
                    v = v.replace("&", "?", 1)
        return v

    @field_validator("greenhouse_board_tokens", "lever_company_slugs", mode="before")
    @classmethod
    def parse_csv_list(cls, v: str | list[str]) -> list[str]:
        return _split_csv(v)


settings = Settings()
