"""PostgreSQL persistence utilities for LangGraph execution checkpoints.

This module manages a process-wide ``AsyncPostgresSaver`` backed by the
application's shared connection pool. The checkpointer persists short-term
graph state by thread, enabling durable execution and graph resumption across
the lifecycle of a content-generation run.

``bootstrap_langgraph_schema`` applies the LangGraph database migrations
required by the checkpointer. It is separate from long-term memory storage,
which is provided by ``langchain_memory``.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import cast

import structlog
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from media_generator_graph.shared.db.connection_pool import get_pool

logger = structlog.get_logger()

_checkpointer: AsyncPostgresSaver | None = None


async def get_checkpointer() -> AsyncPostgresSaver:
    """Return the process-wide checkpointer, creating it on first call.

    The checkpointer reuses the process connection pool. Unlike
    ``from_conn_string``, this instance does not close the connection between
    uses, which keeps the compiled graph usable for the whole application
    lifecycle.
    """
    global _checkpointer

    if _checkpointer is None:
        _checkpointer = cast(
            AsyncPostgresSaver,
            AsyncPostgresSaver(conn=await get_pool()).with_allowlist([]),
        )
        logger.info("checkpointer_created")
    return _checkpointer


async def close_checkpointer() -> None:
    """Release the reference to the checkpointer.

    The underlying pool is closed separately by :func:`close_pool`.
    """
    global _checkpointer

    if _checkpointer is not None:
        _checkpointer = None
        logger.info("checkpointer_closed")


@asynccontextmanager
async def open_checkpointer() -> AsyncGenerator[AsyncPostgresSaver]:
    """Provide the process-wide checkpointer.

    Kept as a context manager for compatibility with existing call sites; the
    checkpointer itself stays open and reusable.
    """
    yield await get_checkpointer()


async def bootstrap_langgraph_schema() -> None:
    """Initialize the LangGraph checkpointer/store tables."""

    logger.info(
        "langgraph_schema_bootstrap_starting",
    )

    checkpointer = await get_checkpointer()
    await checkpointer.setup()
