#!/usr/bin/env python3
"""Initialize database tables before running migrations.

This script creates all tables using SQLAlchemy's create_all(),
which is safe to run multiple times (it only creates tables that don't exist).
This ensures migrations can run successfully on a fresh database.
"""

import asyncio
import os
import sys

# Add the backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database.connection import init_database


async def main():
    """Initialize database tables."""
    print("Initializing database tables...")

    db_manager = init_database()
    await db_manager.create_tables()
    await db_manager.close()

    print("Database tables initialized successfully.")


if __name__ == "__main__":
    asyncio.run(main())
