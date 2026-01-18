"""Database connection management for Oura Health Agent.

Uses SQLAlchemy 2.0 with asyncpg for async PostgreSQL operations.
"""

import logging
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Module-level engine cache
_engine: AsyncEngine | None = None


def get_engine(connection_string: str, pool_size: int = 5, max_overflow: int = 10) -> AsyncEngine:
    """Get or create the async database engine.

    Args:
        connection_string: PostgreSQL connection string (must use asyncpg driver)
        pool_size: Connection pool size
        max_overflow: Maximum overflow connections

    Returns:
        AsyncEngine: SQLAlchemy async engine
    """
    global _engine

    if _engine is not None:
        return _engine

    # Ensure connection string uses asyncpg driver
    if "asyncpg" not in connection_string:
        if connection_string.startswith("postgresql://"):
            connection_string = connection_string.replace(
                "postgresql://", "postgresql+asyncpg://"
            )

    logger.info("Creating async database engine")
    _engine = create_async_engine(
        connection_string,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
        echo=False,
    )

    return _engine


def get_session_factory(engine: AsyncEngine) -> sessionmaker:
    """Get async session factory.

    Args:
        engine: SQLAlchemy async engine

    Returns:
        sessionmaker: Async session factory
    """
    return sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@asynccontextmanager
async def get_async_session(
    connection_string: str,
    pool_size: int = 5,
    max_overflow: int = 10,
) -> AsyncGenerator[AsyncSession, None]:
    """Context manager for async database sessions.

    Args:
        connection_string: PostgreSQL connection string
        pool_size: Connection pool size
        max_overflow: Maximum overflow connections

    Yields:
        AsyncSession: Database session
    """
    engine = get_engine(connection_string, pool_size, max_overflow)
    session_factory = get_session_factory(engine)

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def test_connection(connection_string: str) -> bool:
    """Test database connection.

    Args:
        connection_string: PostgreSQL connection string

    Returns:
        bool: True if connection successful
    """
    try:
        engine = get_engine(connection_string)
        async with engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


async def close_engine() -> None:
    """Close the database engine and dispose of all connections."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("Database engine closed")
