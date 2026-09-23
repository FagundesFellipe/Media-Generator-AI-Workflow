"""Shared factory for embedding clients.

Centralizes ``OpenAIEmbeddings`` configuration so the project consistently
uses the OpenRouter defaults defined in settings.
"""

from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from media_generator_graph.shared.configurations import settings


def create_embeddings(model: str | None = None) -> OpenAIEmbeddings:
    """Create an ``OpenAIEmbeddings`` client configured from application settings.

    Args:
        model: Optional embedding model override. When omitted, uses the
            configured OpenRouter embedding model.
    """
    api_key = settings.openrouter_api_key
    secret_key = SecretStr(api_key.get_secret_value()) if api_key else None

    return OpenAIEmbeddings(
        model=model or settings.openrouter_embedding_model,
        base_url=settings.openrouter_base_url,
        api_key=secret_key,
    )
