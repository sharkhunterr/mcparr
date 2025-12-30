"""Database connection and session management."""

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
# Import all models to register them with Base.metadata
from src.models import (
    SystemMetric, ConfigurationSetting, ServiceConfig, ServiceHealthHistory,
    UserMapping, UserSync, LogEntry, AlertConfiguration, AlertHistory,
    TrainingWorker, WorkerMetricsSnapshot
)


class DatabaseManager:
    """Database connection and session manager."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine: AsyncEngine = create_async_engine(
            database_url,
            echo=os.getenv("DEBUG", "false").lower() == "true",
            pool_pre_ping=True,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def create_tables(self) -> None:
        """Create all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def close(self) -> None:
        """Close database connection."""
        await self.engine.dispose()

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session."""
        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


# Global database manager instance
database_manager: DatabaseManager = None


def get_database_url() -> str:
    """Get database URL from environment."""
    return os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./data/mcparr.db"
    )


def init_database() -> DatabaseManager:
    """Initialize database manager."""
    global database_manager
    if database_manager is None:
        database_manager = DatabaseManager(get_database_url())
    return database_manager


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global database_manager
    if database_manager is None:
        init_database()
    return database_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session."""
    if database_manager is None:
        init_database()

    async for session in database_manager.get_session():
        yield session


def get_async_session_maker():
    """Get the async session maker for creating sessions outside of request context."""
    if database_manager is None:
        init_database()
    return database_manager.session_factory


# Alias for convenience - returns the session factory directly
async_session_maker = property(lambda self: get_async_session_maker())


class AsyncSessionMaker:
    """Context manager for creating async sessions."""

    def __call__(self):
        if database_manager is None:
            init_database()
        return database_manager.session_factory()


async_session_maker = AsyncSessionMaker()