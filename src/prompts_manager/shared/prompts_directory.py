"""Helpers for locating and creating the prompts directory."""

import json
import re
from pathlib import Path

from .settings import ACTIVE_VERSIONS_KEY, METADATA_FILE, PROMPTS_DIR

_VALID_PROMPT_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


def ensure_prompts_dir_exists():
    """Create the prompts directory and an empty metadata file if missing.

    Returns:
        None
    """
    PROMPTS_DIR.mkdir(exist_ok=True)
    if not METADATA_FILE.exists():
        with open(METADATA_FILE, "w") as file:
            json.dump({ACTIVE_VERSIONS_KEY: {}}, file, indent=2, ensure_ascii=False)


def get_prompt_dir(prompt_name: str) -> Path:
    """Return the directory path for a given prompt name.

    Args:
        prompt_name: Name of the prompt.

    Returns:
        The resolved prompt directory path.

    Raises:
        ValueError: If the name contains invalid characters or resolves outside
            the prompts directory.
    """
    if not _VALID_PROMPT_NAME.match(prompt_name):
        raise ValueError(
            f"Invalid prompt name: '{prompt_name}'. "
            "Use only letters, numbers, hyphens, and underscores (max 64 chars)."
        )
    resolved = (PROMPTS_DIR / prompt_name).resolve()
    if not str(resolved).startswith(str(PROMPTS_DIR.resolve())):
        raise ValueError(f"Path traversal blocked for prompt: {prompt_name}")
    return resolved
