"""Factories for configured OpenRouter chat models and shared rate limiters."""

from typing import Literal

from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from media_generator_graph.shared.configurations import settings


def create_chat_model(
    openrouter_model_identifier: str,
    temperature: float = 0.0,
    reasoning_effort_level: Literal["none", "low", "medium", "high"] = "none",
) -> ChatOpenAI:
    """
    Creates ChatOpenAI configured the transmission rate limiter.

        Rate limiter uses token bucket: limits requests per second
        with burst for controlled peaks. The values come from the settings
        (LLM_RATE_LIMIT_REQUESTS_PER_SECOND e LLM_RATE_LIMIT_MAX_BURST).

        Args:
            openrouter_model_identifier: model id in openrouter. Default: setting.sopenrouter_text_model.
            temperature: Temperature. Standard: None (USA standard provider).
            reasoning_effort_level: Reasoning level. Default None (uses provider default)

        Returns:
            ChatOpenAI with rate limiter applied.
    """

    api_key = settings.openrouter_api_key
    api_key_secret = SecretStr(api_key.get_secret_value()) if api_key else None

    rate_limiter = get_or_create_rate_limiter(
        requests_per_second=settings.llm_rate_limit_requests_per_second,
        max_bucket_size=settings.llm_rate_limit_max_burst,
    )

    chat_model_kwargs: dict = {
        "model": openrouter_model_identifier or settings.openrouter_media_model,
        "api_key": api_key_secret,
        "base_url": settings.openrouter_base_url,
        "rate_limiter": rate_limiter,
        "temperature": temperature,
        "reasoning_effort": reasoning_effort_level,
    }

    return ChatOpenAI(**chat_model_kwargs)


_RATE_LIMITERS: dict[tuple[float, int], InMemoryRateLimiter] = {}


def get_or_create_rate_limiter(
    requests_per_second: float, max_bucket_size: int
) -> InMemoryRateLimiter:
    """
    Returns the rate limiter for the given token-bucket limits, creating it on
    first use and reusing it afterward.

    Instances are memoized per (requests_per_second, max_bucket_size) pair, so
    every caller asking for the same limits shares a single limiter instead of
    each building its own.

    Args:
        requests_per_second: Sustained refill rate of the token bucket.
        max_bucket_size: Maximum tokens the bucket can hold (burst size).

    Returns:
        The shared InMemoryRateLimiter configured with these limits.
    """

    key = (requests_per_second, max_bucket_size)
    if key not in _RATE_LIMITERS:
        _RATE_LIMITERS[key] = InMemoryRateLimiter(
            requests_per_second=requests_per_second, max_bucket_size=max_bucket_size
        )

    return _RATE_LIMITERS[key]
