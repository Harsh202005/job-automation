"""
Alembic async environment configuration.

Uses SQLAlchemy async engine so migrations run against asyncpg (same driver as the app).
The DATABASE_URL is read from app.core.config so it always matches the running app.
"""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# ── Import all models so their metadata is populated ────────────────────────
# This import MUST happen before `target_metadata` is referenced.
import app.models  # noqa: F401 — triggers Job + Resume model registration

from app.core.config import settings
from app.core.db import Base

# ── Alembic Config object ────────────────────────────────────────────────────
config = context.config

# Override the sqlalchemy.url from our settings (honours .env)
config.set_main_option("sqlalchemy.url", settings.database_url)

# Set up Python logging from alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata object that Alembic will use to compare against the DB
target_metadata = Base.metadata


# ─────────────────────────────────────────────────────────────────────────────
# Offline mode (generates SQL without connecting to DB)
# ─────────────────────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ─────────────────────────────────────────────────────────────────────────────
# Online mode (connects to the actual database)
# ─────────────────────────────────────────────────────────────────────────────
def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations within a connection context."""
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ── Entry point ──────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
