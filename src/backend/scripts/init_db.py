#!/usr/bin/env python3
"""Initialize database tables and stamp alembic version.

This script:
1. Creates all tables using SQLAlchemy's create_all() (idempotent)
2. Stamps the alembic version table to mark all migrations as applied

This ensures a fresh database starts with all tables and the correct
migration state, so subsequent alembic upgrades work correctly.
"""

import asyncio
import os
import subprocess
import sys

# Add the backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database.connection import init_database


def check_alembic_version_exists():
    """Check if alembic_version table exists and has entries."""
    import sqlite3

    db_path = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/mcparr.db")
    # Extract file path from URL
    if ":///" in db_path:
        db_file = db_path.split(":///")[-1]
    else:
        db_file = "./data/mcparr.db"

    if not os.path.exists(db_file):
        return False

    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM alembic_version")
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except sqlite3.OperationalError:
        return False


async def main():
    """Initialize database tables and stamp alembic."""
    print("Initializing database...")

    # Check if this is a fresh database (no alembic version)
    is_fresh = not check_alembic_version_exists()

    if is_fresh:
        print("Fresh database detected, creating all tables...")
        db_manager = init_database()
        await db_manager.create_tables()
        await db_manager.close()
        print("Database tables created successfully.")

        # Stamp alembic to mark all migrations as applied
        print("Stamping alembic version to 'head'...")
        result = subprocess.run(
            ["alembic", "stamp", "head"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"Warning: alembic stamp failed: {result.stderr}")
        else:
            print("Alembic stamped to head successfully.")
    else:
        print("Existing database detected, skipping table creation.")

    print("Database initialization complete.")


if __name__ == "__main__":
    asyncio.run(main())
