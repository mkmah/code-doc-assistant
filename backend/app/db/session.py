"""Async database session management for SQLAlchemy."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Create async engine
engine = create_async_engine(
    settings.app_db_url,
    pool_size=settings.app_db_pool_size,
    max_overflow=settings.app_db_max_overflow,
    echo=settings.log_level.lower() == "debug",
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependency for FastAPI to get async DB session.

    Yields:
        Async database session

    Example:
        ```python
        @router.get("/codebases")
        async def list_codebases(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Codebase))
            return result.scalars().all()
        ```
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncIterator[AsyncSession]:
    """Context manager for getting async DB session outside of FastAPI.

    Yields:
        Async database session

    Example:
        ```python
        async with get_db_context() as db:
            result = await db.execute(select(Codebase))
            codebases = result.scalars().all()
        ```
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database connection pool.

    Called on application startup to verify database connectivity.
    """
    try:
        async with engine.begin() as conn:
            # Test connection
            await conn.execute(text("SELECT 1"))
        logger.info(
            "database_connected",
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.app_db_name,
        )
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        raise


async def close_db() -> None:
    """Close database connection pool.

    Called on application shutdown.
    """
    await engine.dispose()
    logger.info("database_connection_closed")
