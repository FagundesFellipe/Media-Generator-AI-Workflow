"""Catalog of OpenRouter model IDs used across the prompts manager.

Exposes a single `StrEnum` that centralizes every supported model
identifier, so callers never hardcode provider strings and model upgrades
happen in one place.
"""

from enum import StrEnum


class OpenRouterModelsIds(StrEnum):
    """Fixed catalog of OpenRouter model IDs.

    Each member is a `str` holding the full ID in ``provider/model`` format,
    ready to be passed directly as the ``model`` argument of
    ``create_chat_model``.

    Example:
        router = create_chat_model(
            model=OpenRouterModelsIds.GEMINI_2_5_FLASH_LITE,
        ).with_structured_output(RouteIntention)
    """

    # --- OpenAI ---
    GPT_5_6_LUNA = "openai/gpt-5.6-luna"
    GPT_5_4_NANO = "openai/gpt-5.4-nano"
    GPT_5_4_MINI = "openai/gpt-5.4-mini"
    GPT_5_4 = "openai/gpt-5.4"

    # --- Google ---
    GEMINI_2_5_FLASH_LITE = "google/gemini-2.5-flash-lite"
    GEMINI_2_5_FLASH = "google/gemini-2.5-flash"

    # --- DeepSeek ---
    DEEPSEEK_V4_FLASH = "deepseek/deepseek-v4-flash"

    # --- MiniMax ---
    MINI_MAX_M2_7 = "minimax/minimax-m2.7:free"

    # --- GLM 5.2 ---
    GLM_5_2 = "z-ai/glm-5.2:free"
