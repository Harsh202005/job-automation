"""
Authentication dependency for securing API routes.
Supports X-API-Key header authentication with optional development bypass.
"""
from __future__ import annotations

from fastapi import Header, HTTPException, status
from app.core.config import settings


async def verify_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key")
) -> bool:
    """
    Validate API key from X-API-Key header.
    If API_KEY or PIPELINE_API_KEY is configured, enforces authentication.
    If neither is configured, allows request (for local dev mode).
    """
    valid_key = settings.pipeline_api_key or getattr(settings, "api_key", "")
    if not valid_key:
        return True  # Dev / open mode

    if not x_api_key or x_api_key != valid_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return True
