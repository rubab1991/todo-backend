import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Get the database URL from environment variable
NEON_DB_URL = os.getenv("NEON_DB_URL", "postgresql://user:password@localhost:5432/dbname")

# Convert to asyncpg-compatible URL and remove problematic SSL parameters
if NEON_DB_URL.startswith("postgresql://"):
    # Parse the URL to handle query parameters properly
    from urllib.parse import urlparse, parse_qs, urlencode

    parsed = urlparse(NEON_DB_URL)

    # Remove sslmode and channel_binding which are not supported by asyncpg
    query_params = parse_qs(parsed.query)
    # Remove problematic parameters
    query_params.pop('sslmode', None)
    query_params.pop('channel_binding', None)

    # Reconstruct the query string without problematic parameters
    new_query = urlencode(query_params, doseq=True)

    # Create the new URL with asyncpg scheme and clean query parameters
    DATABASE_URL = f"postgresql+asyncpg://{parsed.netloc}{parsed.path}"
    if new_query:
        DATABASE_URL += f"?{new_query}"
    else:
        DATABASE_URL = f"postgresql+asyncpg://{parsed.netloc}{parsed.path}"
else:
    # If it doesn't start with postgresql://, assume it's already in the right format
    # but still clean it to be safe
    from urllib.parse import urlparse, parse_qs, urlencode

    parsed = urlparse(NEON_DB_URL)

    # Remove sslmode and channel_binding which are not supported by asyncpg
    query_params = parse_qs(parsed.query)
    # Remove problematic parameters
    query_params.pop('sslmode', None)
    query_params.pop('channel_binding', None)

    # Reconstruct the query string without problematic parameters
    new_query = urlencode(query_params, doseq=True)

    # Create the new URL with asyncpg scheme and clean query parameters
    DATABASE_URL = f"postgresql+asyncpg://{parsed.netloc}{parsed.path}"
    if new_query:
        DATABASE_URL += f"?{new_query}"
    else:
        DATABASE_URL = f"postgresql+asyncpg://{parsed.netloc}{parsed.path}"

# Async engine
async_engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    connect_args={"server_settings": {"application_name": "Todo-API-App"}}
)

# ----------------------------
# CREATE TABLES + MIGRATIONS
# ----------------------------
async def _run_column_migrations(conn):
    """
    Idempotent column migrations for Phase V.
    Adds new columns to existing tables if they don't already exist.
    """
    import logging
    from sqlalchemy import text
    log = logging.getLogger(__name__)
    migrations = [
        ("tasks", "tags",               "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS tags TEXT"),
        ("tasks", "recurring_interval", "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS recurring_interval TEXT"),
        ("tasks", "reminder_at",        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS reminder_at TEXT"),
    ]
    for table, column, sql in migrations:
        try:
            await conn.execute(text(sql))
            log.info("Migration: ensured column %s.%s exists", table, column)
        except Exception as e:
            log.warning("Migration skipped for %s.%s: %s", table, column, e)


async def create_db_and_tables():
    from .models import Task, User
    from .models.audit_log import AuditLog  # T064: ensure audit_logs table is created
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await _run_column_migrations(conn)


# ----------------------------
# ASYNC SESSION DEPENDENCY
# ----------------------------
@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(async_engine) as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_async_session_dep() -> AsyncGenerator[AsyncSession, None]:
    async with get_async_session() as session:
        yield session


# ----------------------------
# GET OR CREATE USER
# ----------------------------
from .models import User

async def get_or_create_user(session: AsyncSession, user_id: str, email: str = None) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(id=user_id, email=email)
        session.add(user)
        await session.flush()  # Ensure the user is persisted in the current transaction
    else:
        # Refresh the user to ensure we have the latest data
        await session.refresh(user)
    return user
