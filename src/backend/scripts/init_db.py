#!/usr/bin/env python3
"""Initialize database using Alembic migrations.

This script ensures the database is properly initialized:
1. For fresh databases: runs all migrations from scratch
2. For existing databases: applies any pending migrations
3. For corrupted migration state: resets and re-runs migrations

All schema management is done through Alembic migrations to ensure
consistency between fresh installs and upgrades.
"""

import os
import sqlite3
import subprocess
import sys


def get_db_path():
    """Extract database file path from DATABASE_URL."""
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/mcparr.db")
    if ":///" in db_url:
        return db_url.split(":///")[-1]
    return "./data/mcparr.db"


def ensure_data_directory():
    """Ensure the data directory exists."""
    db_path = get_db_path()
    data_dir = os.path.dirname(db_path)
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
        print(f"Created data directory: {data_dir}")


def check_schema_integrity():
    """Check if the database schema matches expected state.

    Returns True if schema appears valid, False if migrations need to be re-run.
    """
    db_path = get_db_path()

    if not os.path.exists(db_path):
        return True  # Fresh DB, no issues

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check for critical columns that should exist
        # These are columns added by migrations that might be missing
        # if the DB was created with create_all() + stamp head
        checks = [
            ("alert_history", "acknowledged"),
            ("alert_history", "acknowledged_at"),
            ("service_configs", "external_url"),
        ]

        for table, column in checks:
            try:
                cursor.execute(f"SELECT {column} FROM {table} LIMIT 1")
            except sqlite3.OperationalError as e:
                if "no such column" in str(e):
                    print(f"Schema mismatch detected: {table}.{column} is missing")
                    conn.close()
                    return False
                elif "no such table" in str(e):
                    # Table doesn't exist yet, that's OK for fresh DB
                    pass

        conn.close()
        return True

    except Exception as e:
        print(f"Error checking schema: {e}")
        return True  # Assume OK on error, let alembic handle it


def reset_alembic_version():
    """Reset alembic version to force re-running all migrations."""
    db_path = get_db_path()

    if not os.path.exists(db_path):
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Drop alembic_version table to force fresh migration run
        cursor.execute("DROP TABLE IF EXISTS alembic_version")
        conn.commit()
        conn.close()
        print("Reset alembic version table")

    except Exception as e:
        print(f"Error resetting alembic version: {e}")


def run_migrations():
    """Run Alembic migrations to latest version."""
    print("Running database migrations...")

    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Migration error: {result.stderr}")
        return False

    if result.stdout:
        print(result.stdout)

    print("Database migrations complete.")
    return True


def main():
    """Initialize database with migrations."""
    print("Initializing database...")

    # Ensure data directory exists
    ensure_data_directory()

    # Check if schema is valid (detects create_all + stamp head issues)
    if not check_schema_integrity():
        print("Schema integrity check failed, resetting migration state...")
        reset_alembic_version()

    # Run migrations (creates tables for fresh DB, updates existing DB)
    success = run_migrations()

    if success:
        print("Database initialization complete.")
    else:
        print("Database initialization completed with warnings.")


if __name__ == "__main__":
    main()
