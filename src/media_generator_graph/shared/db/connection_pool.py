"""Asynchronous Postgres access through a shared connection pool.

A single ``AsyncConnectionPool`` per process is reused by every repository.
The pool is opened on demand on the first query and must be closed on
application shutdown (``close_pool``).

Usage:
    from media_generator_graph.shared.db.connection_pool import get_connection

    async with get_connection() as conn:
        ...
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import cast

import structlog
from psycopg import AsyncConnection
from psycopg.rows import DictRow, dict_row
from psycopg_pool import AsyncConnectionPool

from media_generator_graph.shared.configurations import settings

logger = structlog.get_logger()

DictConnection = AsyncConnection[DictRow]

_pool: "AsyncConnectionPool[DictConnection] | None" = None


async def get_pool() -> "AsyncConnectionPool[DictConnection]":
    """Return the process-wide connection pool, opening it on first call.

    The pool is created lazily and memoized in the module-level ``_pool``, so
    every repository in the process shares the same connections.

    Returns:
        The open pool, configured with ``dict_row`` and autocommit enabled.
    """
    global _pool

    if _pool is None:
        _pool = cast(
            "AsyncConnectionPool[DictConnection]",
            AsyncConnectionPool(
                conninfo=settings.database_url,
                min_size=settings.database_pool_min_size,
                max_size=settings.database_pool_max_size,
                kwargs={"row_factory": dict_row, "autocommit": True},
                open=False,
            ),
        )
        await _pool.open(wait=True, timeout=settings.database_pool_open_timeout)
        db_endpoint = settings.database_url.split("@")[-1]
        logger.info("db_pool_created", database_url=db_endpoint)
    return _pool


async def close_pool() -> None:
    """Close the pool and clear the module reference.

    Must be called on shutdown of the API and of the worker.
    """
    global _pool

    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("db_pool_closed")


@asynccontextmanager
async def get_connection() -> AsyncGenerator[DictConnection]:
    """Yield a connection borrowed from the shared pool.

    Usage:
        async with get_connection() as conn:
            await conn.execute(...)

    The connection is checked back into the pool when the context exits.

    Yields:
        A connection with ``dict_row`` as its row factory.
    """
    pool = await get_pool()
    async with pool.connection() as conn:
        yield conn


async def is_database_healthy() -> bool:
    """Check whether the database is reachable.

    Runs a trivial ``SELECT 1`` through the pooled connection.

    Returns:
        ``True`` if the probe succeeds, ``False`` if any error is raised.
    """
    try:
        pool = await get_pool()
        async with pool.connection() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception:
        logger.exception("db_health_check_failed")
        return False
