"""PostgreSQL-backed factory for LangGraph long-term memory storage.

This module opens an ``AsyncPostgresStore`` configured with the application's
OpenRouter embedding client. It persists each memory's original JSON value and
optionally indexes its text as vectors for semantic retrieval.

Callers must run ``store.setup()`` once to apply the store migrations, then
close the returned ``AsyncExitStack`` when they are finished using the store.
Execution checkpoints are managed separately by ``langchain_checkpointer``.
"""

from contextlib import AsyncExitStack

from langgraph.store.postgres import AsyncPostgresStore
from langgraph.store.postgres.base import PostgresIndexConfig

from media_generator_graph.shared.configurations import settings
from media_generator_graph.shared.embeddings_factory import create_embeddings


async def open_store() -> tuple[AsyncExitStack, AsyncPostgresStore] | tuple[None, None]:
    """Open the PostgreSQL-backed LangGraph store and return its lifecycle stack.

    The caller must close the returned ``AsyncExitStack`` after it has finished
    using the store. The store is configured with the project's embedding
    provider and index settings.

    Returns:
        A tuple containing the lifecycle stack and initialized asynchronous
        store.
    """

    stack = AsyncExitStack()
    store = await stack.enter_async_context(
        AsyncPostgresStore.from_conn_string(
            settings.database_url,
            index=resolve_store_index_config(),
        )
    )
    return stack, store


def resolve_store_index_config() -> PostgresIndexConfig:
    """Build the embedding index configuration for ``AsyncPostgresStore``.

    The configuration indexes every stored field using the application-wide
    embedding client and its configured vector dimensions.
    """
    return {
        "embed": create_embeddings(),
        "dims": settings.embedding_dims,
        "fields": ["$"],
    }
