"""Standalone database migration runner.

Reads every ``*.sql`` file from the migrations directory and applies only the
ones that have not been applied yet, in lexicographic filename order. The set
of applied migrations is tracked in the ``migrations`` table, so re-running the
script is idempotent and safe.

Usage:
    python db/apply_migrations.py

Requirements:
    ``DATABASE_URL`` must be configured, either through a ``.env`` file or an
    environment variable.
"""

import asyncio
import sys
from pathlib import Path
from typing import LiteralString, cast

import psycopg
import structlog
from dotenv import load_dotenv

from media_generator_graph.shared.configurations import settings
from media_generator_graph.shared.db.connection_pool import get_connection

logger = structlog.get_logger()

load_dotenv()


def _resolve_migrations_dir() -> Path:
    """Resolve the directory that holds the ``*.sql`` migration files.

    Tries, in order, the ``migrations`` folder next to this file, the
    ``db/migrations`` folder relative to the current working directory (local
    development), and the ``/app/db/migrations`` path used inside Docker.
    Returns the first existing directory, or falls back to the sibling
    ``migrations`` folder when none of the candidates exists.

    Returns:
        Path to the resolved migrations directory.
    """
    migration_dir_search_paths = [
        Path(__file__).parent / "migrations_files",
        Path.cwd() / "db" / "migrations_files",
        Path("/app/db/migrations_files"),
    ]

    for search_path in migration_dir_search_paths:
        if search_path.is_dir():
            return search_path

    return migration_dir_search_paths[0]


MIGRATIONS_DIR = _resolve_migrations_dir()


async def _create_migrations_table_if_missing(conn) -> None:
    """Create the ``migrations`` bookkeeping table if it does not exist.

    The table records one row per applied migration: an auto-increment ``id``,
    the unique migration ``name`` (the SQL filename), and the ``applied_at``
    timestamp. Expected to run inside an open transaction.

    Args:
        conn: Open database connection used to run the DDL statement.
    """
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            id          SERIAL PRIMARY KEY,
            name        TEXT NOT NULL UNIQUE,
            applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


async def _fetch_applied_migration_names(conn) -> set[str]:
    """Return the names of every migration already recorded as applied.

    Queries the ``migrations`` bookkeeping table and collects the ``name``
    column, allowing the caller to skip files that were applied in previous
    runs. Expected to run inside an open transaction.

    Args:
        conn: Open database connection used to query the bookkeeping table.

    Returns:
        Set of migration filenames already present in the database.
    """
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT name FROM migrations ORDER BY name")
        migration_rows = await cursor.fetchall()
    return {row["name"] for row in migration_rows}


async def _load_applied_migration_names() -> set[str]:
    """Ensure the bookkeeping table exists and return the applied names.

    Opens a pooled connection, creates the ``migrations`` table if needed, and
    reads the set of migration filenames already applied in previous runs. The
    setup runs in a single transaction that is committed by the context exit.

    Returns:
        Set of migration filenames already recorded in the database.
    """
    async with get_connection() as conn, conn.transaction():
        await _create_migrations_table_if_missing(conn)
        return await _fetch_applied_migration_names(conn)


def _find_pending_migration_files(applied_migration_names: set[str]) -> list[Path]:
    """Return the migration files that have not been applied yet.

    Globs the ``*.sql`` files in the migrations directory, sorts them in
    lexicographic filename order (which defines the apply order), and drops the
    ones whose filename is already recorded as applied, logging each skip.

    Args:
        applied_migration_names: Filenames already recorded in the database.

    Returns:
        Pending migration files, in the order they must be applied.
    """
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    pending_migration_files: list[Path] = []
    for migration_file in migration_files:
        if migration_file.name in applied_migration_names:
            logger.debug("migration_already_applied", migration=migration_file.name)
            continue
        pending_migration_files.append(migration_file)

    return pending_migration_files


async def _apply_migration_file(migration_file: Path) -> None:
    """Apply a single SQL migration file and record it as applied.

    Opens a pooled connection and wraps the migration in its own transaction,
    so a failure rolls back only this file. Executes the raw SQL read from
    ``migration_file`` and inserts its filename into the ``migrations`` table,
    keeping the schema change and its bookkeeping row atomic. Logs the attempt,
    the success and, on failure, the error before re-raising.

    Args:
        migration_file: Path to the SQL file to execute and register.

    Raises:
        Exception: Any error raised while applying the migration is logged and
            re-raised so the caller can stop the remaining files.
    """
    logger.info("applying_migration", migration=migration_file.name)

    try:
        async with get_connection() as conn, conn.transaction():
            migration_sql_script = cast(
                "LiteralString", migration_file.read_text(encoding="utf-8")
            )
            await conn.execute(migration_sql_script)
            await conn.execute(
                "INSERT INTO migrations (name) VALUES (%s)",
                (migration_file.name,),
            )

    except Exception as exc:
        logger.error(
            "migration_failed",
            migration=migration_file.name,
            error=str(exc),
        )
        raise

    logger.info("migration_applied", migration=migration_file.name)


async def apply_pending_migrations() -> None:
    """Apply every pending SQL migration to the database.

    Ensures the bookkeeping table exists, discovers the migration files that
    have not been applied yet, and applies each one in its own transaction.
    Already-applied migrations are skipped, so the call is idempotent.

    Raises:
        Exception: Any error raised while applying a migration is logged and
            re-raised, stopping the remaining files.
    """
    applied_migration_names = await _load_applied_migration_names()
    pending_migration_files = _find_pending_migration_files(applied_migration_names)

    for migration_file in pending_migration_files:
        await _apply_migration_file(migration_file)


async def main() -> None:
    """Command-line entry point for the migration script.

    Validates that the database URL is configured, runs the pending migrations,
    and converts configuration problems or ``psycopg`` errors into a non-zero
    process exit code. Successful runs leave the process with the default exit
    code.
    """
    database_url = settings.database_url
    if not database_url:
        logger.error(
            "database_url_not_configured",
            hint="Set DATABASE_URL via .env or an environment variable.",
        )
        sys.exit(1)

    logger.info("connecting_to_database")
    try:
        await apply_pending_migrations()
        logger.info("migrations_completed")
    except psycopg.Error as exc:
        logger.error("migration_run_failed", error=str(exc))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
