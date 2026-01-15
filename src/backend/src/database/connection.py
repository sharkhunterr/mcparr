"""Database connection and session management."""

import os
from typing import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

# Import all models to register them with Base.metadata
from src.models.base import Base


def _configure_sqlite_connection(dbapi_connection, connection_record):
    """Configure SQLite connection for better concurrency."""
    cursor = dbapi_connection.cursor()
    # Enable WAL mode for better concurrency (readers don't block writers)
    cursor.execute("PRAGMA journal_mode=WAL")
    # Wait up to 30 seconds when database is locked
    cursor.execute("PRAGMA busy_timeout=30000")
    # Synchronous mode - NORMAL is a good balance between safety and speed
    cursor.execute("PRAGMA synchronous=NORMAL")
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class DatabaseManager:
    """Database connection and session manager."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.is_sqlite = database_url.startswith("sqlite")

        # SQLite-specific configuration
        engine_kwargs = {
            "echo": os.getenv("DEBUG", "false").lower() == "true",
        }

        if self.is_sqlite:
            # For SQLite with aiosqlite, use StaticPool to share connection
            # and avoid "database is locked" errors
            engine_kwargs["poolclass"] = StaticPool
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        else:
            # For other databases, use standard pool settings
            engine_kwargs["pool_pre_ping"] = True

        self.engine: AsyncEngine = create_async_engine(
            database_url,
            **engine_kwargs,
        )

        # Register SQLite pragma configuration
        if self.is_sqlite:
            event.listen(self.engine.sync_engine, "connect", _configure_sqlite_connection)
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
    return os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/mcparr.db")


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
