from contextlib import asynccontextmanager
from urllib.parse import urlparse, parse_qs, urlencode
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from ..config import settings
from typing import AsyncGenerator

# Helper function to convert string to boolean
def str_to_bool(value):
    return value.lower() in ('true', '1', 'yes', 'on')

# Build asyncpg-compatible URL: strip sslmode/channel_binding params that asyncpg doesn't support
raw_url = settings.database_url_resolved
parsed = urlparse(raw_url)

query_params = parse_qs(parsed.query)
query_params.pop('sslmode', None)
query_params.pop('channel_binding', None)
clean_query = urlencode(query_params, doseq=True)

db_url = f"postgresql+asyncpg://{parsed.netloc}{parsed.path}"
if clean_query:
    db_url += f"?{clean_query}"

# Create the async engine with pool recycling for Neon serverless
engine = create_async_engine(
    db_url,
    echo=str_to_bool(settings.debug),
    connect_args={"server_settings": {"application_name": "Todo-API-App"}},
    pool_recycle=300,
    pool_pre_ping=True,
)

# Create the async session maker
AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession
)


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
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


# Import User model here to avoid circular imports
async def get_or_create_user(session: AsyncSession, user_id: str, email: str = None):
    from ..models.user import User
    from sqlmodel import select
    from sqlalchemy import text

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user and email:
        # User ID not found — check if a user with this email already exists
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user and user.id != user_id:
            # Same email but different ID (e.g. frontend changed ID scheme).
            # Migrate: create new user row, re-point children, delete old row.
            old_id = user.id
            await session.execute(
                text("UPDATE users SET email = NULL WHERE id = :old_id"),
                {"old_id": old_id},
            )
            await session.execute(
                text("INSERT INTO users (id, email, created_at, updated_at) "
                     "VALUES (:id, :email, NOW(), NOW())"),
                {"id": user_id, "email": email},
            )
            await session.execute(
                text("UPDATE tasks SET user_id = :new WHERE user_id = :old"),
                {"new": user_id, "old": old_id},
            )
            await session.execute(
                text("UPDATE conversations SET user_id = :new WHERE user_id = :old"),
                {"new": user_id, "old": old_id},
            )
            await session.execute(
                text("UPDATE messages SET user_id = :new WHERE user_id = :old"),
                {"new": user_id, "old": old_id},
            )
            await session.execute(
                text("DELETE FROM users WHERE id = :old_id"),
                {"old_id": old_id},
            )
            await session.flush()
            # Clear ORM cache and re-fetch the migrated user
            session.expire_all()
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

    if not user:
        user = User(id=user_id, email=email)
        session.add(user)
        await session.flush()

    return user