"""
SQLAlchemy async engine and session factory.
REQ-07: PostgreSQL database layer.
"""
import os
import re
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

# Sync URL for Alembic (psycopg2 driver)
_SYNC_URL = os.getenv(
    'DATABASE_URL_SYNC',
    'postgresql+psycopg2://saadahmed@localhost/bpulse'
)

# Raw URL from env (may use asyncpg or psycopg2 scheme)
_RAW_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+asyncpg://saadahmed@localhost/bpulse'
)

# Convert to psycopg3 async scheme to avoid asyncpg
# "cannot perform operation: another operation is in progress" errors.
# psycopg3 is also used by langgraph-checkpoint-postgres, keeping all
# PostgreSQL traffic on the same driver.
DATABASE_URL = re.sub(
    r'^postgresql(\+asyncpg|\+psycopg2)?://',
    'postgresql+psycopg://',
    _RAW_URL,
)


class Base(DeclarativeBase):
    pass


# NullPool: each session creates its own connection — no pool sharing.
engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_db():
    """Alias for get_session (convenience)."""
    async with AsyncSessionLocal() as session:
        yield session
