"""
SQLAlchemy async engine and session factory.
REQ-07: PostgreSQL database layer.
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Sync URL for Alembic (psycopg2 driver)
_SYNC_URL = os.getenv(
    'DATABASE_URL_SYNC',
    'postgresql+psycopg2://saadahmed@localhost/bpulse'
)

# Async URL for application (asyncpg driver)
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+asyncpg://saadahmed@localhost/bpulse'
)


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=5,
    pool_recycle=3600,
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
