"""Shared utilities for the prompts manager.

Directory resolution and path validation for prompt files, plus the
centralized application settings.
"""

from prompts_manager.shared.prompts_directory import (
    ensure_prompts_dir_exists,
    get_prompt_dir,
)
from prompts_manager.shared.settings import (
    ACTIVE_VERSIONS_KEY,
    METADATA_FILE,
    PROMPTS_DIR,
    settings,
)

__all__ = [
    "ACTIVE_VERSIONS_KEY",
    "METADATA_FILE",
    "PROMPTS_DIR",
    "ensure_prompts_dir_exists",
    "get_prompt_dir",
    "settings",
]
